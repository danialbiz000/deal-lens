from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.ingestion import edgar_client, market_data_client, normalize
from app.models.company import Company
from app.models.financial_period import FinancialPeriod
from app.schemas.financial_period import FinancialPeriodRead, IngestRequest, IngestResponse

router = APIRouter(prefix="/companies", tags=["financials"])

VALID_PERIOD_TYPES = {"FY", "Q1", "Q2", "Q3", "Q4", "TTM"}


def _upsert_period(db: Session, company_id: str, normalized: dict) -> FinancialPeriod:
    existing = (
        db.query(FinancialPeriod)
        .filter(
            FinancialPeriod.company_id == company_id,
            FinancialPeriod.period_end_date == normalized["period_end_date"],
            FinancialPeriod.period_type == normalized["period_type"],
            FinancialPeriod.source == normalized["source"],
        )
        .first()
    )
    if existing is None:
        existing = FinancialPeriod(company_id=company_id)
        db.add(existing)

    for field, value in normalized.items():
        setattr(existing, field, value)

    return existing


@router.post("/{company_id}/ingest", response_model=IngestResponse)
def ingest_financials(
    company_id: str, payload: IngestRequest, db: Session = Depends(get_db)
) -> IngestResponse:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    sources = payload.sources or ["SEC_EDGAR", "FMP"]
    warnings: List[str] = []
    raw_periods: List[dict] = []

    if "SEC_EDGAR" in sources:
        if not company.cik:
            warnings.append("SEC_EDGAR: skipped, company has no CIK on file")
        else:
            try:
                facts = edgar_client.fetch_company_facts(company.cik, settings.edgar_user_agent)
                edgar_periods = edgar_client.extract_annual_periods(facts)
                edgar_periods = sorted(edgar_periods, key=lambda p: p["fiscal_year"])[-payload.years_back :]
                raw_periods.extend(edgar_periods)
            except edgar_client.EdgarClientError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc

    if "FMP" in sources:
        if not settings.fmp_api_key:
            warnings.append("FMP: skipped, no FMP_API_KEY configured")
        else:
            try:
                income = market_data_client.fetch_income_statement(
                    company.ticker, settings.fmp_api_key, payload.years_back
                )
                balance = market_data_client.fetch_balance_sheet(
                    company.ticker, settings.fmp_api_key, payload.years_back
                )
                cashflow = market_data_client.fetch_cash_flow(
                    company.ticker, settings.fmp_api_key, payload.years_back
                )
                fmp_periods = market_data_client.extract_annual_periods(income, balance, cashflow)
                raw_periods.extend(fmp_periods)
            except market_data_client.FmpClientError as exc:
                warnings.append(str(exc))

            # Phase 2 (design doc section 1.1): backfill the market-data
            # snapshot on the Company row itself while we're already
            # talking to FMP for this ticker -- no separate endpoint.
            try:
                profile = market_data_client.fetch_profile(company.ticker, settings.fmp_api_key)
                snapshot = market_data_client.extract_market_snapshot(profile)
                if snapshot is None:
                    warnings.append(f"FMP: no market profile data found for {company.ticker}")
                else:
                    company.market_cap = snapshot["market_cap"]
                    company.share_price = snapshot["share_price"]
                    company.market_data_as_of = date.today()
                    company.market_data_source = "FMP"
            except market_data_client.FmpClientError as exc:
                warnings.append(f"FMP profile: {exc}")

    normalized_periods, normalize_warnings = normalize.normalize_periods(
        raw_periods, currency=company.reporting_currency
    )
    warnings.extend(normalize_warnings)

    for field_name, human_name in (
        ("shares_outstanding", "shares_outstanding"),
        ("interest_expense", "interest_expense"),
    ):
        for period in normalized_periods:
            if period.get(field_name) is None:
                warnings.append(
                    f"{period['source']}: {human_name} missing for FY{period['fiscal_year']}"
                )

    saved_periods: List[FinancialPeriod] = []
    for normalized in normalized_periods:
        row = _upsert_period(db, company_id, normalized)
        saved_periods.append(row)

    db.commit()
    for row in saved_periods:
        db.refresh(row)

    return IngestResponse(
        company_id=company_id,
        ingested_periods=len(saved_periods),
        periods=[FinancialPeriodRead.model_validate(p) for p in saved_periods],
        warnings=warnings,
    )


@router.get("/{company_id}/financials", response_model=List[FinancialPeriodRead])
def get_financials(
    company_id: str,
    period_type: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[FinancialPeriod]:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    if period_type is not None and period_type not in VALID_PERIOD_TYPES:
        raise HTTPException(status_code=422, detail=f"invalid period_type: {period_type}")

    query = db.query(FinancialPeriod).filter(FinancialPeriod.company_id == company_id)
    if period_type:
        query = query.filter(FinancialPeriod.period_type == period_type)

    return (
        query.order_by(FinancialPeriod.period_end_date.desc()).limit(limit).all()
    )

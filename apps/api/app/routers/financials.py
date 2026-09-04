import base64
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.ai.client import ClaudeApiError, ClaudeClient, get_claude_client
from app.ai.extraction import extract_financials
from app.config import settings
from app.db import get_db
from app.ingestion import edgar_client, market_data_client, normalize
from app.ingestion.normalize import to_positive_magnitude
from app.models.company import Company
from app.models.financial_period import FinancialPeriod
from app.rate_limit import (
    SCOPE_AI_PER_IP,
    SCOPE_EXTRACTION_PER_COMPANY,
    SCOPE_INGEST_PER_COMPANY,
    SCOPE_INGEST_PER_IP,
    company_id_key,
    limiter,
)
from app.schemas.financial_period import (
    DocumentExtractionResponse,
    FinancialPeriodRead,
    IngestRequest,
    IngestResponse,
    ManualFinancialPeriodCreate,
)

# Anthropic document understanding is capped well above this in practice, but
# a hard local ceiling keeps one oversized upload from tying up a request/
# inflating token cost unexpectedly (design doc's own "validate at system
# boundaries" principle).
MAX_EXTRACTION_UPLOAD_BYTES = 20 * 1024 * 1024

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
@limiter.limit(lambda: settings.rate_limit_ingest_per_ip, error_message=SCOPE_INGEST_PER_IP)
@limiter.limit(lambda: settings.rate_limit_ingest_per_company, key_func=company_id_key, error_message=SCOPE_INGEST_PER_COMPANY)
def ingest_financials(
    request: Request, company_id: str, payload: IngestRequest, db: Session = Depends(get_db)
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


@router.post("/{company_id}/financials", response_model=FinancialPeriodRead, status_code=201)
def create_manual_financial_period(
    company_id: str, payload: ManualFinancialPeriodCreate, db: Session = Depends(get_db)
) -> FinancialPeriod:
    """For private companies -- no CIK, no SEC/EDGAR filing, usually no FMP
    market data either -- this is the only way their financials can enter
    DealLens at all. Everything downstream (screening, comps, LBO) already
    works on `FinancialPeriod` rows regardless of where they came from; the
    gap this closes is purely getting the numbers in, not analyzing them.
    """
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    if payload.period_type not in VALID_PERIOD_TYPES:
        raise HTTPException(status_code=422, detail=f"invalid period_type: {payload.period_type}")

    if payload.revenue is None and payload.ebitda is None and payload.operating_cash_flow is None:
        raise HTTPException(
            status_code=422,
            detail="at least one of revenue, ebitda, or operating_cash_flow must be provided",
        )

    normalized = {
        "fiscal_year": payload.fiscal_year,
        "period_end_date": payload.period_end_date,
        "period_type": payload.period_type,
        "currency": payload.currency,
        "source": "MANUAL",
        "source_ref": payload.source_ref,
        "revenue": payload.revenue,
        "gross_profit": payload.gross_profit,
        "ebitda": payload.ebitda,
        "ebit": payload.ebit,
        "net_income": payload.net_income,
        "operating_cash_flow": payload.operating_cash_flow,
        "capex": to_positive_magnitude(payload.capex),
        "total_debt": to_positive_magnitude(payload.total_debt),
        "cash_and_equivalents": payload.cash_and_equivalents,
        "interest_expense": payload.interest_expense,
        "shares_outstanding": payload.shares_outstanding,
        # Never audited/machine-verified like an EDGAR filing -- always
        # flagged, so it can never be silently mistaken for one downstream.
        "is_estimate": True,
        "raw_payload": None,
    }

    row = _upsert_period(db, company_id, normalized)
    db.commit()
    db.refresh(row)
    return row


@router.post("/{company_id}/documents/extract", response_model=DocumentExtractionResponse)
@limiter.shared_limit(lambda: settings.rate_limit_ai_per_ip, scope=SCOPE_AI_PER_IP, error_message=SCOPE_AI_PER_IP)
@limiter.limit(
    lambda: settings.rate_limit_extraction_per_company, key_func=company_id_key, error_message=SCOPE_EXTRACTION_PER_COMPANY
)
def extract_financials_from_document(
    request: Request,
    company_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    client: ClaudeClient = Depends(get_claude_client),
) -> DocumentExtractionResponse:
    """Upload a financial statement / investor-relations PDF and get back AI-
    proposed candidate periods for human review -- never written to the
    database directly (design doc section 8). A reviewer confirms/edits each
    candidate and saves it the same way a manually-typed period is saved,
    via POST /companies/{id}/financials.
    """
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=422, detail=f"unsupported file type: {file.content_type}, expected a PDF")

    raw = file.file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=422, detail="uploaded file is empty")
    if len(raw) > MAX_EXTRACTION_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"file too large: {len(raw)} bytes, max {MAX_EXTRACTION_UPLOAD_BYTES} bytes",
        )

    try:
        result = extract_financials(base64.b64encode(raw).decode("ascii"), client)
    except ClaudeApiError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return DocumentExtractionResponse(periods=result["periods"], notes=result["notes"])


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

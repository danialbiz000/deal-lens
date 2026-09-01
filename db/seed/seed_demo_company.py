"""Seed script: load one real public company end-to-end for local dev/demo.

Usage (from the repo root, with apps/api's venv active and its .env
configured -- EDGAR_USER_AGENT is required, FMP_API_KEY is optional):

    python db/seed/seed_demo_company.py [TICKER] [CIK]

Defaults to Apple Inc. (AAPL, CIK 0000320193) if no args are given -- a
company with clean XBRL tagging and no negative-EBITDA/zero-revenue edge
cases, so the seeded demo shows the finance engine's "normal case" path.

This script performs REAL network calls to SEC EDGAR and, if FMP_API_KEY is
configured, to Financial Modeling Prep. It reuses apps/api/app's ingestion
and normalization modules directly rather than re-implementing them, so
there is exactly one ingestion code path between the API's own
POST /companies/{id}/ingest endpoint and this script.
"""

import sys
from pathlib import Path

API_APP_ROOT = Path(__file__).resolve().parents[2] / "apps" / "api"
sys.path.insert(0, str(API_APP_ROOT))

from app.config import settings  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.ingestion import edgar_client, market_data_client, normalize  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.financial_period import FinancialPeriod  # noqa: E402
from finance_engine import FinancialPeriodInput, score_company  # noqa: E402

DEFAULT_TICKER = "AAPL"
DEFAULT_CIK = "0000320193"
YEARS_BACK = 3


def _upsert_period(db, company_id: str, normalized: dict) -> FinancialPeriod:
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


def _to_period_input(row: FinancialPeriod) -> FinancialPeriodInput:
    return FinancialPeriodInput(
        fiscal_year=row.fiscal_year,
        period_end_date=row.period_end_date,
        period_type=row.period_type,
        source=row.source,
        revenue=float(row.revenue) if row.revenue is not None else None,
        gross_profit=float(row.gross_profit) if row.gross_profit is not None else None,
        ebitda=float(row.ebitda) if row.ebitda is not None else None,
        ebit=float(row.ebit) if row.ebit is not None else None,
        net_income=float(row.net_income) if row.net_income is not None else None,
        operating_cash_flow=float(row.operating_cash_flow) if row.operating_cash_flow is not None else None,
        capex=float(row.capex) if row.capex is not None else None,
        total_debt=float(row.total_debt) if row.total_debt is not None else None,
        cash_and_equivalents=float(row.cash_and_equivalents) if row.cash_and_equivalents is not None else None,
        interest_expense=float(row.interest_expense) if row.interest_expense is not None else None,
        shares_outstanding=float(row.shares_outstanding) if row.shares_outstanding is not None else None,
    )


def main() -> None:
    ticker = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TICKER
    cik = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CIK

    init_db()
    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.ticker == ticker.upper()).first()
        if company is None:
            company = Company(ticker=ticker.upper(), name=ticker.upper(), cik=cik, reporting_currency="USD")
            db.add(company)
            db.commit()
            db.refresh(company)
            print(f"Created company {company.ticker} ({company.id})")
        else:
            print(f"Using existing company {company.ticker} ({company.id})")

        print(f"Fetching SEC EDGAR company facts for CIK {cik}...")
        facts = edgar_client.fetch_company_facts(cik, settings.edgar_user_agent)
        raw_periods = edgar_client.extract_annual_periods(facts)
        raw_periods = sorted(raw_periods, key=lambda p: p["fiscal_year"])[-YEARS_BACK:]
        print(f"  {len(raw_periods)} FY period(s) from SEC_EDGAR")

        if settings.fmp_api_key:
            print("Fetching FMP statements (supplementary)...")
            try:
                income = market_data_client.fetch_income_statement(ticker, settings.fmp_api_key, YEARS_BACK)
                balance = market_data_client.fetch_balance_sheet(ticker, settings.fmp_api_key, YEARS_BACK)
                cashflow = market_data_client.fetch_cash_flow(ticker, settings.fmp_api_key, YEARS_BACK)
                fmp_periods = market_data_client.extract_annual_periods(income, balance, cashflow)
                raw_periods.extend(fmp_periods)
                print(f"  {len(fmp_periods)} FY period(s) from FMP")
            except market_data_client.FmpClientError as exc:
                print(f"  skipping FMP: {exc}")
        else:
            print("FMP_API_KEY not set -- skipping supplementary source")

        normalized_periods, warnings = normalize.normalize_periods(
            raw_periods, currency=company.reporting_currency
        )
        for warning in warnings:
            print(f"  warning: {warning}")

        for normalized in normalized_periods:
            _upsert_period(db, company.id, normalized)
        db.commit()
        print(f"Ingested/updated {len(normalized_periods)} FinancialPeriod row(s) total")

        period_rows = db.query(FinancialPeriod).filter(FinancialPeriod.company_id == company.id).all()
        result = score_company(periods=[_to_period_input(p) for p in period_rows], assumptions=[])

        print(f"\nScreening score (formula {result.formula_version}): {result.score}/100")
        for factor in result.factors:
            print(
                f"  {factor.name:24s} weight={factor.weight:.2f} "
                f"score={factor.normalized_score:6.2f} source={factor.source:9s} {factor.notes}"
            )
        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  - {warning}")

        print(
            f"\nDone. Start apps/api (uvicorn app.main:app --reload) and GET "
            f"/companies/{company.id}/screening-score to see this via the API."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()

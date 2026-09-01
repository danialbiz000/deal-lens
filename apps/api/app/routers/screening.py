from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.assumption import Assumption
from app.models.company import Company
from app.models.financial_period import FinancialPeriod
from app.schemas.screening import ScreeningFactorOut, ScreeningScoreResponse
from finance_engine import AssumptionInput, FinancialPeriodInput, score_company

router = APIRouter(prefix="/companies", tags=["screening"])


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


def _to_assumption_input(row: Assumption) -> AssumptionInput:
    return AssumptionInput(
        name=row.name,
        value_numeric=float(row.value_numeric) if row.value_numeric is not None else None,
        value_text=row.value_text,
    )


@router.get("/{company_id}/screening-score", response_model=ScreeningScoreResponse)
def get_screening_score(company_id: str, db: Session = Depends(get_db)) -> ScreeningScoreResponse:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    period_rows = db.query(FinancialPeriod).filter(FinancialPeriod.company_id == company_id).all()
    if not period_rows:
        raise HTTPException(
            status_code=422,
            detail="no FinancialPeriod rows exist yet for this company; run /ingest first",
        )

    assumption_rows = db.query(Assumption).filter(Assumption.company_id == company_id).all()

    result = score_company(
        periods=[_to_period_input(p) for p in period_rows],
        assumptions=[_to_assumption_input(a) for a in assumption_rows],
    )

    return ScreeningScoreResponse(
        company_id=company_id,
        formula_version=result.formula_version,
        score=result.score,
        factors=[
            ScreeningFactorOut(
                name=f.name,
                weight=f.weight,
                normalized_score=f.normalized_score,
                source=f.source,
                contribution=f.contribution,
                notes=f.notes,
            )
            for f in result.factors
        ],
        warnings=result.warnings,
        computed_at=result.computed_at,
    )

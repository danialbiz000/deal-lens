from datetime import date, datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FinancialPeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    fiscal_year: int
    period_end_date: date
    period_type: str
    currency: str
    source: str
    source_ref: Optional[str] = None
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    net_income: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    total_debt: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    interest_expense: Optional[float] = None
    shares_outstanding: Optional[float] = None
    is_estimate: bool
    raw_payload: Optional[Any] = None
    ingested_at: datetime


class IngestRequest(BaseModel):
    years_back: int = Field(default=3, ge=1, le=10)
    sources: Optional[List[str]] = None  # defaults to both configured sources


class IngestResponse(BaseModel):
    company_id: str
    ingested_periods: int
    periods: List[FinancialPeriodRead]
    warnings: List[str]


class ManualFinancialPeriodCreate(BaseModel):
    """A private company has no SEC/EDGAR filing and (usually) no FMP market
    data either -- this is the only way its financials can enter DealLens.
    Always stored with source="MANUAL" and is_estimate=True, so it can never
    be mistaken for an audited public filing anywhere it's displayed
    (design doc's own auditability principle applies here too: unverified
    data must be labeled as such, not silently blended in).

    Sign convention matches every other source (design doc section 5):
    capex and total_debt are positive magnitudes regardless of how the
    analyst is used to writing them elsewhere; this endpoint normalizes
    that for you rather than rejecting a negative value outright.
    """

    fiscal_year: int = Field(gt=1900, lt=2200)
    period_end_date: date
    period_type: str = Field(default="FY")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    source_ref: Optional[str] = Field(
        default=None, max_length=255, description="e.g. 'management-provided FY2025 draft P&L', 'per CIM dated ...'"
    )
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    ebitda: Optional[float] = None
    ebit: Optional[float] = None
    net_income: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    total_debt: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    interest_expense: Optional[float] = None
    shares_outstanding: Optional[float] = None

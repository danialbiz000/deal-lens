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

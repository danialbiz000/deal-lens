from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=16)
    name: str = Field(..., min_length=1, max_length=255)
    cik: Optional[str] = Field(default=None, max_length=10)
    sector: Optional[str] = Field(default=None, max_length=100)
    industry: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    reporting_currency: str = Field(default="USD", min_length=3, max_length=3)
    description: Optional[str] = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticker: str
    cik: Optional[str] = None
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    reporting_currency: str
    description: Optional[str] = None
    market_cap: Optional[float] = None
    share_price: Optional[float] = None
    market_data_as_of: Optional[date] = None
    market_data_source: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CompanyDetail(CompanyRead):
    latest_financial_period: Optional["FinancialPeriodRead"] = None


from app.schemas.financial_period import FinancialPeriodRead  # noqa: E402

CompanyDetail.model_rebuild()

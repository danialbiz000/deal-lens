"""Plain-data input/output types for the finance engine.

Deliberately plain dataclasses, not ORM models or Pydantic schemas -- this
package must not depend on SQLAlchemy or FastAPI (see package docstring).
Callers (apps/api) are responsible for mapping their own ORM rows into these
types before calling into `finance_engine`.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class FinancialPeriodInput:
    """One reporting period's worth of raw financials.

    Mirrors the subset of the `financial_periods` table columns that the
    scoring math actually needs. Money fields are plain float/int here --
    the DB layer is responsible for Numeric precision; by the time a value
    reaches this package it is just a number to compute with.
    """

    fiscal_year: int
    period_end_date: date
    period_type: str  # "FY", "Q1".."Q4", or "TTM"
    source: str  # "SEC_EDGAR" | "ALPHA_VANTAGE" | "FMP" | "MANUAL"
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


@dataclass(frozen=True)
class AssumptionInput:
    """One analyst-supplied (or default) assumption row."""

    name: str
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None


@dataclass(frozen=True)
class FactorResult:
    """Output of a single computable-factor function (factors.py)."""

    normalized_score: float  # 0-100
    notes: str
    warning: Optional[str] = None


@dataclass(frozen=True)
class CompanySnapshotInput:
    """Latest-FY snapshot of one company for comps purposes (Phase 2).

    `company_id` is caller-defined (the API layer passes its Company.id) --
    finance_engine treats it as an opaque label, never a DB lookup key.
    """

    company_id: str
    sector: Optional[str]
    industry: Optional[str]
    revenue: Optional[float]
    ebitda: Optional[float]
    market_cap: Optional[float]
    total_debt: Optional[float]
    cash_and_equivalents: Optional[float]

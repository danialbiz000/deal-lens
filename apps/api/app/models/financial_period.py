import uuid

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class FinancialPeriod(Base):
    __tablename__ = "financial_periods"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "period_end_date", "period_type", "source", name="uq_financial_period_identity"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)

    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_end_date: Mapped["object"] = mapped_column(Date, nullable=False)
    period_type: Mapped[str] = mapped_column(String(4), nullable=False)  # FY, Q1..Q4, TTM
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # SEC_EDGAR | ALPHA_VANTAGE | FMP | MANUAL
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    revenue: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=True)
    gross_profit: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=True)
    ebitda: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=True)
    ebit: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=True)
    net_income: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=True)
    operating_cash_flow: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=True)
    capex: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=True)  # positive magnitude (outflow)
    total_debt: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=True)
    cash_and_equivalents: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=True)
    interest_expense: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=True)
    shares_outstanding: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=True)

    is_estimate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    raw_payload: Mapped["object"] = mapped_column(JSON, nullable=True)
    ingested_at: Mapped["object"] = mapped_column(DateTime, nullable=False, server_default=func.now())

    company = relationship("Company", back_populates="financial_periods")

    # Deliberately NOT stored: net_debt, free_cash_flow, net_working_capital.
    # These are always derived by finance_engine from the raw fields above
    # (design doc section 2.2) so there is exactly one place the formula
    # lives.

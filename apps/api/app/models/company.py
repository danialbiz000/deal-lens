import uuid

from sqlalchemy import Date, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticker: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    cik: Mapped[str | None] = mapped_column(String(10), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    reporting_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Phase 2 additions (docs/phase2-comps-lbo-design.md section 1.1):
    # latest known market snapshot, refreshed on every /ingest call. Not a
    # price-history entity -- this is deal screening, not a trading terminal.
    market_cap: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=True)
    share_price: Mapped["object"] = mapped_column(Numeric(12, 4), nullable=True)
    market_data_as_of: Mapped["object"] = mapped_column(Date, nullable=True)
    market_data_source: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped["object"] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped["object"] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    financial_periods = relationship(
        "FinancialPeriod", back_populates="company", cascade="all, delete-orphan"
    )
    assumptions = relationship("Assumption", back_populates="company", cascade="all, delete-orphan")

import uuid

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class Scenario(Base):
    __tablename__ = "scenarios"
    __table_args__ = (UniqueConstraint("company_id", "case_type", name="uq_scenario_company_case_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)

    case_type: Mapped[str] = mapped_column(String(4), nullable=False)  # BASE | BULL | BEAR
    revenue_growth_rate: Mapped["object"] = mapped_column(Numeric(6, 4), nullable=False)
    ebitda_margin_delta: Mapped["object"] = mapped_column(Numeric(6, 4), nullable=False)
    exit_multiple_delta: Mapped["object"] = mapped_column(Numeric(6, 4), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)  # default:spec_calibration | manual:analyst
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped["object"] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped["object"] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    company = relationship("Company")

import uuid

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class LboCase(Base):
    """A computed-artifact snapshot, not a wide flat table of every input
    (design doc section 1.4): full inputs and the year-by-year schedule
    live in JSON columns so the whole waterfall is inspectable without
    recomputation, while key outputs get real columns for querying.
    """

    __tablename__ = "lbo_cases"
    __table_args__ = (UniqueConstraint("company_id", "scenario_id", name="uq_lbo_case_company_scenario"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenarios.id"), nullable=False, index=True)

    formula_version: Mapped[str] = mapped_column(String(20), nullable=False)  # lbo_v0.1

    inputs_json: Mapped["object"] = mapped_column(JSON, nullable=False)
    sources_uses_json: Mapped["object"] = mapped_column(JSON, nullable=False)
    schedule_json: Mapped["object"] = mapped_column(JSON, nullable=False)
    value_creation_bridge_json: Mapped["object"] = mapped_column(JSON, nullable=False)

    entry_ev: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=False)
    exit_ev: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=False)
    exit_equity_value: Mapped["object"] = mapped_column(Numeric(20, 2), nullable=False)
    moic: Mapped["object"] = mapped_column(Numeric(10, 4), nullable=False)
    irr: Mapped["object"] = mapped_column(Numeric(10, 4), nullable=False)
    entry_leverage: Mapped["object"] = mapped_column(Numeric(6, 2), nullable=False)
    exit_leverage: Mapped["object"] = mapped_column(Numeric(6, 2), nullable=False)

    computed_at: Mapped["object"] = mapped_column(DateTime, nullable=False, server_default=func.now())
    created_at: Mapped["object"] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped["object"] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    company = relationship("Company")
    scenario = relationship("Scenario")

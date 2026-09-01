import uuid

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class IcSimulation(Base):
    """Append-only and versioned, same rationale as Memo (design doc
    section 6)."""

    __tablename__ = "ic_simulations"
    __table_args__ = (UniqueConstraint("company_id", "version", name="uq_ic_simulation_company_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    model: Mapped[str] = mapped_column(String(50), nullable=False)

    source_bundle_json: Mapped["object"] = mapped_column(JSON, nullable=False)
    transcript_json: Mapped["object"] = mapped_column(JSON, nullable=False)  # ordered 5-role array

    llm_recommendation: Mapped[str] = mapped_column(String(15), nullable=False)  # raw IC Chair output, pre-override
    recommendation: Mapped[str] = mapped_column(String(15), nullable=False)  # final, possibly-overridden value
    override_fired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)  # populated iff override_fired

    key_strengths_json: Mapped["object"] = mapped_column(JSON, nullable=False)
    key_risks_json: Mapped["object"] = mapped_column(JSON, nullable=False)
    unanswered_dd_json: Mapped["object"] = mapped_column(JSON, nullable=False)

    generated_at: Mapped["object"] = mapped_column(DateTime, nullable=False)
    created_at: Mapped["object"] = mapped_column(DateTime, nullable=False, server_default=func.now())

    company = relationship("Company")

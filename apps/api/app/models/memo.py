import uuid

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class Memo(Base):
    """Append-only and versioned (design doc section 6) -- a deliberate
    departure from Phase 0/2's upsert-in-place pattern, since the spec
    wants memo reproducibility across regenerations, not just current
    state. Regenerating creates a new row with version = max(existing) + 1;
    old versions remain individually fetchable.
    """

    __tablename__ = "memos"
    __table_args__ = (UniqueConstraint("company_id", "version", name="uq_memo_company_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. memo_prompt_v0.1
    model: Mapped[str] = mapped_column(String(50), nullable=False)  # resolved model id actually used

    source_bundle_json: Mapped["object"] = mapped_column(JSON, nullable=False)
    sections_json: Mapped["object"] = mapped_column(JSON, nullable=False)
    validation_report_json: Mapped["object"] = mapped_column(JSON, nullable=False)

    generated_at: Mapped["object"] = mapped_column(DateTime, nullable=False)
    created_at: Mapped["object"] = mapped_column(DateTime, nullable=False, server_default=func.now())

    company = relationship("Company")

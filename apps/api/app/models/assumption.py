import uuid

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class Assumption(Base):
    __tablename__ = "assumptions"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_assumption_company_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    value_numeric: Mapped["object"] = mapped_column(Numeric(10, 4), nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped["object"] = mapped_column(Numeric(3, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped["object"] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped["object"] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    company = relationship("Company", back_populates="assumptions")

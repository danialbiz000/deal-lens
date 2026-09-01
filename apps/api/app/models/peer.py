import uuid

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class Peer(Base):
    """A relationship row between a target Company and a peer Company --
    NOT a separate identity entity (design doc section 1.2): every peer is
    a full row in `companies`, ingested through the same EDGAR/FMP pipeline
    as any target.
    """

    __tablename__ = "peers"
    __table_args__ = (UniqueConstraint("target_company_id", "peer_company_id", name="uq_peer_target_candidate"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target_company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    peer_company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(10), nullable=False)  # CANDIDATE | SELECTED | REJECTED
    reason_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reason_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    similarity_score: Mapped["object"] = mapped_column(Numeric(5, 2), nullable=True)
    ev_revenue_multiple: Mapped["object"] = mapped_column(Numeric(10, 4), nullable=True)
    ev_ebitda_multiple: Mapped["object"] = mapped_column(Numeric(10, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)  # auto:top_k_similarity | manual:analyst
    computed_at: Mapped["object"] = mapped_column(DateTime, nullable=False, server_default=func.now())

    created_at: Mapped["object"] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped["object"] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    target_company = relationship("Company", foreign_keys=[target_company_id])
    peer_company = relationship("Company", foreign_keys=[peer_company_id])

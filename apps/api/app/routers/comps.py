"""Comparable-companies peer generation/selection + entry valuation.

Design doc: docs/phase2-comps-lbo-design.md sections 2 and 7.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.company import Company
from app.models.financial_period import FinancialPeriod
from app.models.peer import Peer
from app.schemas.peer import PeerGenerateResponse, PeerPatch, PeerRead, ValuationResponse
from finance_engine import CompanySnapshotInput, compute_valuation, evaluate_peer, select_top_peers
from finance_engine.constants import COMPS_MIN_PEERS_FOR_VALUATION

router = APIRouter(prefix="/companies", tags=["comps"])


def _latest_fy_period(db: Session, company_id: str) -> Optional[FinancialPeriod]:
    return (
        db.query(FinancialPeriod)
        .filter(FinancialPeriod.company_id == company_id, FinancialPeriod.period_type == "FY")
        .order_by(FinancialPeriod.fiscal_year.desc())
        .first()
    )


def _to_snapshot(db: Session, company: Company) -> CompanySnapshotInput:
    latest = _latest_fy_period(db, company.id)
    return CompanySnapshotInput(
        company_id=company.id,
        sector=company.sector,
        industry=company.industry,
        revenue=float(latest.revenue) if latest and latest.revenue is not None else None,
        ebitda=float(latest.ebitda) if latest and latest.ebitda is not None else None,
        market_cap=float(company.market_cap) if company.market_cap is not None else None,
        total_debt=float(latest.total_debt) if latest and latest.total_debt is not None else None,
        cash_and_equivalents=(
            float(latest.cash_and_equivalents) if latest and latest.cash_and_equivalents is not None else None
        ),
    )


def _peer_to_read(peer: Peer, peer_company: Optional[Company]) -> PeerRead:
    return PeerRead(
        id=peer.id,
        target_company_id=peer.target_company_id,
        peer_company_id=peer.peer_company_id,
        peer_ticker=peer_company.ticker if peer_company else None,
        peer_name=peer_company.name if peer_company else None,
        status=peer.status,
        reason_code=peer.reason_code,
        reason_notes=peer.reason_notes,
        similarity_score=float(peer.similarity_score) if peer.similarity_score is not None else None,
        ev_revenue_multiple=float(peer.ev_revenue_multiple) if peer.ev_revenue_multiple is not None else None,
        ev_ebitda_multiple=float(peer.ev_ebitda_multiple) if peer.ev_ebitda_multiple is not None else None,
        source=peer.source,
        computed_at=peer.computed_at,
        created_at=peer.created_at,
        updated_at=peer.updated_at,
    )


@router.post("/{company_id}/peers/generate", response_model=PeerGenerateResponse)
def generate_peers(company_id: str, db: Session = Depends(get_db)) -> PeerGenerateResponse:
    target = db.get(Company, company_id)
    if target is None:
        raise HTTPException(status_code=404, detail="company not found")
    if not target.sector:
        raise HTTPException(
            status_code=422, detail="target company has no sector set -- required for peer generation"
        )

    target_snapshot = _to_snapshot(db, target)
    if target_snapshot.revenue is None or target_snapshot.ebitda is None:
        raise HTTPException(
            status_code=422,
            detail="target company has no FY FinancialPeriod with revenue and ebitda -- run /ingest first",
        )

    candidates = db.query(Company).filter(Company.id != company_id).all()
    existing_peer_rows = {
        p.peer_company_id: p for p in db.query(Peer).filter(Peer.target_company_id == company_id).all()
    }

    evaluations = [evaluate_peer(target_snapshot, _to_snapshot(db, candidate)) for candidate in candidates]
    selected_ids = set(select_top_peers(evaluations))

    saved_peers: List[Peer] = []
    for evaluation in evaluations:
        existing = existing_peer_rows.get(evaluation.peer_company_id)
        manual_override = existing is not None and existing.source == "manual:analyst"

        if existing is None:
            existing = Peer(target_company_id=company_id, peer_company_id=evaluation.peer_company_id)
            db.add(existing)

        # Refresh the raw computed snapshot regardless of override status --
        # freshness of the underlying numbers is separate from an analyst's
        # status decision.
        existing.similarity_score = evaluation.similarity_score
        existing.ev_revenue_multiple = evaluation.ev_revenue_multiple
        existing.ev_ebitda_multiple = evaluation.ev_ebitda_multiple
        existing.computed_at = datetime.now(timezone.utc)

        if manual_override:
            # Idempotency requirement (design doc acceptance criteria):
            # regenerating must never change an existing manual override's
            # status/source/reason -- only the snapshot numbers above.
            pass
        elif evaluation.status == "REJECTED":
            existing.status = "REJECTED"
            existing.reason_code = evaluation.reason_code
            existing.reason_notes = None
            existing.source = "auto:top_k_similarity"
        elif evaluation.peer_company_id in selected_ids:
            existing.status = "SELECTED"
            existing.reason_code = None
            existing.reason_notes = None
            existing.source = "auto:top_k_similarity"
        else:
            existing.status = "CANDIDATE"
            existing.reason_code = None
            existing.reason_notes = None
            existing.source = "auto:top_k_similarity"

        saved_peers.append(existing)

    db.commit()
    for row in saved_peers:
        db.refresh(row)

    peer_companies: Dict[str, Company] = {c.id: c for c in candidates}
    peer_reads = [_peer_to_read(p, peer_companies.get(p.peer_company_id)) for p in saved_peers]
    selected_count = sum(1 for p in saved_peers if p.status == "SELECTED")

    return PeerGenerateResponse(
        target_company_id=company_id, peers=peer_reads, selected_count=selected_count, warnings=[]
    )


@router.get("/{company_id}/peers", response_model=List[PeerRead])
def list_peers(
    company_id: str, status: Optional[str] = Query(default=None), db: Session = Depends(get_db)
) -> List[PeerRead]:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    query = db.query(Peer).filter(Peer.target_company_id == company_id)
    if status:
        query = query.filter(Peer.status == status.upper())
    peers = query.all()
    peers.sort(key=lambda p: (p.similarity_score is None, -(float(p.similarity_score) if p.similarity_score is not None else 0)))

    peer_company_ids = [p.peer_company_id for p in peers]
    peer_companies = (
        {c.id: c for c in db.query(Company).filter(Company.id.in_(peer_company_ids)).all()}
        if peer_company_ids
        else {}
    )

    return [_peer_to_read(p, peer_companies.get(p.peer_company_id)) for p in peers]


@router.patch("/{company_id}/peers/{peer_id}", response_model=PeerRead)
def patch_peer(company_id: str, peer_id: str, payload: PeerPatch, db: Session = Depends(get_db)) -> PeerRead:
    peer = db.query(Peer).filter(Peer.id == peer_id, Peer.target_company_id == company_id).first()
    if peer is None:
        raise HTTPException(status_code=404, detail="peer not found")

    peer.status = payload.status
    peer.reason_notes = payload.reason_notes
    peer.source = "manual:analyst"
    if payload.status != "REJECTED":
        peer.reason_code = None

    db.commit()
    db.refresh(peer)

    peer_company = db.get(Company, peer.peer_company_id)
    return _peer_to_read(peer, peer_company)


@router.get("/{company_id}/valuation", response_model=ValuationResponse)
def get_valuation(company_id: str, db: Session = Depends(get_db)) -> ValuationResponse:
    target = db.get(Company, company_id)
    if target is None:
        raise HTTPException(status_code=404, detail="company not found")

    target_snapshot = _to_snapshot(db, target)
    if target_snapshot.revenue is None or target_snapshot.ebitda is None:
        raise HTTPException(status_code=422, detail="target company has no FY financials -- run /ingest first")

    selected_peers = (
        db.query(Peer).filter(Peer.target_company_id == company_id, Peer.status == "SELECTED").all()
    )
    multiples = [
        (float(p.ev_revenue_multiple), float(p.ev_ebitda_multiple))
        for p in selected_peers
        if p.ev_revenue_multiple is not None and p.ev_ebitda_multiple is not None
    ]

    if len(multiples) < COMPS_MIN_PEERS_FOR_VALUATION:
        raise HTTPException(
            status_code=422,
            detail=(
                f"at least {COMPS_MIN_PEERS_FOR_VALUATION} SELECTED peers with valid multiples are required "
                f"for valuation (have {len(multiples)}) -- run /peers/generate first"
            ),
        )

    result = compute_valuation(
        multiples,
        target_revenue=target_snapshot.revenue,
        target_ebitda=target_snapshot.ebitda,
        target_total_debt=target_snapshot.total_debt or 0.0,
        target_cash_and_equivalents=target_snapshot.cash_and_equivalents or 0.0,
    )

    return ValuationResponse(
        company_id=company_id,
        peer_count=result.peer_count,
        median_ev_revenue=result.median_ev_revenue,
        q1_ev_revenue=result.q1_ev_revenue,
        q3_ev_revenue=result.q3_ev_revenue,
        median_ev_ebitda=result.median_ev_ebitda,
        q1_ev_ebitda=result.q1_ev_ebitda,
        q3_ev_ebitda=result.q3_ev_ebitda,
        implied_ev_from_revenue=result.implied_ev_from_revenue,
        implied_ev_from_ebitda=result.implied_ev_from_ebitda,
        entry_ev=result.entry_ev,
        entry_net_debt=result.entry_net_debt,
        entry_equity_value=result.entry_equity_value,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )

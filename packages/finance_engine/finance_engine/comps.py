"""Comparable-companies similarity scoring + valuation multiples math.

Pure Python, zero I/O/DB dependency -- same discipline as screening.py.
The API layer resolves each Company's latest-FY FinancialPeriod into a
`CompanySnapshotInput` and calls into this module; this module never
touches the database or the peer-candidate universe question (which
companies exist to compare against) at all.
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .constants import (
    COMPS_INDUSTRY_MATCH_POINTS,
    COMPS_MARGIN_GAP_CEILING,
    COMPS_MARGIN_MAX_POINTS,
    COMPS_MIN_PEERS_FOR_VALUATION,
    COMPS_REVENUE_SCALE_MISMATCH_MAX_RATIO,
    COMPS_REVENUE_SCALE_MISMATCH_MIN_RATIO,
    COMPS_SCALE_MAX_POINTS,
    COMPS_SECTOR_MATCH_POINTS,
    COMPS_TOP_K,
    COMPS_MIN_SELECTED_SCORE,
    REASON_MISSING_FINANCIALS,
    REASON_REVENUE_SCALE_MISMATCH,
    REASON_SELF,
)
from .factors import clamp
from .types import CompanySnapshotInput


@dataclass(frozen=True)
class PeerEvaluation:
    peer_company_id: str
    status: str  # "REJECTED" | "CANDIDATE" -- promotion to "SELECTED" happens in select_top_peers
    reason_code: Optional[str]
    similarity_score: Optional[float]
    ev_revenue_multiple: Optional[float]
    ev_ebitda_multiple: Optional[float]


def compute_enterprise_value(market_cap: float, total_debt: float, cash_and_equivalents: float) -> float:
    return market_cap + total_debt - cash_and_equivalents


def evaluate_peer(target: CompanySnapshotInput, candidate: CompanySnapshotInput) -> PeerEvaluation:
    """Apply the hard filters (design doc section 2.2), then score
    similarity for anything that passes (section 2.3).
    """
    if candidate.company_id == target.company_id:
        return PeerEvaluation(candidate.company_id, "REJECTED", REASON_SELF, None, None, None)

    missing = (
        candidate.revenue is None
        or candidate.ebitda is None
        or candidate.market_cap is None
        or target.revenue is None
        or target.ebitda is None
        or candidate.revenue <= 0
        or target.revenue <= 0
    )
    if missing:
        return PeerEvaluation(candidate.company_id, "REJECTED", REASON_MISSING_FINANCIALS, None, None, None)

    revenue_ratio = candidate.revenue / target.revenue  # type: ignore[operator]
    if not (COMPS_REVENUE_SCALE_MISMATCH_MIN_RATIO <= revenue_ratio <= COMPS_REVENUE_SCALE_MISMATCH_MAX_RATIO):
        return PeerEvaluation(candidate.company_id, "REJECTED", REASON_REVENUE_SCALE_MISMATCH, None, None, None)

    sector_score = COMPS_SECTOR_MATCH_POINTS if (target.sector and candidate.sector == target.sector) else 0.0
    industry_score = (
        COMPS_INDUSTRY_MATCH_POINTS if (target.industry and candidate.industry == target.industry) else 0.0
    )

    log_ratio = abs(math.log(revenue_ratio))
    scale_score = clamp(
        COMPS_SCALE_MAX_POINTS * (1 - log_ratio / math.log(COMPS_REVENUE_SCALE_MISMATCH_MAX_RATIO)),
        0,
        COMPS_SCALE_MAX_POINTS,
    )

    peer_margin = candidate.ebitda / candidate.revenue  # type: ignore[operator]
    target_margin = target.ebitda / target.revenue  # type: ignore[operator]
    margin_diff = abs(peer_margin - target_margin)
    margin_score = clamp(
        COMPS_MARGIN_MAX_POINTS * (1 - margin_diff / COMPS_MARGIN_GAP_CEILING), 0, COMPS_MARGIN_MAX_POINTS
    )

    similarity_score = sector_score + industry_score + scale_score + margin_score

    ev = compute_enterprise_value(
        candidate.market_cap,  # type: ignore[arg-type]
        candidate.total_debt or 0.0,
        candidate.cash_and_equivalents or 0.0,
    )
    ev_revenue_multiple = ev / candidate.revenue  # type: ignore[operator]
    ev_ebitda_multiple = ev / candidate.ebitda if candidate.ebitda and candidate.ebitda > 0 else None

    return PeerEvaluation(
        peer_company_id=candidate.company_id,
        status="CANDIDATE",
        reason_code=None,
        similarity_score=round(similarity_score, 2),
        ev_revenue_multiple=ev_revenue_multiple,
        ev_ebitda_multiple=ev_ebitda_multiple,
    )


def select_top_peers(
    evaluations: Sequence[PeerEvaluation], top_k: int = COMPS_TOP_K, min_score: float = COMPS_MIN_SELECTED_SCORE
) -> List[str]:
    """Return the peer_company_ids to auto-promote to SELECTED: candidates
    (post-hard-filter) with score >= min_score, top_k by score descending.
    """
    eligible = [
        e for e in evaluations if e.status == "CANDIDATE" and e.similarity_score is not None and e.similarity_score >= min_score
    ]
    eligible.sort(key=lambda e: e.similarity_score, reverse=True)  # type: ignore[arg-type,return-value]
    return [e.peer_company_id for e in eligible[:top_k]]


def _quantile(sorted_values: List[float], q: float) -> float:
    """Linear-interpolation quantile (same convention as numpy's default)."""
    if not sorted_values:
        raise ValueError("cannot compute a quantile of an empty list")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return sorted_values[int(pos)]
    fraction = pos - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


@dataclass(frozen=True)
class ValuationResult:
    median_ev_revenue: float
    q1_ev_revenue: float
    q3_ev_revenue: float
    median_ev_ebitda: float
    q1_ev_ebitda: float
    q3_ev_ebitda: float
    implied_ev_from_revenue: float
    implied_ev_from_ebitda: float
    entry_ev: float
    entry_net_debt: float
    entry_equity_value: float
    peer_count: int


def compute_valuation(
    selected_peer_multiples: Sequence[Tuple[float, float]],  # (ev_revenue_multiple, ev_ebitda_multiple)
    target_revenue: float,
    target_ebitda: float,
    target_total_debt: float,
    target_cash_and_equivalents: float,
) -> ValuationResult:
    """Median/quartile multiples from SELECTED peers only, and the implied
    entry EV/equity bridge for the target (design doc section 2.5).

    Raises ValueError if fewer than COMPS_MIN_PEERS_FOR_VALUATION peer
    multiples are supplied -- callers (the API layer) turn this into a 422.
    """
    if len(selected_peer_multiples) < COMPS_MIN_PEERS_FOR_VALUATION:
        raise ValueError(
            f"at least {COMPS_MIN_PEERS_FOR_VALUATION} selected peers with valid multiples are required "
            f"for valuation, got {len(selected_peer_multiples)}"
        )

    ev_revenue_values = sorted(m[0] for m in selected_peer_multiples)
    ev_ebitda_values = sorted(m[1] for m in selected_peer_multiples)

    median_ev_revenue = _quantile(ev_revenue_values, 0.5)
    q1_ev_revenue = _quantile(ev_revenue_values, 0.25)
    q3_ev_revenue = _quantile(ev_revenue_values, 0.75)
    median_ev_ebitda = _quantile(ev_ebitda_values, 0.5)
    q1_ev_ebitda = _quantile(ev_ebitda_values, 0.25)
    q3_ev_ebitda = _quantile(ev_ebitda_values, 0.75)

    implied_ev_from_revenue = median_ev_revenue * target_revenue
    implied_ev_from_ebitda = median_ev_ebitda * target_ebitda

    entry_ev = implied_ev_from_ebitda  # EV/EBITDA is the PE convention; EV/Revenue is a cross-check only
    entry_net_debt = target_total_debt - target_cash_and_equivalents
    entry_equity_value = entry_ev - entry_net_debt

    return ValuationResult(
        median_ev_revenue=median_ev_revenue,
        q1_ev_revenue=q1_ev_revenue,
        q3_ev_revenue=q3_ev_revenue,
        median_ev_ebitda=median_ev_ebitda,
        q1_ev_ebitda=q1_ev_ebitda,
        q3_ev_ebitda=q3_ev_ebitda,
        implied_ev_from_revenue=implied_ev_from_revenue,
        implied_ev_from_ebitda=implied_ev_from_ebitda,
        entry_ev=entry_ev,
        entry_net_debt=entry_net_debt,
        entry_equity_value=entry_equity_value,
        peer_count=len(selected_peer_multiples),
    )

import math

import pytest

from finance_engine.comps import compute_enterprise_value, compute_valuation, evaluate_peer, select_top_peers
from finance_engine.constants import REASON_MISSING_FINANCIALS, REASON_REVENUE_SCALE_MISMATCH, REASON_SELF
from finance_engine.types import CompanySnapshotInput


def snap(company_id, sector="Tech", industry="Software", revenue=100.0, ebitda=20.0,
         market_cap=500.0, total_debt=50.0, cash=20.0):
    return CompanySnapshotInput(
        company_id=company_id, sector=sector, industry=industry, revenue=revenue, ebitda=ebitda,
        market_cap=market_cap, total_debt=total_debt, cash_and_equivalents=cash,
    )


def test_compute_enterprise_value():
    assert compute_enterprise_value(market_cap=500, total_debt=100, cash_and_equivalents=50) == 550


def test_evaluate_peer_self_rejected():
    target = snap("A")
    result = evaluate_peer(target, snap("A"))
    assert result.status == "REJECTED"
    assert result.reason_code == REASON_SELF


def test_evaluate_peer_missing_financials_rejected():
    target = snap("A")
    candidate = snap("B", revenue=None, ebitda=None)
    result = evaluate_peer(target, candidate)
    assert result.status == "REJECTED"
    assert result.reason_code == REASON_MISSING_FINANCIALS


def test_evaluate_peer_missing_market_cap_rejected():
    target = snap("A")
    candidate = snap("B", market_cap=None)
    result = evaluate_peer(target, candidate)
    assert result.status == "REJECTED"
    assert result.reason_code == REASON_MISSING_FINANCIALS


def test_evaluate_peer_revenue_scale_mismatch_rejected():
    target = snap("A", revenue=100.0)
    too_big = snap("B", revenue=400.0)  # 4x > 3x ceiling
    too_small = snap("C", revenue=20.0)  # 0.2x < 1/3 floor
    assert evaluate_peer(target, too_big).reason_code == REASON_REVENUE_SCALE_MISMATCH
    assert evaluate_peer(target, too_small).reason_code == REASON_REVENUE_SCALE_MISMATCH


def test_evaluate_peer_at_scale_boundary_is_accepted():
    # Exactly at the 3x hard-filter boundary: still a CANDIDATE (not rejected),
    # but scale_score must be exactly 0 per design doc section 2.3 ("3x or
    # 1/3x apart -> 0 pts"). Margin held identical (same ebitda/revenue ratio)
    # to isolate scale_score cleanly: total = sector(50) + industry(20) +
    # scale(0) + margin(15, identical margin) = 85.
    target = snap("A", revenue=100.0, ebitda=20.0)
    exactly_3x = snap("B", revenue=300.0, ebitda=60.0)  # same 20% margin as target
    result = evaluate_peer(target, exactly_3x)
    assert result.status == "CANDIDATE"
    assert result.similarity_score == pytest.approx(85.0, abs=0.01)


def test_evaluate_peer_identical_company_scores_high():
    target = snap("A", sector="Tech", industry="Software", revenue=100.0, ebitda=20.0)
    identical_twin = snap("B", sector="Tech", industry="Software", revenue=100.0, ebitda=20.0)
    result = evaluate_peer(target, identical_twin)
    assert result.status == "CANDIDATE"
    # sector(50) + industry(20) + scale(15, identical rev) + margin(15, identical margin) = 100
    assert result.similarity_score == pytest.approx(100.0, abs=0.01)


def test_evaluate_peer_different_sector_and_industry_scores_lower():
    target = snap("A", sector="Tech", industry="Software")
    other = snap("B", sector="Healthcare", industry="Pharma")
    result = evaluate_peer(target, other)
    assert result.status == "CANDIDATE"
    assert result.similarity_score < 50.0  # no sector/industry points, only scale+margin


def test_evaluate_peer_multiples_computed_correctly():
    target = snap("A")
    candidate = snap("B", revenue=200.0, ebitda=40.0, market_cap=600.0, total_debt=100.0, cash=50.0)
    result = evaluate_peer(target, candidate)
    # ev = 600 + 100 - 50 = 650
    assert result.ev_revenue_multiple == pytest.approx(650 / 200)
    assert result.ev_ebitda_multiple == pytest.approx(650 / 40)


def test_select_top_peers_respects_min_score_and_top_k():
    target = snap("target", sector="Tech", industry="Software", revenue=100.0, ebitda=20.0)
    # 6 identical-twin candidates (score 100) + 1 low-scoring candidate
    evaluations = [evaluate_peer(target, snap(f"peer{i}", sector="Tech", industry="Software",
                                               revenue=100.0, ebitda=20.0)) for i in range(6)]
    low_score = evaluate_peer(target, snap("low", sector="Healthcare", industry="Pharma", revenue=300.0, ebitda=1.0))
    evaluations.append(low_score)

    selected = select_top_peers(evaluations, top_k=5, min_score=50.0)
    assert len(selected) == 5
    assert "low" not in selected


def test_select_top_peers_excludes_rejected():
    target = snap("target")
    rejected = evaluate_peer(target, snap("rej", revenue=None, ebitda=None))
    good = evaluate_peer(target, snap("good"))
    selected = select_top_peers([rejected, good])
    assert selected == ["good"]


# --- compute_valuation ---


def test_compute_valuation_normal_case():
    multiples = [(3.0, 10.0), (3.5, 11.0), (4.0, 12.0)]
    result = compute_valuation(
        multiples, target_revenue=100.0, target_ebitda=20.0, target_total_debt=50.0, target_cash_and_equivalents=10.0
    )
    assert result.median_ev_ebitda == pytest.approx(11.0)
    assert result.implied_ev_from_ebitda == pytest.approx(11.0 * 20.0)
    assert result.entry_ev == pytest.approx(220.0)
    assert result.entry_net_debt == pytest.approx(40.0)
    assert result.entry_equity_value == pytest.approx(180.0)
    assert result.peer_count == 3


def test_compute_valuation_too_few_peers_raises():
    with pytest.raises(ValueError):
        compute_valuation([(3.0, 10.0)], target_revenue=100, target_ebitda=20, target_total_debt=0, target_cash_and_equivalents=0)


def test_compute_valuation_exactly_two_peers_works():
    result = compute_valuation(
        [(3.0, 10.0), (4.0, 12.0)], target_revenue=100.0, target_ebitda=20.0,
        target_total_debt=0.0, target_cash_and_equivalents=0.0,
    )
    assert result.median_ev_ebitda == pytest.approx(11.0)  # midpoint of 2 values

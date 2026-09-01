"""Unit tests for the deterministic bear-case gate (Phase 4).

Per docs/phase4-ai-layer-design.md section 9: >=5 constructed scenarios --
one passing all thresholds, and one failing each threshold individually.
"""

import pytest

from finance_engine.ic_gate import (
    BEAR_EXIT_LEVERAGE_CEILING,
    BEAR_IRR_FLOOR,
    BEAR_MOIC_FLOOR,
    BearCaseInput,
    BearCaseYear,
    evaluate_bear_case_thresholds,
)


def make_bear_case(irr=0.10, moic=1.2, exit_leverage=3.0, schedule=None):
    if schedule is None:
        schedule = [
            BearCaseYear(year=0, ebitda=100.0, interest=None),
            BearCaseYear(year=1, ebitda=90.0, interest=40.0),
            BearCaseYear(year=2, ebitda=95.0, interest=35.0),
        ]
    return BearCaseInput(irr=irr, moic=moic, exit_leverage=exit_leverage, schedule=schedule)


def test_gate_passes_all_thresholds():
    result = evaluate_bear_case_thresholds(make_bear_case())
    assert result.passes is True
    assert result.failures == []


def test_gate_fails_irr_floor():
    result = evaluate_bear_case_thresholds(make_bear_case(irr=0.05))
    assert result.passes is False
    assert any("IRR" in f for f in result.failures)


def test_gate_passes_at_exact_irr_floor():
    # Boundary: exactly at the floor should pass (< floor fails, not <=).
    result = evaluate_bear_case_thresholds(make_bear_case(irr=BEAR_IRR_FLOOR))
    assert result.passes is True


def test_gate_fails_moic_floor():
    result = evaluate_bear_case_thresholds(make_bear_case(moic=0.85))
    assert result.passes is False
    assert any("MOIC" in f for f in result.failures)


def test_gate_passes_at_exact_moic_floor():
    result = evaluate_bear_case_thresholds(make_bear_case(moic=BEAR_MOIC_FLOOR))
    assert result.passes is True


def test_gate_fails_exit_leverage_ceiling():
    result = evaluate_bear_case_thresholds(make_bear_case(exit_leverage=7.5))
    assert result.passes is False
    assert any("leverage" in f for f in result.failures)


def test_gate_passes_at_exact_exit_leverage_ceiling():
    result = evaluate_bear_case_thresholds(make_bear_case(exit_leverage=BEAR_EXIT_LEVERAGE_CEILING))
    assert result.passes is True


def test_gate_fails_interest_coverage_breach():
    schedule = [
        BearCaseYear(year=0, ebitda=100.0, interest=None),
        BearCaseYear(year=1, ebitda=30.0, interest=40.0),  # ebitda <= interest -> breach
    ]
    result = evaluate_bear_case_thresholds(make_bear_case(schedule=schedule))
    assert result.passes is False
    assert any("year 1" in f and "coverage" in f for f in result.failures)


def test_gate_interest_coverage_boundary_ebitda_equals_interest_is_a_breach():
    schedule = [BearCaseYear(year=0, ebitda=100.0, interest=None), BearCaseYear(year=1, ebitda=40.0, interest=40.0)]
    result = evaluate_bear_case_thresholds(make_bear_case(schedule=schedule))
    assert result.passes is False


def test_gate_year_zero_with_no_interest_never_flagged():
    schedule = [BearCaseYear(year=0, ebitda=0.0, interest=None)]  # would look like a breach if not skipped
    result = evaluate_bear_case_thresholds(make_bear_case(schedule=schedule))
    assert result.passes is True


def test_gate_accumulates_multiple_failures():
    result = evaluate_bear_case_thresholds(make_bear_case(irr=0.02, moic=0.5, exit_leverage=9.0))
    assert result.passes is False
    assert len(result.failures) == 3

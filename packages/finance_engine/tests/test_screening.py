"""Tests for the full 8-factor score_company assembly."""

from datetime import date

import pytest

from finance_engine.constants import WEIGHTS
from finance_engine.screening import score_company
from finance_engine.types import AssumptionInput, FinancialPeriodInput


def make_period(fiscal_year, **kwargs):
    defaults = dict(
        fiscal_year=fiscal_year,
        period_end_date=date(fiscal_year, 12, 31),
        period_type="FY",
        source="SEC_EDGAR",
    )
    defaults.update(kwargs)
    return FinancialPeriodInput(**defaults)


def test_weights_sum_to_one():
    """A future edit can't silently break the formula's completeness."""
    assert sum(WEIGHTS.values()) == pytest.approx(1.0, abs=1e-9)


def test_score_company_all_defaults_when_no_data():
    result = score_company(periods=[], assumptions=[])
    assert result.score == 50.0  # every factor defaults to neutral 50
    assert len(result.factors) == 8
    assert len(result.warnings) == 8  # all 8 factors flagged as default/placeholder
    for factor in result.factors:
        assert factor.source == "default"
        assert factor.normalized_score == 50.0


def test_score_company_with_full_financial_history_and_no_assumptions():
    periods = [
        make_period(2021, revenue=100, ebitda=20, operating_cash_flow=18, capex=5,
                    total_debt=60, cash_and_equivalents=10, interest_expense=4),
        make_period(2022, revenue=110, ebitda=24, operating_cash_flow=20, capex=6,
                    total_debt=55, cash_and_equivalents=12, interest_expense=3.5),
        make_period(2023, revenue=125, ebitda=28, operating_cash_flow=24, capex=6,
                    total_debt=50, cash_and_equivalents=15, interest_expense=3),
    ]
    result = score_company(periods=periods, assumptions=[])

    computed_names = {"growth", "margins", "cash_conversion", "leverage_capacity"}
    default_names = {"business_quality", "market_structure", "exit_optionality", "management_execution"}

    by_name = {f.name: f for f in result.factors}
    for name in computed_names:
        assert by_name[name].source == "computed", name
    for name in default_names:
        assert by_name[name].source == "default", name

    assert 0 <= result.score <= 100
    # exactly the 4 placeholder warnings, no data-quality warnings
    assert len(result.warnings) == 4


def test_score_company_assumption_override_changes_score_deterministically():
    periods = [
        make_period(2022, revenue=100, ebitda=20, operating_cash_flow=18, capex=5,
                    total_debt=60, cash_and_equivalents=10, interest_expense=4),
        make_period(2023, revenue=110, ebitda=22, operating_cash_flow=19, capex=5,
                    total_debt=55, cash_and_equivalents=12, interest_expense=3.5),
    ]
    assumptions = [
        AssumptionInput(name="business_quality_score", value_numeric=90),
        AssumptionInput(name="market_structure_score", value_numeric=80),
        AssumptionInput(name="exit_optionality_score", value_numeric=70),
        AssumptionInput(name="management_execution_score", value_numeric=60),
    ]

    baseline = score_company(periods=periods, assumptions=[])
    overridden = score_company(periods=periods, assumptions=assumptions)

    assert overridden.score != baseline.score
    by_name = {f.name: f for f in overridden.factors}
    assert by_name["business_quality"].normalized_score == 90
    assert by_name["business_quality"].source == "assumption"
    assert overridden.warnings == []  # no more defaults needed anywhere

    # Determinism: calling twice with identical inputs is bit-for-bit identical
    # on score/factors (computed_at timestamp legitimately differs).
    repeat = score_company(periods=periods, assumptions=assumptions)
    assert repeat.score == overridden.score
    assert [f.contribution for f in repeat.factors] == [f.contribution for f in overridden.factors]


def test_formula_version_is_reported():
    result = score_company(periods=[], assumptions=[])
    assert result.formula_version == "v0.1"


def test_score_is_weighted_sum_of_contributions():
    result = score_company(periods=[], assumptions=[])
    expected = sum(f.contribution for f in result.factors)
    assert result.score == pytest.approx(round(expected, 2))


def test_score_matches_independently_hand_computed_weighted_sum():
    """Cross-check against the design doc's section 3.4 formula computed by
    hand from known inputs, independent of score_company's own internals
    (unlike test_score_is_weighted_sum_of_contributions above, which
    re-derives its expectation from the same result object and would not
    catch a bug shared between the weight table and the summation code).
    """
    periods = [
        make_period(2021, revenue=100, ebitda=20, operating_cash_flow=18, capex=5,
                    total_debt=60, cash_and_equivalents=10, interest_expense=4),
        make_period(2022, revenue=110, ebitda=24, operating_cash_flow=20, capex=6,
                    total_debt=55, cash_and_equivalents=12, interest_expense=3.5),
        make_period(2023, revenue=125, ebitda=28, operating_cash_flow=24, capex=6,
                    total_debt=50, cash_and_equivalents=15, interest_expense=3),
    ]
    assumptions = [
        AssumptionInput(name="business_quality_score", value_numeric=80),
        AssumptionInput(name="market_structure_score", value_numeric=60),
        AssumptionInput(name="exit_optionality_score", value_numeric=70),
        AssumptionInput(name="management_execution_score", value_numeric=40),
    ]

    # Hand-computed per design doc section 3.2, using the same raw inputs above.
    # growth: CAGR = (125/100)**0.5 - 1 = 0.11803...
    #   score = clamp((0.11803 - (-0.10)) / (0.30 - (-0.10)) * 100, 0, 100) = 54.508
    growth_score = ((125 / 100) ** 0.5 - 1 - (-0.10)) / (0.30 - (-0.10)) * 100
    growth_score = max(0.0, min(100.0, growth_score))

    # margins: avg EBITDA margin across all 3 FY periods, / 0.40 ceiling
    margins = [20 / 100, 24 / 110, 28 / 125]
    avg_margin = sum(margins) / len(margins)
    margins_score = max(0.0, min(100.0, avg_margin / 0.40 * 100))

    # cash_conversion: avg (ocf - capex) / ebitda across all 3 periods
    conversions = [(18 - 5) / 20, (20 - 6) / 24, (24 - 6) / 28]
    avg_conversion = sum(conversions) / len(conversions)
    cash_conversion_score = max(0.0, min(100.0, avg_conversion * 100))

    # leverage_capacity: latest FY (2023) only, 50/50 blend
    net_debt = 50 - 15
    leverage_ratio = net_debt / 28
    leverage_score = max(0.0, min(100.0, (1 - leverage_ratio / 6) * 100))
    interest_coverage = 28 / 3
    coverage_score = max(0.0, min(100.0, (interest_coverage - 1) / (10 - 1) * 100))
    leverage_capacity_score = (leverage_score + coverage_score) / 2

    expected_score = (
        0.20 * 80
        + 0.15 * growth_score
        + 0.15 * margins_score
        + 0.15 * cash_conversion_score
        + 0.10 * leverage_capacity_score
        + 0.10 * 60
        + 0.10 * 70
        + 0.05 * 40
    )

    result = score_company(periods=periods, assumptions=assumptions)
    assert result.score == pytest.approx(round(expected_score, 2), abs=0.01)

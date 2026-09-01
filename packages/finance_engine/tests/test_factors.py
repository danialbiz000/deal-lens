"""Unit tests for the 4 computable factors.

Covers, per design doc section 6's acceptance checklist: normal case,
single-period/missing-data case, negative-EBITDA case, zero-revenue case,
and zero-interest-expense case. All deterministic, no I/O.
"""

from datetime import date

import pytest

from finance_engine.factors import (
    clamp,
    compute_cash_conversion,
    compute_growth,
    compute_leverage_capacity,
    compute_margins,
    select_fy_periods,
)
from finance_engine.types import FinancialPeriodInput


def make_period(fiscal_year, **kwargs):
    defaults = dict(
        fiscal_year=fiscal_year,
        period_end_date=date(fiscal_year, 12, 31),
        period_type="FY",
        source="SEC_EDGAR",
    )
    defaults.update(kwargs)
    return FinancialPeriodInput(**defaults)


# --- clamp ---


def test_clamp_bounds():
    assert clamp(150, 0, 100) == 100
    assert clamp(-10, 0, 100) == 0
    assert clamp(42, 0, 100) == 42


# --- select_fy_periods ---


def test_select_fy_periods_prefers_sec_edgar_on_duplicate_year():
    periods = [
        make_period(2022, source="FMP", revenue=100),
        make_period(2022, source="SEC_EDGAR", revenue=101),
        make_period(2023, source="SEC_EDGAR", revenue=110),
    ]
    selected = select_fy_periods(periods)
    assert len(selected) == 2
    y2022 = next(p for p in selected if p.fiscal_year == 2022)
    assert y2022.source == "SEC_EDGAR"
    assert y2022.revenue == 101


def test_select_fy_periods_excludes_non_fy():
    periods = [
        make_period(2023, period_type="Q1", revenue=10),
        make_period(2023, period_type="FY", revenue=100),
    ]
    selected = select_fy_periods(periods)
    assert len(selected) == 1
    assert selected[0].period_type == "FY"


def test_select_fy_periods_caps_at_three_most_recent():
    periods = [make_period(y, revenue=100 + y) for y in range(2018, 2024)]
    selected = select_fy_periods(periods)
    assert [p.fiscal_year for p in selected] == [2021, 2022, 2023]


# --- compute_growth ---


def test_growth_normal_case():
    periods = [
        make_period(2021, revenue=100),
        make_period(2022, revenue=110),
        make_period(2023, revenue=140.4),  # ~18.4% CAGR over 2 years
    ]
    result = compute_growth(periods)
    assert result.warning is None
    # revenue_cagr = (140.4/100)**0.5 - 1 ~= 0.1849
    assert 60 < result.normalized_score < 75


def test_growth_missing_period_case():
    periods = [make_period(2023, revenue=100)]
    result = compute_growth(periods)
    assert result.warning is not None
    assert result.normalized_score == 50.0


def test_growth_zero_revenue_earliest_case():
    periods = [
        make_period(2021, revenue=0),
        make_period(2023, revenue=100),
    ]
    result = compute_growth(periods)
    assert result.warning is not None
    assert result.normalized_score == 50.0


def test_growth_zero_percent_cagr_is_25_points():
    periods = [
        make_period(2022, revenue=100),
        make_period(2023, revenue=100),
    ]
    result = compute_growth(periods)
    assert result.normalized_score == pytest.approx(25.0, abs=0.1)


def test_growth_ceiling_and_floor():
    high_growth = [make_period(2022, revenue=100), make_period(2023, revenue=140)]
    assert compute_growth(high_growth).normalized_score == 100.0

    steep_decline = [make_period(2022, revenue=100), make_period(2023, revenue=50)]
    assert compute_growth(steep_decline).normalized_score == 0.0


# --- compute_margins ---


def test_margins_normal_case():
    periods = [
        make_period(2022, revenue=1000, ebitda=200),
        make_period(2023, revenue=1000, ebitda=200),
    ]
    result = compute_margins(periods)
    assert result.warning is None
    assert result.normalized_score == pytest.approx(50.0, abs=0.01)


def test_margins_negative_ebitda_case():
    periods = [make_period(2023, revenue=1000, ebitda=-50)]
    result = compute_margins(periods)
    assert result.warning is None  # computable, just a bad score
    assert result.normalized_score == 0.0


def test_margins_zero_revenue_case():
    periods = [make_period(2023, revenue=0, ebitda=100)]
    result = compute_margins(periods)
    assert result.warning is not None
    assert result.normalized_score == 50.0


def test_margins_missing_data_case():
    periods = [make_period(2023, revenue=None, ebitda=None)]
    result = compute_margins(periods)
    assert result.warning is not None
    assert result.normalized_score == 50.0


# --- compute_cash_conversion ---


def test_cash_conversion_normal_case():
    periods = [make_period(2023, ebitda=100, operating_cash_flow=80, capex=30)]
    result = compute_cash_conversion(periods)
    assert result.warning is None
    assert result.normalized_score == 50.0  # (80-30)/100 = 50%


def test_cash_conversion_negative_ebitda_case():
    periods = [make_period(2023, ebitda=-50, operating_cash_flow=10, capex=5)]
    result = compute_cash_conversion(periods)
    assert result.warning is not None
    assert result.normalized_score == 50.0


def test_cash_conversion_missing_period_case():
    periods = [make_period(2023, ebitda=None, operating_cash_flow=None, capex=None)]
    result = compute_cash_conversion(periods)
    assert result.warning is not None
    assert result.normalized_score == 50.0


def test_cash_conversion_negative_fcf_floors_at_zero():
    periods = [make_period(2023, ebitda=100, operating_cash_flow=10, capex=50)]
    result = compute_cash_conversion(periods)
    assert result.normalized_score == 0.0


# --- compute_leverage_capacity ---


def test_leverage_capacity_normal_case():
    periods = [
        make_period(
            2023,
            ebitda=100,
            total_debt=300,
            cash_and_equivalents=100,
            interest_expense=20,
        )
    ]
    result = compute_leverage_capacity(periods)
    assert result.warning is None
    # net_debt/ebitda = 2.0x -> leverage_score = (1 - 2/6)*100 = 66.67
    # interest_coverage = 100/20 = 5x -> coverage_score = (5-1)/9*100 = 44.44
    assert result.normalized_score == pytest.approx((66.6667 + 44.4444) / 2, abs=0.1)


def test_leverage_capacity_negative_ebitda_case():
    periods = [
        make_period(
            2023,
            ebitda=-50,
            total_debt=200,
            cash_and_equivalents=50,
            interest_expense=10,
        )
    ]
    result = compute_leverage_capacity(periods)
    assert result.warning is not None
    assert "EBITDA <= 0" in result.warning


def test_leverage_capacity_zero_interest_expense_case():
    periods = [
        make_period(
            2023,
            ebitda=100,
            total_debt=100,
            cash_and_equivalents=50,
            interest_expense=0,
        )
    ]
    result = compute_leverage_capacity(periods)
    assert result.warning is not None
    assert "interest_expense" in result.warning
    # leverage_ratio = 50/100 = 0.5x -> leverage_score = (1-0.5/6)*100 = 91.67
    # coverage_score forced to 100
    assert result.normalized_score == pytest.approx((91.6667 + 100) / 2, abs=0.1)


def test_leverage_capacity_null_interest_expense_case():
    periods = [
        make_period(
            2023,
            ebitda=100,
            total_debt=100,
            cash_and_equivalents=50,
            interest_expense=None,
        )
    ]
    result = compute_leverage_capacity(periods)
    assert result.warning is not None
    assert result.normalized_score > 90  # coverage_score=100 dominates


def test_leverage_capacity_missing_period_case():
    result = compute_leverage_capacity([])
    assert result.warning is not None
    assert result.normalized_score == 50.0

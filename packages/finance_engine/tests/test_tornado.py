import pytest

from finance_engine.lbo import DebtTranche, LboInputs, run_lbo
from finance_engine.tornado import run_tornado_analysis


def base_inputs(**overrides):
    defaults = dict(
        entry_ev=1000.0,
        entry_ebitda=100.0,
        entry_revenue=500.0,
        revenue_growth_rate=0.05,
        ebitda_margin_delta=0.02,
        exit_multiple_delta=0.0,
        lbo_leverage_multiple=5.0,
        lbo_interest_rate=0.08,
        lbo_cash_sweep_pct=1.0,
        lbo_mandatory_amort_pct=0.01,
        lbo_tax_rate=0.25,
        lbo_capex_pct_revenue=0.03,
        lbo_nwc_pct_revenue_change=0.05,
        lbo_transaction_fees_pct=0.02,
        hold_period_years=5,
    )
    defaults.update(overrides)
    return LboInputs(**defaults)


def test_all_six_variables_present_and_sorted_by_spread_descending():
    result = run_tornado_analysis(base_inputs())
    variables = result["variables"]
    assert {v["variable"] for v in variables} == {
        "revenue_growth_rate", "ebitda_margin_delta", "entry_multiple",
        "exit_multiple", "leverage", "interest_rate",
    }
    spreads = [v["spread"] for v in variables]
    assert spreads == sorted(spreads, reverse=True)


def test_base_irr_matches_a_direct_run_lbo_call():
    inputs = base_inputs()
    direct = run_lbo(inputs)
    result = run_tornado_analysis(inputs)
    for v in result["variables"]:
        assert v["base_irr"] == pytest.approx(direct.irr, abs=1e-9)
        assert v["base_moic"] == pytest.approx(direct.moic, abs=1e-9)


def test_entry_multiple_holds_exit_multiple_fixed_isolating_the_effect():
    # Standard PE framing: "what if I pay more/less to get in" should not
    # also silently drag the exit multiple along with it.
    inputs = base_inputs()
    result = run_tornado_analysis(inputs, deltas={"entry_multiple": 2.0})
    entry_row = next(v for v in result["variables"] if v["variable"] == "entry_multiple")
    # Higher entry multiple at a fixed exit multiple must hurt IRR.
    assert entry_row["high_irr"] < entry_row["base_irr"] < entry_row["low_irr"]


def test_exit_multiple_sign_is_opposite_of_entry_multiple():
    inputs = base_inputs()
    result = run_tornado_analysis(inputs, deltas={"exit_multiple": 2.0})
    exit_row = next(v for v in result["variables"] if v["variable"] == "exit_multiple")
    # Higher exit multiple must help IRR (opposite direction from entry).
    assert exit_row["high_irr"] > exit_row["base_irr"] > exit_row["low_irr"]


def test_higher_leverage_increases_irr_in_a_positive_spread_case():
    inputs = base_inputs()
    result = run_tornado_analysis(inputs, deltas={"leverage": 1.0})
    leverage_row = next(v for v in result["variables"] if v["variable"] == "leverage")
    assert leverage_row["high_irr"] > leverage_row["base_irr"] > leverage_row["low_irr"]


def test_higher_interest_rate_decreases_irr():
    inputs = base_inputs()
    result = run_tornado_analysis(inputs, deltas={"interest_rate": 0.02})
    rate_row = next(v for v in result["variables"] if v["variable"] == "interest_rate")
    assert rate_row["high_irr"] < rate_row["base_irr"] < rate_row["low_irr"]


def test_growth_and_margin_directions_are_intuitive():
    inputs = base_inputs()
    result = run_tornado_analysis(inputs)
    growth_row = next(v for v in result["variables"] if v["variable"] == "revenue_growth_rate")
    margin_row = next(v for v in result["variables"] if v["variable"] == "ebitda_margin_delta")
    assert growth_row["high_irr"] > growth_row["base_irr"] > growth_row["low_irr"]
    assert margin_row["high_irr"] > margin_row["base_irr"] > margin_row["low_irr"]


def test_leverage_floor_prevents_negative_leverage():
    inputs = base_inputs(lbo_leverage_multiple=1.0)
    result = run_tornado_analysis(inputs, deltas={"leverage": 5.0})  # would go to -4.0x unfloored
    leverage_row = next(v for v in result["variables"] if v["variable"] == "leverage")
    assert leverage_row["low_value"] == 0.0


def test_interest_rate_floor_prevents_negative_rate():
    inputs = base_inputs(lbo_interest_rate=0.01)
    result = run_tornado_analysis(inputs, deltas={"interest_rate": 0.05})  # would go to -4% unfloored
    rate_row = next(v for v in result["variables"] if v["variable"] == "interest_rate")
    assert rate_row["low_value"] == 0.0


def test_custom_deltas_override_only_the_specified_variables():
    inputs = base_inputs()
    default_result = run_tornado_analysis(inputs)
    custom_result = run_tornado_analysis(inputs, deltas={"leverage": 3.0})

    default_leverage = next(v for v in default_result["variables"] if v["variable"] == "leverage")
    custom_leverage = next(v for v in custom_result["variables"] if v["variable"] == "leverage")
    assert custom_leverage["low_value"] == pytest.approx(2.0)  # 5.0 - 3.0
    assert custom_leverage["low_value"] != default_leverage["low_value"]

    # Untouched variables keep using the defaults.
    default_growth = next(v for v in default_result["variables"] if v["variable"] == "revenue_growth_rate")
    custom_growth = next(v for v in custom_result["variables"] if v["variable"] == "revenue_growth_rate")
    assert custom_growth["low_value"] == pytest.approx(default_growth["low_value"])


def test_leverage_sensitivity_preserves_tranche_mix_proportionally():
    # Base: 70% senior / 30% mezzanine of a 5.0x total. Bumping total
    # leverage to 6.0x should scale both tranches by the same factor, not
    # just pile the extra 1.0x onto one tranche.
    inputs = base_inputs(
        debt_tranches=(
            DebtTranche(name="Senior", leverage_multiple=3.5, interest_rate=0.06, priority=1),
            DebtTranche(name="Mezzanine", leverage_multiple=1.5, interest_rate=0.11, priority=2),
        )
    )
    result = run_tornado_analysis(inputs, deltas={"leverage": 1.0})
    leverage_row = next(v for v in result["variables"] if v["variable"] == "leverage")
    assert leverage_row["base_value"] == pytest.approx(5.0)
    assert leverage_row["high_value"] == pytest.approx(6.0)

    high_inputs = base_inputs(
        debt_tranches=(
            DebtTranche(name="Senior", leverage_multiple=3.5 * 1.2, interest_rate=0.06, priority=1),
            DebtTranche(name="Mezzanine", leverage_multiple=1.5 * 1.2, interest_rate=0.11, priority=2),
        )
    )
    expected_high = run_lbo(high_inputs)
    assert leverage_row["high_irr"] == pytest.approx(expected_high.irr, abs=1e-9)


def test_interest_rate_sensitivity_shifts_every_tranche_by_the_same_delta():
    inputs = base_inputs(
        debt_tranches=(
            DebtTranche(name="Senior", leverage_multiple=3.5, interest_rate=0.06, priority=1),
            DebtTranche(name="Mezzanine", leverage_multiple=1.5, interest_rate=0.11, priority=2),
        )
    )
    result = run_tornado_analysis(inputs, deltas={"interest_rate": 0.02})
    rate_row = next(v for v in result["variables"] if v["variable"] == "interest_rate")
    # Representative rate is the highest-priority (Senior) tranche's own rate.
    assert rate_row["base_value"] == pytest.approx(0.06)
    assert rate_row["high_value"] == pytest.approx(0.08)

    high_inputs = base_inputs(
        debt_tranches=(
            DebtTranche(name="Senior", leverage_multiple=3.5, interest_rate=0.08, priority=1),
            DebtTranche(name="Mezzanine", leverage_multiple=1.5, interest_rate=0.13, priority=2),
        )
    )
    expected_high = run_lbo(high_inputs)
    assert rate_row["high_irr"] == pytest.approx(expected_high.irr, abs=1e-9)

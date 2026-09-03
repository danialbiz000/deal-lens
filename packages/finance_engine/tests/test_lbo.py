import pytest

from finance_engine.lbo import DebtTranche, LboInputs, run_lbo, run_sensitivity_grid


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


# --- standard run ---


def test_standard_five_year_run_produces_sane_outputs():
    result = run_lbo(base_inputs())
    assert result.formula_version == "lbo_v0.1"
    assert len(result.schedule) == 6  # year 0 + 5 hold years
    assert result.moic > 0
    assert result.entry_multiple == pytest.approx(10.0)
    assert result.entry_leverage == pytest.approx(5.0)


def test_sources_equal_uses_exactly():
    result = run_lbo(base_inputs())
    su = result.sources_uses
    assert su.reconciles is True
    sources_total = su.new_debt + su.sponsor_equity
    uses_total = su.purchase_ev + su.fees
    assert sources_total == pytest.approx(uses_total, abs=1e-9)


def test_sources_uses_values():
    result = run_lbo(base_inputs())
    su = result.sources_uses
    assert su.new_debt == pytest.approx(100.0 * 5.0)  # entry_ebitda * leverage_multiple
    assert su.fees == pytest.approx(1000.0 * 0.02)
    assert su.sponsor_equity == pytest.approx((1000.0 + 20.0) - 500.0)


def test_debt_schedule_rolls_forward_exactly():
    result = run_lbo(base_inputs())
    schedule = result.schedule
    for prev, curr in zip(schedule, schedule[1:]):
        assert curr.beginning_debt == pytest.approx(prev.ending_debt, abs=1e-9)
        assert curr.beginning_cash == pytest.approx(prev.ending_cash, abs=1e-9)
    for year in schedule[1:]:
        reconstructed_ending_debt = year.beginning_debt - year.mandatory_amort - year.sweep
        assert year.ending_debt == pytest.approx(reconstructed_ending_debt, abs=1e-9)
        assert year.ending_debt >= -1e-9  # never negative


def test_debt_fully_repaid_before_hold_period_ends_no_negative_debt():
    # Low leverage + full cash sweep -> debt should hit exactly 0 well before year 5.
    result = run_lbo(base_inputs(lbo_leverage_multiple=1.0, lbo_cash_sweep_pct=1.0))
    schedule = result.schedule
    zero_debt_years = [y.year for y in schedule if y.ending_debt == 0]
    assert len(zero_debt_years) >= 2  # once it hits 0 it should stay 0 for remaining years
    # Once debt is 0, ending_cash should be non-decreasing (excess FCF accumulates as cash)
    zero_debt_start = min(zero_debt_years)
    cash_after_payoff = [y.ending_cash for y in schedule if y.year >= zero_debt_start]
    for prev, curr in zip(cash_after_payoff, cash_after_payoff[1:]):
        assert curr >= prev - 1e-9
    for year in schedule:
        assert year.ending_debt >= -1e-9


def test_bear_case_with_negative_cfads_no_crash_and_warns():
    bear = base_inputs(
        entry_ebitda=50.0,
        entry_revenue=500.0,  # base margin 10%
        revenue_growth_rate=0.20,  # aggressive growth stresses NWC
        ebitda_margin_delta=-0.05,  # margin compression
        lbo_capex_pct_revenue=0.10,  # high capex
        hold_period_years=5,
    )
    result = run_lbo(bear)
    year1 = result.schedule[1]
    assert year1.cfads < 0  # genuinely negative CFADS, not just a thin margin
    assert year1.sweep == 0  # no sweep when cash_before_sweep is not positive
    assert year1.ending_cash < 0  # allowed to go negative -- no revolver modeled
    assert any("negative" in w for w in result.warnings)
    # no exception raised getting here -- that itself is the main assertion


def test_zero_interest_rate_edge_case():
    result = run_lbo(base_inputs(lbo_interest_rate=0.0))
    for year in result.schedule[1:]:
        assert year.interest == 0.0
    assert result.moic > 0  # still computes a sane result


def test_zero_hold_period_years_raises():
    with pytest.raises(ValueError):
        run_lbo(base_inputs(hold_period_years=0))


def test_zero_entry_ebitda_raises():
    with pytest.raises(ValueError):
        run_lbo(base_inputs(entry_ebitda=0.0))


# --- value creation bridge reconciliation (hard requirement: 1e-6 tolerance) ---


@pytest.mark.parametrize(
    "overrides",
    [
        {},  # base-ish
        dict(revenue_growth_rate=0.10, ebitda_margin_delta=0.03, exit_multiple_delta=1.0),  # bull-like
        dict(revenue_growth_rate=-0.03, ebitda_margin_delta=-0.02, exit_multiple_delta=-2.0),  # bear-like
        dict(lbo_leverage_multiple=3.0, lbo_interest_rate=0.06, exit_multiple_delta=2.5),  # low leverage, big rerate
    ],
)
def test_value_creation_bridge_reconciles_to_moic(overrides):
    result = run_lbo(base_inputs(**overrides))
    bridge = result.value_creation_bridge
    assert bridge.total == pytest.approx(result.moic, abs=1e-6)


def test_value_creation_bridge_components_sum_matches_stored_total():
    result = run_lbo(base_inputs(revenue_growth_rate=0.08, ebitda_margin_delta=0.01, exit_multiple_delta=0.5))
    bridge = result.value_creation_bridge
    manual_sum = (
        bridge.entry_equity
        + bridge.ebitda_growth
        + bridge.margin_expansion
        + bridge.debt_paydown
        + bridge.multiple_expansion
        + bridge.transaction_fees
    )
    assert manual_sum == pytest.approx(bridge.total, abs=1e-9)
    assert manual_sum == pytest.approx(result.moic, abs=1e-6)


# --- exit-multiple-dependent / value-destructive flags ---


def test_exit_multiple_dependent_flag_true_when_rerating_dominates():
    # No organic growth/margin change at all -> ebitda_growth and margin_expansion
    # are exactly 0; a huge exit-multiple delta on thin equity makes multiple
    # expansion overwhelm any incidental debt-paydown-from-cash component.
    result = run_lbo(
        base_inputs(
            revenue_growth_rate=0.0,
            ebitda_margin_delta=0.0,
            exit_multiple_delta=15.0,
            lbo_leverage_multiple=5.0,
        )
    )
    bridge = result.value_creation_bridge
    assert bridge.value_destructive is False
    assert bridge.exit_multiple_dependent is True


def test_exit_multiple_dependent_flag_false_when_multiple_flat():
    # exit_multiple_delta = 0 -> multiple_expansion is exactly 0, so it can
    # never be >50% of a positive value-creation total.
    result = run_lbo(
        base_inputs(revenue_growth_rate=0.15, ebitda_margin_delta=0.05, exit_multiple_delta=0.0)
    )
    bridge = result.value_creation_bridge
    assert bridge.multiple_expansion == pytest.approx(0.0, abs=1e-9)
    assert bridge.exit_multiple_dependent is False


def test_value_destructive_flag_when_deal_loses_money():
    result = run_lbo(
        base_inputs(
            entry_ev=800.0,
            entry_ebitda=100.0,
            entry_revenue=500.0,
            revenue_growth_rate=0.0,
            ebitda_margin_delta=0.0,
            exit_multiple_delta=-6.0,  # entry_multiple 8x -> exit_multiple 2x
            lbo_leverage_multiple=5.0,
        )
    )
    assert result.moic < 1.0
    bridge = result.value_creation_bridge
    assert bridge.value_destructive is True
    assert bridge.exit_multiple_dependent is False  # not the relevant framing when value-destructive
    assert bridge.total == pytest.approx(result.moic, abs=1e-6)  # identity still holds even when destructive


# --- sensitivity grid ---


def test_sensitivity_grid_shape_and_centering():
    grid = run_sensitivity_grid(base_inputs(), step=1.0, size=4)
    assert len(grid["entry_multiples"]) == 4
    assert len(grid["exit_multiples"]) == 4
    assert len(grid["irr_grid"]) == 4
    assert all(len(row) == 4 for row in grid["irr_grid"])
    assert len(grid["moic_grid"]) == 4

    base_entry_multiple = 1000.0 / 100.0  # 10x
    # size=4 -> offsets of -1.5,-0.5,0.5,1.5 around the base multiple
    assert grid["entry_multiples"][0] == pytest.approx(base_entry_multiple - 1.5)
    assert grid["entry_multiples"][-1] == pytest.approx(base_entry_multiple + 1.5)


def test_sensitivity_grid_monotonicity():
    grid = run_sensitivity_grid(base_inputs(), step=1.0, size=4)
    irr_grid = grid["irr_grid"]

    # Fixed entry multiple (each row): IRR strictly increases as exit multiple increases.
    for row in irr_grid:
        for a, b in zip(row, row[1:]):
            assert b > a

    # Fixed exit multiple (each column): IRR strictly decreases as entry multiple increases
    # (paying more to get in, same exit proceeds, is strictly worse).
    for col in range(len(irr_grid[0])):
        column_values = [irr_grid[row][col] for row in range(len(irr_grid))]
        for a, b in zip(column_values, column_values[1:]):
            assert b < a


# --- debt sculpting: multiple tranches (v1.0) ---


def test_no_tranches_given_is_byte_identical_to_the_old_single_blended_behavior():
    # The whole point of making debt_tranches optional: every existing
    # caller (no tranches specified) must get exactly the same numbers as
    # before this feature existed.
    without_tranches = run_lbo(base_inputs())
    with_equivalent_single_tranche = run_lbo(
        base_inputs(
            debt_tranches=(
                DebtTranche(name="Blended Term Loan", leverage_multiple=5.0, interest_rate=0.08,
                            mandatory_amort_pct=0.01, priority=1),
            )
        )
    )
    assert with_equivalent_single_tranche.moic == pytest.approx(without_tranches.moic, abs=1e-9)
    assert with_equivalent_single_tranche.irr == pytest.approx(without_tranches.irr, abs=1e-9)
    for a, b in zip(without_tranches.schedule, with_equivalent_single_tranche.schedule):
        assert a.ending_debt == pytest.approx(b.ending_debt, abs=1e-6)
        assert a.ending_cash == pytest.approx(b.ending_cash, abs=1e-6)


def test_tranche_principals_sum_to_total_new_debt():
    inputs = base_inputs(
        debt_tranches=(
            DebtTranche(name="Senior", leverage_multiple=3.5, interest_rate=0.06, mandatory_amort_pct=0.05, priority=1),
            DebtTranche(name="Mezzanine", leverage_multiple=1.5, interest_rate=0.11, mandatory_amort_pct=0.0, priority=2),
        )
    )
    result = run_lbo(inputs)
    assert result.sources_uses.new_debt == pytest.approx(100.0 * (3.5 + 1.5))  # entry_ebitda * total leverage
    assert result.entry_leverage == pytest.approx(5.0)

    year1 = result.schedule[1]
    assert len(year1.tranches) == 2
    assert sum(tr.beginning_balance for tr in year1.tranches) == pytest.approx(year1.beginning_debt)
    assert sum(tr.ending_balance for tr in year1.tranches) == pytest.approx(year1.ending_debt, abs=1e-6)
    assert sum(tr.interest for tr in year1.tranches) == pytest.approx(year1.interest, abs=1e-6)
    assert sum(tr.mandatory_amort for tr in year1.tranches) == pytest.approx(year1.mandatory_amort, abs=1e-6)
    assert sum(tr.sweep for tr in year1.tranches) == pytest.approx(year1.sweep, abs=1e-6)


def test_each_tranche_accrues_interest_at_its_own_rate():
    inputs = base_inputs(
        lbo_cash_sweep_pct=0.0,  # isolate interest from sweep effects
        debt_tranches=(
            DebtTranche(name="Senior", leverage_multiple=3.5, interest_rate=0.06, priority=1),
            DebtTranche(name="Mezzanine", leverage_multiple=1.5, interest_rate=0.11, priority=2),
        ),
    )
    result = run_lbo(inputs)
    year1 = result.schedule[1]
    senior = next(tr for tr in year1.tranches if tr.name == "Senior")
    mezz = next(tr for tr in year1.tranches if tr.name == "Mezzanine")
    assert senior.interest == pytest.approx(350.0 * 0.06)  # entry_ebitda(100) * 3.5x * 6%
    assert mezz.interest == pytest.approx(150.0 * 0.11)  # entry_ebitda(100) * 1.5x * 11%


def test_mandatory_amort_caps_at_each_tranches_own_original_principal():
    # Senior amortizes 20%/yr of its OWN principal; mezzanine never amortizes.
    # After year 1, mezzanine's balance must be completely untouched by
    # senior's amort schedule.
    inputs = base_inputs(
        lbo_cash_sweep_pct=0.0,
        revenue_growth_rate=0.0,
        ebitda_margin_delta=0.0,
        debt_tranches=(
            DebtTranche(name="Senior", leverage_multiple=3.5, interest_rate=0.06, mandatory_amort_pct=0.20, priority=1),
            DebtTranche(name="Mezzanine", leverage_multiple=1.5, interest_rate=0.11, mandatory_amort_pct=0.0, priority=2),
        ),
    )
    result = run_lbo(inputs)
    year1 = result.schedule[1]
    senior = next(tr for tr in year1.tranches if tr.name == "Senior")
    mezz = next(tr for tr in year1.tranches if tr.name == "Mezzanine")
    assert senior.mandatory_amort == pytest.approx(350.0 * 0.20)  # 20% of senior's own original principal
    assert mezz.mandatory_amort == pytest.approx(0.0)
    assert mezz.beginning_balance == pytest.approx(150.0)
    assert mezz.ending_balance == pytest.approx(150.0)  # untouched: no mandatory amort, no sweep


def test_cash_sweep_pays_down_higher_priority_tranche_first():
    # Senior (priority 1) must be swept down to zero before Mezzanine
    # (priority 2) receives any sweep cash at all.
    inputs = base_inputs(
        entry_ev=250.0,  # small EV -> aggressive equity return -> lots of excess cash to sweep
        lbo_leverage_multiple=1.0,
        lbo_mandatory_amort_pct=0.0,
        lbo_cash_sweep_pct=1.0,
        debt_tranches=(
            DebtTranche(name="Senior", leverage_multiple=0.5, interest_rate=0.06, priority=1),
            DebtTranche(name="Mezzanine", leverage_multiple=0.5, interest_rate=0.11, priority=2),
        ),
    )
    result = run_lbo(inputs)

    senior_paid_off_year = None
    for year in result.schedule[1:]:
        senior = next(tr for tr in year.tranches if tr.name == "Senior")
        mezz = next(tr for tr in year.tranches if tr.name == "Mezzanine")
        if senior_paid_off_year is None:
            # While Senior still has a balance, Mezzanine must receive zero sweep.
            if senior.ending_balance > 1e-6:
                assert mezz.sweep == pytest.approx(0.0, abs=1e-6)
            else:
                senior_paid_off_year = year.year
        else:
            # Once Senior is fully repaid, Mezzanine is now free to receive sweep cash.
            pass

    assert senior_paid_off_year is not None, "test is only meaningful if Senior actually gets fully repaid"
    final_mezz = next(tr for tr in result.schedule[-1].tranches if tr.name == "Mezzanine")
    assert final_mezz.ending_balance < 0.5 * 100.0 * 0.5  # meaningfully paid down vs its own starting principal


def test_value_creation_bridge_still_reconciles_with_multiple_tranches():
    inputs = base_inputs(
        debt_tranches=(
            DebtTranche(name="Senior", leverage_multiple=3.5, interest_rate=0.06, mandatory_amort_pct=0.05, priority=1),
            DebtTranche(name="Mezzanine", leverage_multiple=1.5, interest_rate=0.11, mandatory_amort_pct=0.0, priority=2),
        )
    )
    result = run_lbo(inputs)
    assert result.value_creation_bridge.total == pytest.approx(result.moic, abs=1e-6)


def test_inputs_snapshot_always_records_the_fully_resolved_tranche_list():
    # Even when debt_tranches is left unset, the stored snapshot should show
    # the implicit single tranche actually used -- the audit trail must
    # reflect what was modeled, not just what the caller passed in.
    result = run_lbo(base_inputs())
    assert result.inputs["debt_tranches"] == [
        {"name": "Blended Term Loan", "leverage_multiple": 5.0, "interest_rate": 0.08,
         "mandatory_amort_pct": 0.01, "priority": 1}
    ]

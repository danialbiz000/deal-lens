from __future__ import annotations

import numpy as np
import pandas as pd

from toolkit import crash_regime_interaction, full_report, tail_risk_profile


def _synthetic_hedged_returns(prices: pd.DataFrame) -> pd.Series:
    """A stand-in 'signal' return series: the cross-sectional mean of the
    synthetic random-walk prices' own daily returns, offset from zero so
    VaR/CVaR has a non-degenerate mean to work with. Mechanics-only test --
    this data has no real crash-regime structure built in, so it should
    come back a clean (non-significant) null, which is itself part of what
    this test checks."""
    return prices.pct_change().mean(axis=1).dropna() + 0.0002


def test_crash_regime_interaction_runs_and_returns_well_formed_result(random_walk_prices):
    hedged = _synthetic_hedged_returns(random_walk_prices)
    result = crash_regime_interaction("synthetic signal", hedged, random_walk_prices)

    assert result.label == "synthetic signal"
    assert result.n_total_days > 0
    assert 0 <= result.n_bear_highvol_days <= result.n_total_days
    assert 0.0 <= result.interaction_p <= 1.0
    assert 0.0 <= result.baseline_p <= 1.0
    assert isinstance(result.significant, bool)
    assert "Bear+HighVol interaction" in result.summary()


def test_tail_risk_profile_runs_and_returns_well_formed_result(random_walk_prices):
    hedged = _synthetic_hedged_returns(random_walk_prices)
    report = tail_risk_profile("synthetic signal", hedged, n_bootstrap=200)  # small for test speed

    assert report.n == len(hedged.dropna())
    assert len(report.levels) == 3  # 95%, 99%, 99.9% by default
    for level in report.levels:
        assert level.cvar_ratio > 0 or np.isnan(level.cvar_ratio)
        assert level.cvar_ratio_ci_lo <= level.cvar_ratio_ci_hi or (
            np.isnan(level.cvar_ratio_ci_lo) and np.isnan(level.cvar_ratio_ci_hi)
        )
        assert level.n_tail_obs >= 0
    assert "CVaR ratio" in report.summary()


def test_full_report_skips_stress_table_when_interaction_not_significant(random_walk_prices):
    hedged = _synthetic_hedged_returns(random_walk_prices)
    report = full_report("synthetic signal", hedged, random_walk_prices)

    # synthetic random-walk data has no built-in crash-regime structure, so
    # this should reliably come back non-significant -- exercising the same
    # "don't stress-test a null result" branch Milestones 46 and 53 found
    # necessary for real signals.
    assert not report.crash_interaction.significant
    assert report.stress is None
    assert "No crash-duration stress scenario run" in report.summary()

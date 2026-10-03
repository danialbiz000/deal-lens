from __future__ import annotations

import numpy as np
import pandas as pd

from investigations.beta_hedged_backtest import build_hedged_return_series, rolling_beta


def test_rolling_beta_recovers_a_known_exact_beta():
    dates = pd.bdate_range("2020-01-01", periods=300)
    rng = np.random.default_rng(0)
    market = pd.Series(rng.normal(scale=0.01, size=300), index=dates)
    strategy = 1.5 * market  # exact beta of 1.5, no noise

    beta = rolling_beta(strategy, market, as_of=dates[280])
    assert beta is not None
    assert np.isclose(beta, 1.5, atol=1e-9)


def test_rolling_beta_is_none_before_enough_history():
    dates = pd.bdate_range("2020-01-01", periods=50)
    market = pd.Series(0.01, index=dates)
    strategy = pd.Series(0.01, index=dates)

    assert rolling_beta(strategy, market, as_of=dates[40]) is None


def test_hedged_series_removes_market_exposure_when_beta_is_exact_and_stable():
    dates = pd.bdate_range("2020-01-01", periods=400)
    rng = np.random.default_rng(1)
    market = pd.Series(rng.normal(scale=0.01, size=400), index=dates)
    strategy = 2.0 * market  # exact beta of 2.0, no idiosyncratic return at all

    reb_dates = pd.DatetimeIndex([dates[i] for i in range(150, 400, 21)])
    hedged, beta_used = build_hedged_return_series(strategy, market, reb_dates)

    covered = hedged.dropna()
    # with zero idiosyncratic return and a (near-)correctly estimated beta,
    # the hedged residual should be tiny
    assert covered.abs().max() < 1e-6

from __future__ import annotations

import numpy as np
import pandas as pd

from signals.composite import composite_score
from signals.momentum import high_52w_proximity, momentum_12_1
from signals.reversal import short_term_reversal


def test_momentum_12_1_matches_manual_calculation():
    # a single ticker, 300 flat days then a known step, to hand-check the
    # skip=21 / lookback=252 windowing rather than trust it blind
    dates = pd.bdate_range("2020-01-01", periods=300)
    prices = pd.Series(100.0, index=dates)
    prices.iloc[100:] = 150.0  # a jump partway through
    df = prices.to_frame("A")

    mom = momentum_12_1(df, lookback=252, skip=21)
    # value at the last date should reflect (price 21 days ago) / (price 252-21
    # days before THAT) - 1, computed directly from the same series for a
    # cross-check
    lagged = prices.shift(21)
    expected_last = lagged.iloc[-1] / lagged.shift(231).iloc[-1] - 1.0
    assert np.isclose(mom["A"].iloc[-1], expected_last)


def test_high_52w_proximity_is_one_at_the_running_high():
    dates = pd.bdate_range("2020-01-01", periods=300)
    prices = pd.Series(np.linspace(100, 200, 300), index=dates)  # strictly increasing
    df = prices.to_frame("A")

    prox = high_52w_proximity(df, window=252)
    # strictly increasing series -> today's price IS the trailing max every day
    valid = prox["A"].dropna()
    assert np.allclose(valid, 1.0)


def test_short_term_reversal_sign_convention():
    dates = pd.bdate_range("2020-01-01", periods=60)
    prices = pd.Series(100.0, index=dates)
    prices.iloc[45:] = 50.0  # a sharp decline within the last `lookback` days
    df = prices.to_frame("A")

    rev = short_term_reversal(df, lookback=21)
    # after a recent large DECLINE, the reversal signal should be POSITIVE
    # (i.e. "predicted" to bounce), per the sign convention documented in
    # signals/reversal.py
    assert rev["A"].iloc[-1] > 0


def test_composite_score_is_cross_sectionally_zero_mean(random_walk_prices):
    score = composite_score(random_walk_prices)
    last_row = score.iloc[-1].dropna()
    assert len(last_row) == random_walk_prices.shape[1]
    # cross-sectional z-scored components summed -> mean should be ~0 across tickers
    assert abs(last_row.mean()) < 1e-6

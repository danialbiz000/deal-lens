"""Shared synthetic fixtures.

None of these tests touch the network -- they exist to prove the signal and
backtest MECHANICS are correct (a `pytest.ini`-free sanity net), not to
validate the anomalies empirically. See ../README.md "Important limitation
of this environment" for why real market-data validation has to happen
outside this sandbox.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def random_walk_prices() -> pd.DataFrame:
    """20 synthetic tickers, ~3 years of daily prices, independent random walks
    with a small positive drift and idiosyncratic vol -- enough history for
    the 252-day rolling windows in signals/momentum.py to be well-defined."""
    rng = np.random.default_rng(42)
    n_days, n_tickers = 800, 20
    dates = pd.bdate_range("2019-01-01", periods=n_days)
    tickers = [f"T{i:02d}" for i in range(n_tickers)]

    daily_returns = rng.normal(loc=0.0003, scale=0.015, size=(n_days, n_tickers))
    prices = 100 * np.cumprod(1 + daily_returns, axis=0)
    return pd.DataFrame(prices, index=dates, columns=tickers)


@pytest.fixture
def signal_predicts_return_prices() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Synthetic prices constructed so that a KNOWN score perfectly ranks next-
    month returns at every rebalance: ticker i's forward monthly return is
    exactly proportional to a fixed rank i. This lets the backtest test assert
    the long-short spread is unambiguously positive, without depending on any
    real anomaly actually existing in random data."""
    rng = np.random.default_rng(7)
    n_tickers = 40
    tickers = [f"S{i:02d}" for i in range(n_tickers)]
    # fixed cross-sectional "skill" ranking, ticker index -> return tilt
    skill = np.linspace(-1.0, 1.0, n_tickers)

    dates = pd.bdate_range("2018-01-01", periods=760)  # ~3 years
    n_days = len(dates)

    prices = np.empty((n_days, n_tickers))
    prices[0] = 100.0
    daily_noise = rng.normal(scale=0.01, size=(n_days, n_tickers))
    # daily drift proportional to skill (constant per ticker across time), so
    # cumulative return over any window is monotonic in skill (and therefore
    # in the "score" fixture below)
    daily_drift = skill * 0.0006  # shape (n_tickers,)
    for t in range(1, n_days):
        prices[t] = prices[t - 1] * (1 + daily_drift + daily_noise[t])

    price_df = pd.DataFrame(prices, index=dates, columns=tickers)
    # score = skill itself, broadcast across all dates -> perfectly predicts
    # which names will keep drifting up vs down
    score_df = pd.DataFrame(
        np.tile(skill, (n_days, 1)), index=dates, columns=tickers
    )
    return price_df, score_df

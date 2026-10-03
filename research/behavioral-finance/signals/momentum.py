"""
Momentum-family behavioral signals.

Both signals below are cross-sectional: for each date, they rank tickers
against each other, which is what the decile backtest in backtest/engine.py
consumes. Input `prices` is a wide DataFrame (index=date, columns=ticker,
values=close), as returned by data.loaders.load_price_history.
"""
from __future__ import annotations

import pandas as pd


def momentum_12_1(prices: pd.DataFrame, lookback: int = 252, skip: int = 21) -> pd.DataFrame:
    """Jegadeesh & Titman (1993) 12-1 month momentum: cumulative return over the
    trailing ~12 months, EXCLUDING the most recent month (skip=21 trading days)
    to avoid the well-documented short-term reversal effect contaminating the
    signal. Behavioral mechanism: investors underreact to new information, so
    trends that are already underway tend to continue as the market gradually
    incorporates it.
    """
    lagged = prices.shift(skip)
    return lagged / lagged.shift(lookback - skip) - 1.0


def high_52w_proximity(prices: pd.DataFrame, window: int = 252) -> pd.DataFrame:
    """George & Hwang (2004) 52-week-high signal: current price as a fraction of
    its trailing 52-week high. Behavioral mechanism: anchoring -- investors use
    the 52-week high as a reference point and are slow to bid a stock through it
    even in the face of genuinely good news, so proximity to the high predicts
    continued (underreacted) upward drift.
    """
    rolling_high = prices.rolling(window, min_periods=window // 2).max()
    return prices / rolling_high

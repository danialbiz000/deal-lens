"""
Low-volatility anomaly signal, not previously tested in this project.

Input `prices` is a wide DataFrame (index=date, columns=ticker, values=close),
same convention as signals/momentum.py and signals/reversal.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def low_volatility_score(prices: pd.DataFrame, window: int = 252) -> pd.DataFrame:
    """Ang, Hodrick, Xing & Zhang (2006) / Frazzini & Pedersen (2014) low-volatility
    anomaly: trailing realized daily-return volatility, sign-flipped so that
    LOW-volatility names get the HIGH score this project's decile backtest goes
    long (backtest/engine.py: long the top decile, short the bottom). Under the
    standard CAPM, expected return should scale with beta/volatility; the
    anomaly is that it empirically doesn't -- low-volatility stocks have
    historically delivered comparable or higher risk-adjusted, and sometimes
    even raw, returns than high-volatility ones. Behavioral mechanism most
    commonly cited: leverage-constrained investors bid up high-beta/high-vol
    names to get extra expected return without borrowing, pushing their prices
    above and low-vol names' prices below what CAPM would predict (Frazzini &
    Pedersen's "betting against beta" framing), plus a lottery-preference
    effect (retail investors overpay for the small chance of a huge win that
    high-volatility names offer).
    """
    daily_returns = prices.pct_change()
    realized_vol = daily_returns.rolling(window, min_periods=window // 2).std()
    return -realized_vol

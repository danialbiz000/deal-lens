"""
Long-term reversal, not previously tested in this project. A third,
deliberately different family from momentum/52-week-high (underreaction)
and low-volatility/MAX (lottery demand): De Bondt & Thaler's overreaction
story operates on a multi-year horizon, the opposite prediction from
momentum's 12-1 month construction.

Input `prices` is a wide DataFrame (index=date, columns=ticker, values=close),
same convention as signals/momentum.py and signals/reversal.py.
"""
from __future__ import annotations

import pandas as pd


def long_term_reversal_score(prices: pd.DataFrame, lookback: int = 1260, skip: int = 252) -> pd.DataFrame:
    """De Bondt & Thaler (1985) long-term reversal: cumulative return over a
    multi-year formation period (default 5 years, ~1260 trading days),
    EXCLUDING the most recent year (skip=252 trading days) so this doesn't
    just mechanically overlap with momentum's own 12-1 month window. Sign-
    flipped so past LOSERS (large negative formation-period return) get the
    HIGH score this project's decile backtest goes long (backtest/engine.py:
    long the top decile, short the bottom) -- the opposite prediction from
    momentum. Behavioral mechanism: investors systematically overreact to a
    long run of bad (or good) news, pushing extreme past losers below and
    extreme past winners above fundamental value; over a multi-year horizon
    that overreaction is predicted to partially correct, so yesterday's
    biggest losers should outperform yesterday's biggest winners going
    forward -- the opposite mechanism from momentum's underreaction story,
    operating at a much longer horizon than signals/reversal.py's ~1-month
    short-term reversal.
    """
    lagged = prices.shift(skip)
    formation_return = lagged / lagged.shift(lookback - skip) - 1.0
    return -formation_return

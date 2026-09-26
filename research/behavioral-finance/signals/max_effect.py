"""
The MAX effect (lottery-demand anomaly), not previously tested in this
project. A different construction from signals/low_volatility.py: that
signal ranks by *average* dispersion over a year; this one ranks by the
single most extreme daily return over the past month, a direct proxy for
"has this name recently offered a lottery-ticket-like payoff."

Input `prices` is a wide DataFrame (index=date, columns=ticker, values=close),
same convention as signals/momentum.py and signals/reversal.py.
"""
from __future__ import annotations

import pandas as pd


def max_effect_score(prices: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    """Bali, Cakici & Whitelaw (2011): the single maximum daily return over
    the trailing month (MAX) cross-sectionally predicts *lower*, not higher,
    future returns -- the opposite of what a risk-return tradeoff would
    predict for a genuinely riskier name. Sign-flipped here so LOW-MAX names
    get the HIGH score this project's decile backtest goes long
    (backtest/engine.py: long the top decile, short the bottom), matching
    signals/low_volatility.py's convention. Behavioral mechanism: Barberis &
    Huang (2008)'s cumulative-prospect-theory investors overweight small
    probabilities of large gains and are willing to overpay for (and hence
    subsequently underperform in) stocks that have recently delivered a
    lottery-like payoff -- a related but distinct story from low-volatility's
    leverage-constraint mechanism, since MAX is about the single most extreme
    observation, not the average dispersion of returns, and Bali et al. show
    the two do not fully subsume one another empirically.
    """
    daily_returns = prices.pct_change()
    trailing_max = daily_returns.rolling(window, min_periods=window // 2).max()
    return -trailing_max

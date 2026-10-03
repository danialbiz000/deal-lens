"""Standard performance metrics for a daily return series."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def annualized_return(daily_returns: pd.Series) -> float:
    growth = (1.0 + daily_returns).prod()
    n_years = len(daily_returns) / TRADING_DAYS_PER_YEAR
    if n_years <= 0:
        return float("nan")
    return growth ** (1.0 / n_years) - 1.0


def annualized_vol(daily_returns: pd.Series) -> float:
    return daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def sharpe_ratio(daily_returns: pd.Series, risk_free_annual: float = 0.0) -> float:
    excess = daily_returns - risk_free_annual / TRADING_DAYS_PER_YEAR
    vol = excess.std()
    if vol == 0 or np.isnan(vol):
        return float("nan")
    return (excess.mean() / vol) * np.sqrt(TRADING_DAYS_PER_YEAR)


def max_drawdown(daily_returns: pd.Series) -> float:
    cumulative = (1.0 + daily_returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = cumulative / running_max - 1.0
    return drawdown.min()

"""Decile long-short backtest engine.

Methodology: at each monthly rebalance date, rank the universe by the signal
score, go equal-weighted long the top decile and equal-weighted short the
bottom decile, hold for one month, roll forward. This is the standard
methodology used in the momentum/reversal academic literature (Jegadeesh &
Titman 1993 and follow-ons), chosen so results are comparable to published
anomaly studies rather than to a bespoke design.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .metrics import annualized_return, annualized_vol, max_drawdown, sharpe_ratio


@dataclass
class BacktestResult:
    daily_returns_gross: pd.Series
    daily_returns_net: pd.Series
    daily_returns_long: pd.Series
    daily_returns_short: pd.Series
    turnover_by_month: pd.Series
    cost_bps: float
    n_deciles: int

    def summary(self) -> str:
        lines = [
            "Decile long-short backtest",
            f"  deciles={self.n_deciles}  cost={self.cost_bps}bps/unit turnover",
            f"  gross: ann.return={annualized_return(self.daily_returns_gross):.2%}  "
            f"ann.vol={annualized_vol(self.daily_returns_gross):.2%}  "
            f"Sharpe={sharpe_ratio(self.daily_returns_gross):.2f}  "
            f"maxDD={max_drawdown(self.daily_returns_gross):.2%}",
            f"  net:   ann.return={annualized_return(self.daily_returns_net):.2%}  "
            f"ann.vol={annualized_vol(self.daily_returns_net):.2%}  "
            f"Sharpe={sharpe_ratio(self.daily_returns_net):.2f}  "
            f"maxDD={max_drawdown(self.daily_returns_net):.2%}",
            f"  avg monthly turnover: {self.turnover_by_month.mean():.1%}",
        ]
        return "\n".join(lines)


def _month_end_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(index=index, data=index)
    return s.groupby([index.year, index.month]).last().values


def run_decile_backtest(
    prices: pd.DataFrame,
    scores: pd.DataFrame,
    n_deciles: int = 10,
    cost_bps: float = 10.0,
    min_names_per_side: int = 3,
) -> BacktestResult:
    """
    prices: date x ticker close prices
    scores: date x ticker signal score (e.g. from signals.composite.composite_score),
            same shape/alignment as prices
    cost_bps: linear transaction cost in basis points, applied per unit of
              portfolio turnover at each rebalance (a simplification -- see
              README.md "Explicit limitations")
    """
    daily_returns = prices.pct_change()
    rebalance_dates = _month_end_dates(prices.index)

    prev_weights = pd.Series(dtype=float)
    portfolio_daily = pd.Series(0.0, index=prices.index)
    long_leg_daily = pd.Series(0.0, index=prices.index)
    short_leg_daily = pd.Series(0.0, index=prices.index)
    turnover_records = {}

    for i, reb_date in enumerate(rebalance_dates[:-1]):
        next_reb_date = rebalance_dates[i + 1]
        period_mask = (prices.index > reb_date) & (prices.index <= next_reb_date)
        if not period_mask.any():
            continue

        cross_section = scores.loc[reb_date].dropna()
        n = len(cross_section)
        if n < min_names_per_side * n_deciles:
            continue

        ranked = cross_section.rank(pct=True)
        long_names = ranked[ranked >= 1.0 - 1.0 / n_deciles].index
        short_names = ranked[ranked <= 1.0 / n_deciles].index
        if len(long_names) < min_names_per_side or len(short_names) < min_names_per_side:
            continue

        weights = pd.Series(0.0, index=cross_section.index)
        weights[long_names] = 1.0 / len(long_names)
        weights[short_names] = -1.0 / len(short_names)

        aligned_prev = prev_weights.reindex(weights.index, fill_value=0.0)
        turnover = (weights - aligned_prev).abs().sum() / 2.0
        turnover_records[reb_date] = turnover

        period_returns = daily_returns.loc[period_mask, weights.index].fillna(0.0)
        portfolio_daily.loc[period_mask] = period_returns.mul(weights, axis=1).sum(axis=1)
        long_leg_daily.loc[period_mask] = period_returns.mul(weights.clip(lower=0.0), axis=1).sum(axis=1)
        short_leg_daily.loc[period_mask] = period_returns.mul(weights.clip(upper=0.0), axis=1).sum(axis=1)

        prev_weights = weights

    turnover_series = pd.Series(turnover_records)
    cost_drag_per_rebalance = turnover_series * (cost_bps / 10_000.0)

    net_returns = portfolio_daily.copy()
    for reb_date, drag in cost_drag_per_rebalance.items():
        if reb_date in net_returns.index:
            net_returns.loc[reb_date] -= drag

    return BacktestResult(
        daily_returns_gross=portfolio_daily,
        daily_returns_net=net_returns,
        daily_returns_long=long_leg_daily,
        daily_returns_short=short_leg_daily,
        turnover_by_month=turnover_series,
        cost_bps=cost_bps,
        n_deciles=n_deciles,
    )

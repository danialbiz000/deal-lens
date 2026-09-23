"""
Investigates why the 52-week-high (anchoring) signal lost money on both the
NSE and US Kaggle-mirror backtests (see README.md "Empirical results").

Two candidate explanations were flagged, neither confirmed:
  (a) momentum-crash risk (a generic property of "buy recent winners" -- the
      strategy is short volatility and can blow up in any sharp reversal), or
  (b) a value/growth confound specific to a secular bull market: shorting
      "far from 52-week-high" names may just mean shorting cheap/beaten-down
      names that then mean-revert upward, fighting the anchoring thesis.

This script tests (b) directly: it builds a simple price-only value proxy
(signals/value_proxy.py), measures how correlated it is with the raw
52-week-high score cross-sectionally, orthogonalizes the 52w-high signal
against it (regresses it out, date by date), and re-runs the backtest on the
residual "value-neutral" signal. If (b) were the dominant explanation, the
orthogonalized signal should lose much less money than the raw one. If it
still loses about as much, (b) is not the (main) explanation and (a) becomes
the more likely story.

Run: python investigations/52w_high_value_confound.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return, max_drawdown, sharpe_ratio
from data.loaders import load_nse_github_mirror, load_us_kaggle_mirror
from signals.momentum import high_52w_proximity
from signals.value_proxy import price_to_long_run_average


def cross_sectional_correlation(signal: pd.DataFrame, control: pd.DataFrame) -> float:
    common_cols = signal.columns.intersection(control.columns)
    corrs = []
    for date in signal.index:
        y = signal.loc[date, common_cols]
        x = control.loc[date, common_cols]
        valid = y.notna() & x.notna()
        if valid.sum() < 5:
            continue
        yv, xv = y[valid], x[valid]
        if yv.std() == 0 or xv.std() == 0:
            continue
        corrs.append(yv.corr(xv))
    return float(np.nanmean(corrs)) if corrs else float("nan")


def orthogonalize_cross_sectionally(signal: pd.DataFrame, control: pd.DataFrame) -> pd.DataFrame:
    """Date-by-date cross-sectional OLS of `signal` on `control`; returns the
    residuals, same shape as `signal`, NaN wherever there weren't enough
    valid pairs (<5) or `control` had no cross-sectional variance that day."""
    common_cols = signal.columns.intersection(control.columns)
    residuals = pd.DataFrame(np.nan, index=signal.index, columns=signal.columns)
    for date in signal.index:
        y = signal.loc[date, common_cols]
        x = control.loc[date, common_cols]
        valid = y.notna() & x.notna()
        if valid.sum() < 5:
            continue
        yv = y[valid].values.astype(float)
        xv = x[valid].values.astype(float)
        if xv.std() == 0:
            continue
        slope, intercept = np.polyfit(xv, yv, 1)
        resid = yv - (slope * xv + intercept)
        residuals.loc[date, valid.index[valid]] = resid
    return residuals


def run_for_market(name: str, prices: pd.DataFrame) -> None:
    print(f"\n{'=' * 60}\n{name}\n{'=' * 60}")
    raw_signal = high_52w_proximity(prices)
    value_proxy = price_to_long_run_average(prices)

    avg_corr = cross_sectional_correlation(raw_signal, value_proxy)
    print(f"Average cross-sectional correlation, 52w-high score vs. value proxy: {avg_corr:.3f}")

    print("Orthogonalizing (this loops over every trading date -- may take a bit)...")
    residual_signal = orthogonalize_cross_sectionally(raw_signal, value_proxy)

    raw_result = run_decile_backtest(prices, raw_signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    resid_result = run_decile_backtest(prices, residual_signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)

    def line(label, r):
        print(f"  {label:28s} ann_ret={annualized_return(r.daily_returns_gross):7.2%}  "
              f"gross_sharpe={sharpe_ratio(r.daily_returns_gross):6.2f}  "
              f"net_sharpe={sharpe_ratio(r.daily_returns_net):6.2f}  "
              f"maxDD={max_drawdown(r.daily_returns_gross):7.2%}")

    line("raw 52w-high signal", raw_result)
    line("value-orthogonalized", resid_result)


if __name__ == "__main__":
    run_for_market("NSE (India)", load_nse_github_mirror())
    run_for_market("US Kaggle mirror", load_us_kaggle_mirror())

"""
Tests the remaining candidate explanation for the 52-week-high signal's losses
(see README.md "Investigating the 52-week-high result"): generic momentum-crash
risk, as documented in Daniel & Moskowitz, "Momentum Crashes" (2016).

Their empirical finding, in plain terms: a "long recent winners, short recent
losers" strategy is exposed to occasional severe losses specifically when (a)
realized market volatility is elevated, and (b) the market has recently been
in a downturn ("bear" state) -- the classic setup being a sharp post-crash
rebound, where the SHORT leg (recent losers, which tend to be high-beta) snaps
back hard and the strategy is short exactly the wrong thing at exactly the
wrong time. Crucially, this predicts the damage should concentrate in the
SHORT leg specifically, not be symmetric across both legs.

This script builds the two regime indicators (realized volatility tercile,
trailing-12-month market state) from the same price data already used
elsewhere in this project, and reports strategy/long-leg/short-leg performance
conditional on each regime, plus return skewness, for both markets.

Run: python investigations/momentum_crash_risk.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return, sharpe_ratio
from data.loaders import load_nse_github_mirror, load_us_kaggle_mirror
from signals.momentum import high_52w_proximity

VOL_WINDOW = 21          # trading days, ~1 month, for realized volatility
MARKET_STATE_WINDOW = 252  # trading days, ~1 year, for trailing market return


def build_regime_indicators(prices: pd.DataFrame) -> pd.DataFrame:
    """Equal-weighted market proxy built from the same universe (no external
    index available), then: realized volatility tercile (Low/Mid/High, cut
    over the full sample -- a diagnostic threshold, not a live trading rule,
    see the note in README.md), and a trailing-12-month bear/bull flag.
    Both indicators are lagged by one day so a given day's regime label never
    uses that day's own return.
    """
    market_ret = prices.pct_change().mean(axis=1)
    realized_vol = market_ret.rolling(VOL_WINDOW).std() * np.sqrt(252)

    market_index = (1.0 + market_ret.fillna(0.0)).cumprod()
    trailing_return = market_index / market_index.shift(MARKET_STATE_WINDOW) - 1.0

    vol_tercile = pd.qcut(realized_vol, 3, labels=["Low", "Mid", "High"])

    regimes = pd.DataFrame({
        "vol_tercile": vol_tercile,
        "bear_state": trailing_return < 0,
    })
    regimes = regimes.shift(1)  # lag: today's regime label is as of yesterday's close
    # shift() on a bool column upcasts to object (NaN for the first rows), which
    # breaks `~`; nullable boolean dtype handles that NaN correctly instead.
    regimes["bear_state"] = regimes["bear_state"].astype("boolean")
    return regimes


def skew(series: pd.Series) -> float:
    s = series.dropna()
    return float(s.skew()) if len(s) > 2 else float("nan")


def report_conditional(label: str, daily: pd.Series, mask: pd.Series) -> None:
    clean_mask = mask.reindex(daily.index).fillna(False).astype(bool)
    sub = daily[clean_mask]
    if sub.dropna().empty:
        print(f"    {label:32s} (no data)")
        return
    print(f"    {label:32s} n_days={len(sub.dropna()):5d}  "
          f"ann_ret={annualized_return(sub):7.2%}  sharpe={sharpe_ratio(sub):6.2f}  "
          f"skew={skew(sub):6.2f}")


def run_for_market(name: str, prices: pd.DataFrame) -> None:
    print(f"\n{'=' * 70}\n{name}\n{'=' * 70}")
    signal = high_52w_proximity(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    regimes = build_regime_indicators(prices)

    print(f"Whole-sample skewness -- long-short: {skew(result.daily_returns_gross):.2f}  "
          f"long leg: {skew(result.daily_returns_long):.2f}  "
          f"short leg: {skew(result.daily_returns_short):.2f}")

    for leg_name, leg_returns in [
        ("long-short (combined)", result.daily_returns_gross),
        ("long leg only", result.daily_returns_long),
        ("short leg only", result.daily_returns_short),
    ]:
        print(f"\n  -- {leg_name} --")
        report_conditional("Low realized-vol tercile", leg_returns, regimes["vol_tercile"] == "Low")
        report_conditional("Mid realized-vol tercile", leg_returns, regimes["vol_tercile"] == "Mid")
        report_conditional("High realized-vol tercile", leg_returns, regimes["vol_tercile"] == "High")
        report_conditional("Bull state (trailing 12m > 0)", leg_returns, ~regimes["bear_state"])
        report_conditional("Bear state (trailing 12m < 0)", leg_returns, regimes["bear_state"])
        report_conditional(
            "Bear + High-vol (crash-rebound setup)",
            leg_returns,
            regimes["bear_state"] & (regimes["vol_tercile"] == "High"),
        )


if __name__ == "__main__":
    run_for_market("NSE (India)", load_nse_github_mirror())
    run_for_market("US Kaggle mirror", load_us_kaggle_mirror())

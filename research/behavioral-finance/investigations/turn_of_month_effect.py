"""
Milestone 38 (line P) tests a fourth new signal, deliberately chosen from a
genuinely different behavioral family than any of the six already coded.
Momentum/52-week-high (underreaction), short-term/long-term reversal
(overreaction at two different horizons), and low-volatility/MAX
(lottery-demand) are all CROSS-SECTIONAL: rank stocks against each other,
go long/short the extremes. This milestone tests a TIME-SERIES calendar
anomaly instead -- the turn-of-month effect (Ariel 1987; Lakonishok &
Smidt 1988) -- which doesn't rank stocks at all. It asks whether the
market AS A WHOLE returns more on a small, well-defined window of trading
days than on the rest of the month.

Definition (Lakonishok & Smidt 1988's exact window, the standard one in
the literature): the LAST trading day of a calendar month and the FIRST
THREE trading days of the next month -- a 4-trading-day window per month
boundary. Behavioral/institutional mechanism, genuinely distinct from
underreaction, overreaction, or lottery demand: month-end and month-start
concentrate real cash flows (payroll-driven retirement contributions,
mutual-fund inflows, pension rebalancing) and portfolio-manager
window-dressing, creating buying pressure independent of any individual
stock's characteristics or recent price history.

This also tests differently from every earlier signal in this project:
it's a LONG-ONLY market-timing question (is the market's own return higher
in this window?), not a cross-sectional long-short decile sort, so it does
not use run_decile_backtest at all -- just the project's own equal-weighted
market_proxy() and its standard HAC-regression significance test, applied
directly to a turn-of-month dummy variable. Run on all three markets, the
same immediate-full-scope discipline established since low-volatility
(Milestone 25).

Reuses market_proxy and hac_regression unchanged.

Run: python investigations/turn_of_month_effect.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from data.loaders import load_asx_github_mirror, load_nse_github_mirror, load_us_kaggle_mirror
from investigations.momentum_crash_significance import hac_regression
from investigations.short_leg_beta import market_proxy

HAC_LAGS_DAILY = 21
FIRST_N_DAYS = 3  # first N trading days of the month, plus the prior month's last day


def stars(p: float) -> str:
    if p != p:
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def turn_of_month_flags(index: pd.DatetimeIndex) -> pd.Series:
    """True on the last trading day of a month and the first FIRST_N_DAYS
    trading days of the next month (Lakonishok & Smidt 1988's window)."""
    key = index.year * 100 + index.month
    ordinal = pd.Series(np.arange(len(index)), index=index)
    day_num = ordinal.groupby(key).cumcount() + 1
    days_in_month = ordinal.groupby(key).transform("size")
    is_first_days = day_num <= FIRST_N_DAYS
    is_last_day = day_num == days_in_month
    return (is_first_days | is_last_day)


def run_market(label: str, prices: pd.DataFrame) -> None:
    print(f"\n{'=' * 90}\n{label}\n{'=' * 90}")
    market = market_proxy(prices).dropna()
    tom = turn_of_month_flags(market.index)

    tom_mean = market[tom].mean()
    non_tom_mean = market[~tom].mean()
    print(f"Trading days: {len(market)} total, {int(tom.sum())} turn-of-month "
          f"({tom.mean():.1%} of days), {int((~tom).sum())} rest-of-month")
    print(f"  Mean daily return, turn-of-month days:     {tom_mean:+.4%}  "
          f"(implied ann.: {tom_mean * 252:+.2%})")
    print(f"  Mean daily return, rest-of-month days:     {non_tom_mean:+.4%}  "
          f"(implied ann.: {non_tom_mean * 252:+.2%})")

    X = pd.DataFrame({"turn_of_month": tom.astype(float)}, index=market.index)
    fit = hac_regression(market, X, lags=HAC_LAGS_DAILY)
    const, tom_coef = float(fit.params["const"]), float(fit.params["turn_of_month"])
    p = float(fit.pvalues["turn_of_month"])
    print(f"  HAC regression: rest-of-month daily mean (const)={const:+.4%}, "
          f"turn-of-month ADD-ON={tom_coef:+.4%}  p={p:.4f}{stars(p)}")
    print(f"  Implied annualized turn-of-month premium: {tom_coef * 252:+.2%}/yr "
          f"(illustrative -- no strategy can be long only turn-of-month days)")

    if p < 0.10:
        print("\n  Sub-period breakdown (this project's own hard-learned lesson: never trust")
        print("  a pooled/full-sample result without checking non-overlapping sub-periods):")
        n_sub = 3
        boundaries = np.array_split(np.arange(len(market)), n_sub)
        for i, b in enumerate(boundaries, 1):
            sub_idx = market.index[b]
            sub_market = market.loc[sub_idx]
            sub_tom = tom.loc[sub_idx]
            sub_X = pd.DataFrame({"turn_of_month": sub_tom.astype(float)}, index=sub_idx)
            sub_fit = hac_regression(sub_market, sub_X, lags=HAC_LAGS_DAILY)
            sub_coef = float(sub_fit.params["turn_of_month"])
            sub_p = float(sub_fit.pvalues["turn_of_month"])
            print(f"    Sub-period {i} ({sub_idx.min().date()} to {sub_idx.max().date()}, "
                  f"n={len(sub_idx)}): add-on={sub_coef:+.4%}/day  p={sub_p:.4f}{stars(sub_p)}")


def main() -> None:
    run_market("NSE (India)", load_nse_github_mirror())
    run_market("US mirror", load_us_kaggle_mirror())
    run_market("ASX mirror", load_asx_github_mirror())


if __name__ == "__main__":
    print("Does the turn-of-month effect (Lakonishok & Smidt 1988) -- higher market returns")
    print("in the last trading day of a month and the first three of the next -- replicate")
    print("on any of this project's three markets? A time-series, long-only calendar question,")
    print("genuinely different from every cross-sectional signal tested so far.")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

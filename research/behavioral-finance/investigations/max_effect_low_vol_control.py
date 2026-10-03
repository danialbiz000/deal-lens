"""
Milestone 28 flagged, but left explicitly open, a pattern: two distinct
"lottery demand" signals (low-volatility, Milestone 25-26; MAX effect,
Milestone 28) both fail to replicate positively and both show some degree
of inversion on the US mirror specifically. Left unresolved: does that
shared US inversion reflect something structural about this dataset that
both signals happen to pick up independently, or are the two signals
substantially picking the same names, so the "two" inversions are really
one mechanism counted twice -- the identical question this project already
asked and answered directly for ASX momentum and 52-week-high (Milestones
23-24)?

A first check: the two signals' raw cross-sectional scores correlate at
~0.61 on the US mirror (sampled monthly, 1970-2017) -- substantial, but
well below the 0.76-0.82 that triggered Milestone 24's control regression
for ASX. Worth testing directly rather than left as a correlation
coefficient, per this project's own standing rule (Milestone 24's lesson):
regress MAX's hedged US combined-book return on low-volatility's, and check
whether MAX's intercept (alpha net of its low-volatility exposure) survives.

Reuses run_decile_backtest, build_hedged_return_series, hac_regression,
report_regression, and monthly_returns_at_rebalances unchanged.

Run: python investigations/max_effect_low_vol_control.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from backtest.engine import run_decile_backtest
from data.loaders import load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_significance import (
    hac_regression,
    monthly_returns_at_rebalances,
    report_regression,
)
from investigations.short_leg_beta import market_proxy
from signals.low_volatility import low_volatility_score
from signals.max_effect import max_effect_score

HAC_LAGS_DAILY = 21
HAC_LAGS_MONTHLY = 6


def hedged_series_for(signal_fn, prices: pd.DataFrame, market: pd.Series):
    signal = signal_fn(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    hedged_long, _ = build_hedged_return_series(result.daily_returns_long, market, reb_dates)
    hedged_gross, _ = build_hedged_return_series(result.daily_returns_gross, market, reb_dates)
    return reb_dates, hedged_long, hedged_gross


def run_control_check(label: str, y_daily: pd.Series, x_daily: pd.Series, reb_dates: pd.DatetimeIndex) -> None:
    print(f"\n-- {label} --")

    aligned_daily = pd.concat([y_daily.rename("y"), x_daily.rename("low_vol")], axis=1).dropna()
    print(f"   Daily (n={len(aligned_daily)}):")
    fit_daily = hac_regression(aligned_daily["y"], aligned_daily[["low_vol"]], lags=HAC_LAGS_DAILY)
    report_regression("   max_hedged ~ const + low_vol_hedged  (HAC)", fit_daily)

    y_monthly = monthly_returns_at_rebalances(y_daily, reb_dates)
    x_monthly = monthly_returns_at_rebalances(x_daily, reb_dates)
    aligned_monthly = pd.concat([y_monthly.rename("y"), x_monthly.rename("low_vol")], axis=1).dropna()
    print(f"\n   Monthly (n={len(aligned_monthly)}):")
    fit_monthly = hac_regression(aligned_monthly["y"], aligned_monthly[["low_vol"]], lags=HAC_LAGS_MONTHLY)
    report_regression("   max_hedged ~ const + low_vol_hedged  (HAC)", fit_monthly)


def main() -> None:
    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)

    lv_reb_dates, lv_long, lv_gross = hedged_series_for(low_volatility_score, prices, market)
    mx_reb_dates, mx_long, mx_gross = hedged_series_for(max_effect_score, prices, market)

    print("Does the MAX effect's US combined-book inversion survive controlling for")
    print("low-volatility exposure, or is it the same mechanism counted twice?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")

    run_control_check("Long leg: MAX hedged return ~ low-vol hedged return", mx_long, lv_long, mx_reb_dates)
    run_control_check(
        "Combined long-short: MAX hedged return ~ low-vol hedged return",
        mx_gross, lv_gross, mx_reb_dates,
    )


if __name__ == "__main__":
    main()

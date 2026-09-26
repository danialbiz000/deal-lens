"""
Milestone 23 found ASX 52-week-high's hedged alpha significant at both
frequencies, but left explicitly open which of two stories explains it:
genuine, independent 52-week-high anchoring skill, or the same underlying
mechanism as momentum's own ASX result (Milestone 22), showing up because
the two signals' leg returns are highly correlated (0.76-0.82) on this
market. The natural test that distinguishes them -- momentum held constant
as an explicit control, rather than just compared after the fact -- was
named as future work, not run.

This milestone runs it: regress 52-week-high's out-of-sample-hedged return
series on momentum's own out-of-sample-hedged return series (both already
built exactly as in Milestones 22-23), and check whether 52-week-high's
intercept (alpha net of its momentum exposure) is still significant. If it
survives, 52-week-high has incremental information beyond momentum on ASX.
If it collapses once momentum is controlled for, Milestone 23's "same
mechanism" reading is confirmed directly rather than just suggested by a
correlation coefficient.

Reuses run_decile_backtest, build_hedged_return_series, hac_regression,
report_regression, and monthly_returns_at_rebalances unchanged.

Run: python investigations/momentum_control_asx_52w_high.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from backtest.engine import run_decile_backtest
from data.loaders import load_asx_github_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_significance import (
    hac_regression,
    monthly_returns_at_rebalances,
    report_regression,
)
from investigations.short_leg_beta import market_proxy
from signals.momentum import high_52w_proximity, momentum_12_1

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

    aligned_daily = pd.concat([y_daily.rename("y"), x_daily.rename("momentum")], axis=1).dropna()
    print(f"   Daily (n={len(aligned_daily)}):")
    fit_daily = hac_regression(aligned_daily["y"], aligned_daily[["momentum"]], lags=HAC_LAGS_DAILY)
    report_regression("   52w_high_hedged ~ const + momentum_hedged  (HAC)", fit_daily)

    y_monthly = monthly_returns_at_rebalances(y_daily, reb_dates)
    x_monthly = monthly_returns_at_rebalances(x_daily, reb_dates)
    aligned_monthly = pd.concat([y_monthly.rename("y"), x_monthly.rename("momentum")], axis=1).dropna()
    print(f"\n   Monthly (n={len(aligned_monthly)}):")
    fit_monthly = hac_regression(aligned_monthly["y"], aligned_monthly[["momentum"]], lags=HAC_LAGS_MONTHLY)
    report_regression("   52w_high_hedged ~ const + momentum_hedged  (HAC)", fit_monthly)


def main() -> None:
    prices = load_asx_github_mirror()
    market = market_proxy(prices)

    mom_reb_dates, mom_long, mom_gross = hedged_series_for(momentum_12_1, prices, market)
    hi_reb_dates, hi_long, hi_gross = hedged_series_for(high_52w_proximity, prices, market)

    print("Does ASX 52-week-high's hedged alpha survive controlling for momentum exposure?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")

    run_control_check("Long leg: 52w-high hedged return ~ momentum hedged return", hi_long, mom_long, hi_reb_dates)
    run_control_check(
        "Combined long-short: 52w-high hedged return ~ momentum hedged return",
        hi_gross, mom_gross, hi_reb_dates,
    )


if __name__ == "__main__":
    main()

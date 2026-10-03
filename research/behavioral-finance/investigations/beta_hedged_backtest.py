"""
Closes the loop opened by investigations/short_leg_beta.py (Milestone 6):
that script found the 52-week-high long-short book carries a significant,
uncontrolled net market beta, and that its full-sample regression alpha is
statistically indistinguishable from zero. The natural next step, flagged
explicitly in README.md and FRAMEWORK.md but not yet done: build an actual
beta-HEDGED version of the strategy -- not just a static, full-sample
regression coefficient -- and test whether real, tradable, beta-independent
return survives.

Methodology, and why it's a stronger test than Milestone 6's regression
alone: Milestone 6 estimated one beta for the entire sample and asked "is
the average residual different from zero" after the fact. This script
estimates beta on a ROLLING, OUT-OF-SAMPLE basis instead -- at each monthly
rebalance, beta is estimated only from the preceding ~1 year of daily
returns (never using data from the holding period being hedged), and that
beta is used to hedge the NEXT month's daily returns. This mirrors how a
real fund would operationally hedge (re-estimate periodically, apply
forward, never look ahead) and lets beta drift over time, rather than
assuming one fixed number for the whole sample -- a materially different
and more realistic test, not a re-derivation of the same number.

Run: python investigations/beta_hedged_backtest.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return, annualized_vol, sharpe_ratio
from data.loaders import load_nse_github_mirror, load_us_kaggle_mirror
from investigations.momentum_crash_significance import hac_regression, monthly_returns_at_rebalances, report_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import high_52w_proximity

ROLLING_BETA_WINDOW = 252  # trading days (~1 year) of trailing history used to estimate beta
MIN_BETA_HISTORY = 126     # don't hedge until at least this much trailing history exists
HAC_LAGS_DAILY = 21
HAC_LAGS_MONTHLY = 6


def rolling_beta(strategy_ret: pd.Series, market_ret: pd.Series, as_of: pd.Timestamp) -> float | None:
    """OLS beta of strategy on market, using only data with index <= as_of,
    over the trailing ROLLING_BETA_WINDOW days -- strictly out-of-sample for
    anything after `as_of`."""
    window = strategy_ret.loc[:as_of].tail(ROLLING_BETA_WINDOW)
    market_window = market_ret.loc[:as_of].tail(ROLLING_BETA_WINDOW)
    aligned = pd.concat([window.rename("s"), market_window.rename("m")], axis=1).dropna()
    if len(aligned) < MIN_BETA_HISTORY or aligned["m"].std() == 0:
        return None
    # OLS slope, not a manual cov/var ratio -- np.cov defaults to ddof=1 while
    # np.var defaults to ddof=0, a mismatched-degrees-of-freedom bug that biases
    # every beta estimate by a factor of n/(n-1); np.polyfit avoids it entirely.
    beta, _intercept = np.polyfit(aligned["m"], aligned["s"], 1)
    return float(beta)


def build_hedged_return_series(
    combined_ret: pd.Series, market_ret: pd.Series, reb_dates: pd.DatetimeIndex
) -> tuple[pd.Series, pd.Series]:
    """Returns (hedged_return, beta_used) daily series, hedged only where a
    valid trailing beta was available (earlier dates are NaN, not zero)."""
    hedged = pd.Series(np.nan, index=combined_ret.index)
    beta_used = pd.Series(np.nan, index=combined_ret.index)

    for i in range(len(reb_dates) - 1):
        start, end = reb_dates[i], reb_dates[i + 1]
        beta = rolling_beta(combined_ret, market_ret, as_of=start)
        if beta is None:
            continue
        period_mask = (combined_ret.index > start) & (combined_ret.index <= end)
        hedged.loc[period_mask] = combined_ret.loc[period_mask] - beta * market_ret.loc[period_mask]
        beta_used.loc[period_mask] = beta

    return hedged, beta_used


def run_for_market(name: str, prices: pd.DataFrame) -> None:
    print(f"\n{'=' * 78}\n{name}\n{'=' * 78}")
    signal = high_52w_proximity(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    market = market_proxy(prices)
    reb_dates = result.turnover_by_month.index

    hedged, beta_used = build_hedged_return_series(result.daily_returns_gross, market, reb_dates)
    covered = hedged.notna()
    n_covered = int(covered.sum())
    print(f"Rolling out-of-sample beta hedge covers {n_covered} trading days "
          f"(needs {ROLLING_BETA_WINDOW}d trailing history before it can start).")
    print(f"Hedge beta over the covered period: mean={beta_used[covered].mean():.3f}  "
          f"std={beta_used[covered].std():.3f}  "
          f"(compare to Milestone 6's single full-sample estimate)")

    unhedged_covered = result.daily_returns_gross[covered]
    hedged_covered = hedged[covered]
    residual_corr = hedged_covered.corr(market[covered])
    print(f"Correlation of HEDGED returns with the market (should be near zero if the hedge "
          f"worked): {residual_corr:.3f}  (unhedged correlation was strongly negative -- see "
          f"Milestone 6)")

    print(f"\nUnhedged combined book, same covered period: "
          f"ann_ret={annualized_return(unhedged_covered):.2%}  "
          f"ann_vol={annualized_vol(unhedged_covered):.2%}  "
          f"sharpe={sharpe_ratio(unhedged_covered):.2f}")
    print(f"Beta-hedged book,   same covered period: "
          f"ann_ret={annualized_return(hedged_covered):.2%}  "
          f"ann_vol={annualized_vol(hedged_covered):.2%}  "
          f"sharpe={sharpe_ratio(hedged_covered):.2f}")

    print("\n### Is the hedged return significantly different from zero? ###")
    X_const = pd.DataFrame(index=hedged_covered.index)  # HAC regression with intercept only
    report_regression(
        "DAILY: hedged_return ~ const  (HAC lag=21)",
        hac_regression(hedged_covered, X_const, lags=HAC_LAGS_DAILY),
    )

    # only compound over rebalance dates from after the rolling window warmed up,
    # so no month is contaminated by an artificial "0 return" during warm-up
    first_covered_date = hedged.index[covered][0]
    warm_reb_dates = reb_dates[reb_dates >= first_covered_date]
    monthly_hedged = monthly_returns_at_rebalances(hedged, warm_reb_dates)
    X_const_m = pd.DataFrame(index=monthly_hedged.index)
    report_regression(
        "MONTHLY: hedged_return ~ const  (HAC lag=6)",
        hac_regression(monthly_hedged, X_const_m, lags=HAC_LAGS_MONTHLY),
    )


if __name__ == "__main__":
    print("Rolling, out-of-sample beta hedge (re-estimated every rebalance from the preceding")
    print(f"{ROLLING_BETA_WINDOW} trading days only) applied to the combined long-short book.")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    run_for_market("NSE (India)", load_nse_github_mirror())
    run_for_market("US Kaggle mirror", load_us_kaggle_mirror())

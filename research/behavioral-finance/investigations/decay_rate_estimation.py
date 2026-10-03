"""
Milestones 9-13 established that momentum's long leg and reversal's long
leg both carry genuine, out-of-sample-hedged alpha that is strong before
roughly 1994 and not statistically distinguishable from zero after --
but every test so far used a single, somewhat arbitrary binary cut
(1994-01-01, chosen as "~1 year after Jegadeesh & Titman's 1993
publication"). A binary split answers "was there a difference before vs.
after this one date," not "how fast did the edge erode, and when did it
actually cross zero." This milestone quantifies the decay directly rather
than assuming a step function at an arbitrary date.

Method: for each signal's long leg, build the same rolling, out-of-sample
beta-hedged daily return series used since Milestone 7 (252-day window),
over the FULL sample -- no pre/post split -- then regress:

    hedged_return_t = alpha + slope * (years since first hedged day) + e_t

with Newey-West (HAC) standard errors. `alpha` is the fitted level at the
start of the hedged sample; `slope` is the estimated annual rate of change
in daily alpha, in return units per year -- a direct, continuous measure
of the decay rate, together with a p-value testing whether that rate is
significantly different from zero. From (alpha, slope) this script also
computes the implied zero-crossing date: the calendar date at which the
fitted trend line crosses zero, i.e. this project's best point estimate
of "when did the edge actually run out," as an alternative and cross-check
to the fixed 1994 cutoff used everywhere else in this project.

As a non-parametric sanity check on the linear-trend assumption, the
script also reports a rolling 5-year-window annualized return trajectory
(stepped every ~1 year) -- so the fitted straight line can be compared
against the actual, non-parametric shape of the decline, and the reader
can judge whether "linear decay" is a reasonable description or an
oversimplification of a messier pattern (e.g. a sharper drop, a plateau,
or a partial recovery).

Run: python investigations/decay_rate_estimation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return
from data.loaders import load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_significance import hac_regression, monthly_returns_at_rebalances, report_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1
from signals.reversal import short_term_reversal

HAC_LAGS_DAILY = 21
HAC_LAGS_MONTHLY = 6
ROLLING_WINDOW_YEARS = 5
STEP_TRADING_DAYS = 252  # advance the rolling window by ~1 year each step

SIGNALS = {
    "12-1 momentum": momentum_12_1,
    "short-term reversal": short_term_reversal,
}


def stars(p: float) -> str:
    if np.isnan(p):
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def years_since_start(index: pd.DatetimeIndex, start: pd.Timestamp) -> pd.Series:
    return pd.Series((index - start).days / 365.25, index=index)


def fit_trend(hedged: pd.Series, lags: int, freq_label: str) -> dict:
    hedged = hedged.dropna()
    start = hedged.index.min()
    trend = years_since_start(hedged.index, start)
    X = pd.DataFrame({"years_since_start": trend})
    fit = hac_regression(hedged, X, lags=lags)
    alpha0 = float(fit.params["const"])
    slope = float(fit.params["years_since_start"])
    slope_p = float(fit.pvalues["years_since_start"])
    alpha0_p = float(fit.pvalues["const"])

    zero_crossing_years = -alpha0 / slope if slope != 0 else float("nan")
    zero_crossing_date = start + pd.Timedelta(days=zero_crossing_years * 365.25) if np.isfinite(zero_crossing_years) else None

    print(f"  [{freq_label}] hedged_return ~ const(alpha0) + slope*years_since_start  (HAC lag={lags}, n={int(fit.nobs)})")
    print(f"    alpha0 (annualized, at start): {alpha0 * (252 if freq_label == 'daily' else 12):+.2%}  p={alpha0_p:.4f}{stars(alpha0_p)}")
    print(f"    slope  (annualized change/yr): {slope * (252 if freq_label == 'daily' else 12):+.2%}/yr  p={slope_p:.4f}{stars(slope_p)}")
    if zero_crossing_date is not None and hedged.index.min() <= zero_crossing_date <= hedged.index.max() + pd.Timedelta(days=365 * 5):
        print(f"    implied zero-crossing date: {zero_crossing_date.date()}  "
              f"({zero_crossing_years:.1f} years after hedge coverage began {start.date()})")
    else:
        print(f"    implied zero-crossing date: outside/near sample edge or ill-conditioned "
              f"(raw estimate {zero_crossing_years:.1f} years after {start.date()})")

    return {
        "alpha0_ann": alpha0 * (252 if freq_label == "daily" else 12),
        "slope_ann": slope * (252 if freq_label == "daily" else 12),
        "slope_p": slope_p,
        "zero_crossing_date": zero_crossing_date,
    }


def rolling_trajectory(hedged: pd.Series) -> None:
    hedged = hedged.dropna()
    window = ROLLING_WINDOW_YEARS * 252
    if len(hedged) < window:
        print("    (not enough hedged history for a 5-year rolling trajectory)")
        return
    print(f"    Rolling {ROLLING_WINDOW_YEARS}-year annualized return trajectory (stepped ~1yr, window END date shown):")
    i = window
    while i <= len(hedged):
        chunk = hedged.iloc[i - window:i]
        end_date = chunk.index[-1]
        print(f"      window ending {end_date.date()}: ann_ret={annualized_return(chunk):+7.2%}")
        i += STEP_TRADING_DAYS


def main() -> None:
    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)

    for name, fn in SIGNALS.items():
        print(f"\n{'#' * 90}\n# {name.upper()} -- LONG LEG, CONTINUOUS DECAY-RATE ESTIMATE\n{'#' * 90}")
        signal = fn(prices)
        result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
        reb_dates = result.turnover_by_month.index
        hedged, _beta_used = build_hedged_return_series(result.daily_returns_long, market, reb_dates)

        fit_trend(hedged, HAC_LAGS_DAILY, "daily")
        monthly = monthly_returns_at_rebalances(hedged, reb_dates)
        fit_trend(monthly, HAC_LAGS_MONTHLY, "monthly")

        print("\n  Non-parametric sanity check on the linear-trend assumption:")
        rolling_trajectory(hedged)


if __name__ == "__main__":
    print("Quantifying the decay rate directly (linear time trend on the out-of-sample hedged")
    print("return series) instead of a single, arbitrary 1994 binary cut.")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10\n")
    main()

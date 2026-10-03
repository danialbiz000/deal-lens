"""
Milestone 17 found a tentative post-2008 NSE momentum signal (long leg,
daily p=0.044, monthly p=0.073, marginal) using this project's own rolling
out-of-sample hedge -- but flagged a real, unresolved caveat: the NSE
mirror's universe itself grew from ~30 names in 2000 to a full 48 by late
2010, so part of the apparent post-2008 improvement could reflect a less
thin, better-populated cross-section rather than a genuine change in the
underlying economics. That caveat was named but never tested.

This milestone tests it directly. Checking the NSE mirror's daily coverage
count confirms the universe was still growing through early-to-mid 2010 (45
of 48 names as of 2009, reaching 48 by late 2010) but has been PERFECTLY
FIXED at exactly 48 names, with zero further growth or shrinkage, every
single day from 2010-11-04 through the end of the sample (2021-04-30) --
roughly 10.5 of the ~12.7 years in Milestone 17's "post-2008" window. That
split gives a clean test the universe-growth caveat itself invites: does
the tentative signal survive when restricted to ONLY the years where the
universe cannot possibly be a confound, because it never changed size at
all?

Two sub-windows within Milestone 17's post-2008-09 era:
  - "Growing" (2008-09-01 to 2010-11-03): universe still expanding, 45-47
    of 48 names -- the window the growth-confound concern is actually
    about.
  - "Stable" (2010-11-04 onward): universe fixed at exactly 48 names,
    every day, for the rest of the sample -- a universe-growth confound is
    definitionally impossible here.

Reuses check_plain_alpha (Milestone 17) unchanged, and this project's
standard decile backtest + out-of-sample hedge pipeline.

Run: python investigations/momentum_nse_universe_growth_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from backtest.engine import run_decile_backtest
from data.loaders import load_nse_github_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_mechanism_nse import check_plain_alpha
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

BREAK_DATE = pd.Timestamp("2008-09-01")   # same as Milestones 14/16/17/18
STABLE_DATE = pd.Timestamp("2010-11-04")  # first day the universe is fixed at 48 names for good


def describe_universe_growth(prices: pd.DataFrame) -> None:
    avail = prices.notna().sum(axis=1)
    below_48 = avail[avail < 48]
    print("NSE universe coverage (names with data that day):")
    print(f"  2000 average: {avail[avail.index.year == 2000].mean():.1f} of 48")
    print(f"  2008 average: {avail[avail.index.year == 2008].mean():.1f} of 48")
    print(f"  Last date below 48 names: {below_48.index.max().date()}")
    print(f"  Fixed at exactly 48 names, every day, from {STABLE_DATE.date()} through "
          f"{prices.index.max().date()} ({(prices.index.max() - STABLE_DATE).days / 365.25:.1f} years)")


def main() -> None:
    prices = load_nse_github_mirror()
    describe_universe_growth(prices)

    market = market_proxy(prices)
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index

    hedged_long, _beta = build_hedged_return_series(result.daily_returns_long, market, reb_dates)
    post_2008 = hedged_long[hedged_long.index >= BREAK_DATE]
    growing = hedged_long[(hedged_long.index >= BREAK_DATE) & (hedged_long.index < STABLE_DATE)]
    stable = hedged_long[hedged_long.index >= STABLE_DATE]

    print(f"\nSample sizes: post-2008 full={len(post_2008.dropna())}  "
          f"growing (2008-09 to 2010-11)={len(growing.dropna())}  "
          f"stable, fixed-48 (2010-11 onward)={len(stable.dropna())}")

    print("\nLong leg, out-of-sample hedged. Newey-West (HAC) standard errors.")
    print("*** p<0.01  ** p<0.05  * p<0.10\n")
    check_plain_alpha("POST-2008 FULL (Milestone 17's original window)", post_2008, reb_dates)
    check_plain_alpha("GROWING (2008-09 to 2010-11, universe still expanding)", growing, reb_dates)
    check_plain_alpha("STABLE (2010-11 onward, universe fixed at 48 names)", stable, reb_dates)


if __name__ == "__main__":
    print("Does Milestone 17's tentative post-2008 NSE momentum signal survive restricting to")
    print("the years where the universe is definitionally fixed, ruling out a growth confound?")
    main()

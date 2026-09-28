"""
Milestone 52 (line AF) runs a walk-forward-style consistency check this
project has never applied to its own CURRENT recommendation. Milestone
37's walk-forward test asked whether a naive selection process, run on
only pre-1994 US data, would have picked momentum over low-volatility --
a question about the past. This milestone asks the analogous question
about the present: does the cross-market combined book (Milestones 45,
49, 50, 51 -- ASX momentum + NSE turn-of-month) actually survive the
same walk-forward and sub-period discipline this project has applied to
every other finding, or was it quietly built on a shortcut?

Two specific gaps motivate this. First, Milestone 38's own sub-period
breakdown found NSE turn-of-month's add-on insignificant in its most
recent generic tercile (2014-03-03 to 2021-04-30, p=0.125) -- but that
tercile boundary was never checked against the SPECIFIC window the
combined book actually uses (2010-11-01 to 2015-11-30, from Milestone
45's own ASX-date-range clipping), which only partially overlaps it.
Second, Milestones 45/49/50/51 never asked whether the turn-of-month
signal would have been selectable walk-forward -- using only NSE data
available BEFORE that window began -- or whether it was only visible in
hindsight, the exact failure mode Milestone 37 found for low-volatility.

Part 1 (true walk-forward): restricting to NSE data strictly before the
combined book's window starts (pre-2010-11-01), is the turn-of-month
add-on significant using Milestone 38's own HAC-regression-with-dummy
methodology? Part 2 (post-hoc consistency): is the add-on significant
specifically WITHIN the exact window the combined book uses, rather than
relying on Milestone 38's generic tercile split, which doesn't align to
it? Part 3 states, rather than silently skips, a genuine constraint this
milestone cannot get around: ASX momentum's own window (2010-11 to
2015-11) already IS essentially ASX's full usable sample after its 12-1
month lookback, leaving no earlier or later ASX data to run the same
walk-forward logic against on that leg.

Reuses turn_of_month_flags, HAC_LAGS_DAILY from turn_of_month_effect.py
(Milestone 38); hac_regression from momentum_crash_significance.py;
market_proxy from short_leg_beta.py; and asx_momentum_leg from
cross_market_combined_portfolio.py (Milestone 45) -- all unchanged.

Run: python investigations/turn_of_month_walkforward_consistency.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from data.loaders import load_nse_github_mirror
from investigations.cross_market_combined_portfolio import asx_momentum_leg
from investigations.momentum_crash_significance import hac_regression
from investigations.short_leg_beta import market_proxy
from investigations.turn_of_month_effect import HAC_LAGS_DAILY, turn_of_month_flags


def stars(p: float) -> str:
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def tom_addon(market: pd.Series) -> tuple[float, float, int]:
    tom = turn_of_month_flags(market.index)
    X = pd.DataFrame({"turn_of_month": tom.astype(float)}, index=market.index)
    fit = hac_regression(market, X, lags=HAC_LAGS_DAILY)
    return float(fit.params["turn_of_month"]), float(fit.pvalues["turn_of_month"]), len(market)


def main() -> None:
    print("Milestone 37 asked whether a naive selection process, run on only earlier data,")
    print("would have picked this project's own currently-trusted finding. This milestone asks")
    print("the same question of the project's CURRENT recommendation -- the cross-market combined")
    print("book (Milestones 45, 49, 50, 51) -- rather than only ever asking it of the past.\n")

    nse = market_proxy(load_nse_github_mirror()).dropna()
    asx_leg = asx_momentum_leg()
    window_start, window_end = asx_leg.index.min(), asx_leg.index.max()
    print(f"Combined book's actual NSE window (Milestone 45's ASX-date-range clipping): "
          f"{window_start.date()} to {window_end.date()}\n")

    print(f"{'=' * 100}\nPart 1: TRUE walk-forward -- using only NSE data available BEFORE the "
          f"combined book's window began, would turn-of-month have been selectable?\n{'=' * 100}")
    pre_window = nse.loc[:window_start]
    coef_pre, p_pre, n_pre = tom_addon(pre_window)
    print(f"  Pre-{window_start.date()} NSE data (n={n_pre}, {nse.index.min().date()} to "
          f"{window_start.date()}): add-on={coef_pre:+.4%}/day  p={p_pre:.4f}{stars(p_pre)}")
    print(f"  {'YES' if p_pre < 0.05 else 'NO'} -- a selection process run at that point, using "
          f"only data available then, would{' ' if p_pre < 0.05 else ' NOT '}have flagged NSE "
          f"turn-of-month as worth including.\n")

    print(f"{'=' * 100}\nPart 2: post-hoc consistency -- is the add-on significant specifically "
          f"WITHIN the exact window the combined book uses (not Milestone 38's generic "
          f"tercile split, which does not align to it)?\n{'=' * 100}")
    in_window = nse.loc[window_start:window_end]
    coef_win, p_win, n_win = tom_addon(in_window)
    print(f"  Combined-book window (n={n_win}, {window_start.date()} to {window_end.date()}): "
          f"add-on={coef_win:+.4%}/day  p={p_win:.4f}{stars(p_win)}")
    print(f"  For comparison, Milestone 38's own generic tercile split flagged its most recent "
          f"third (2014-03-03 to 2021-04-30) as insignificant (p=0.125) -- that boundary only "
          f"partially overlaps the window actually used here; testing the ACTUAL window directly, "
          f"rather than relying on a generic split that doesn't align to it, is the right check.")
    print(f"  {'YES' if p_win < 0.05 else 'NO'} -- the specific window the combined book actually "
          f"traded {'is' if p_win < 0.05 else 'is NOT'} statistically consistent with a real "
          f"turn-of-month effect, not merely a lucky draw from a decayed signal.\n")

    print(f"{'=' * 100}\nPart 3: a genuine constraint, stated rather than skipped\n{'=' * 100}")
    print(f"  ASX momentum's own window ({window_start.date()} to {window_end.date()}) already "
          f"IS essentially ASX's full usable sample once the 12-1 month signal's own lookback is "
          f"applied to ASX's {asx_leg.index.min().year}-{asx_leg.index.max().year} data. There is "
          f"no earlier ASX data to run a true walk-forward selection against on that leg, and no "
          f"later ASX data (this project's ASX mirror ends 2015-12-30) to test whether the pick "
          f"would have held up going forward. This is a hard data constraint this project has "
          f"named before (Milestone 34) and cannot get around here -- stated honestly rather than "
          f"silently narrowing the walk-forward check to only the leg that can support one.")


if __name__ == "__main__":
    main()

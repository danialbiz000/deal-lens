"""
Milestone 27 is a retroactive audit, not a new test of a new question.
Milestone 26 found that a cumulative "does it hold from date X onward" sweep
cannot distinguish a persisting effect from one episode pooled with several
quiet decades -- and that this project's own low-volatility inversion had
exactly that problem. But that sweep methodology (investigations/
reversal_1980_break_diagnostics.py's ROBUSTNESS_STARTS pattern) was used
FIRST, back in Milestones 15-16, to validate the two headline conclusions
this project has rested on ever since: that reversal's edge is null "from
every start date" and that momentum's pre-1994 edge is significant "from
every start date through 1990." Neither of those has ever been re-checked
with the non-overlapping-decade version of the test Milestone 26 just used
on itself. This milestone closes that gap, plus a second one: ASX's two
positive findings (momentum's "cleanest replication yet," and low-
volatility's long-leg signal) have never had the ticker-concentration /
leave-one-out check Milestone 26 ran on the US mirror, even though the
underlying methodology (a small, fixed universe ranked into deciles) is
identical.

Two parts:

PART A -- non-overlapping decade breakdown of the US mirror's original
reversal-vs-momentum cumulative sweep (Milestones 15-16), on both signals'
out-of-sample-hedged long legs. Two specific risks a pure cumulative sweep
cannot rule out:
  - reversal's "null at every start date" could still mask two offsetting
    decades (one strongly positive, one strongly negative) that a pooled
    or cumulative test would report as "no effect," which is a different
    and more interesting finding than "no effect anywhere."
  - momentum's "significant through 1990" could itself be concentrated in
    one decade rather than persisting evenly pre-1994, the same pattern
    Milestone 26 just found for the low-volatility inversion.

PART B -- ticker-concentration and leave-one-out checks for ASX momentum
(Milestone 22) and ASX low-volatility's long leg (Milestone 25), which have
never had this check even though the US mirror's identical methodology
(Milestone 26) found it mattered there. ASX's universe (209 names) is far
less thin than the US mirror's (30), so the prior is that this check should
come back clean -- worth confirming rather than assuming.

Run: python investigations/pooled_window_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

from collections import Counter

import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return
from data.loaders import load_asx_github_mirror, load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_mechanism_nse import check_plain_alpha
from investigations.momentum_crash_significance import hac_regression
from investigations.short_leg_beta import market_proxy
from signals.low_volatility import low_volatility_score
from signals.momentum import momentum_12_1
from signals.reversal import short_term_reversal

N_DECILES = 5
HAC_LAGS_DAILY = 21
US_DECADE_WINDOWS = [
    ("1970-01-01", "1979-12-31"),
    ("1980-01-01", "1989-12-31"),
    ("1990-01-01", "1999-12-31"),
    ("2000-01-01", "2009-12-31"),
    ("2010-01-01", "2017-12-31"),
]


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


def decade_breakdown(label: str, hedged: pd.Series) -> None:
    print(f"\n  -- {label}: non-overlapping decade breakdown --")
    for start, end in US_DECADE_WINDOWS:
        sub = hedged.loc[start:end].dropna()
        if len(sub) < 20:
            print(f"    {start[:4]}-{end[:4]}: insufficient data (n={len(sub)})")
            continue
        fit = hac_regression(sub, pd.DataFrame(index=sub.index), lags=HAC_LAGS_DAILY)
        alpha, p = float(fit.params["const"]), float(fit.pvalues["const"])
        print(f"    {start[:4]}-{end[:4]}: n={len(sub):5d}  ann.ret={annualized_return(sub):+8.2%}  "
              f"daily alpha p={p:.4f}{stars(p)}")


def part_a_us_decade_audit() -> None:
    print("\n" + "=" * 90)
    print("PART A -- non-overlapping decade breakdown of the original US reversal/momentum")
    print("cumulative-sweep conclusions (Milestones 15-16)")
    print("=" * 90)
    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)

    for name, signal_fn in [("short-term reversal", short_term_reversal), ("12-1 momentum (control)", momentum_12_1)]:
        scores = signal_fn(prices)
        result = run_decile_backtest(prices, scores, n_deciles=N_DECILES, cost_bps=10.0, min_names_per_side=2)
        reb_dates = result.turnover_by_month.index
        hedged, _beta = build_hedged_return_series(result.daily_returns_long, market, reb_dates)
        decade_breakdown(name, hedged.dropna())


def month_end_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(index.to_series().groupby([index.year, index.month]).max().values))


def leg_membership(scores: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    reb_dates = month_end_dates(prices.index)
    rows = []
    for d in reb_dates:
        if d not in scores.index:
            continue
        cross_section = scores.loc[d].dropna()
        if len(cross_section) == 0:
            continue
        ranked = cross_section.rank(pct=True)
        long_names = ranked[ranked >= 1.0 - 1.0 / N_DECILES].index.tolist()
        short_names = ranked[ranked <= 1.0 / N_DECILES].index.tolist()
        rows.append((d, long_names, short_names))
    return pd.DataFrame(rows, columns=["date", "long_names", "short_names"]).set_index("date")


def concentration_and_leave_one_out(label: str, signal_fn, prices: pd.DataFrame, market: pd.Series, leg: str) -> None:
    print(f"\n  -- {label} --")
    scores = signal_fn(prices)
    membership = leg_membership(scores, prices)
    col = "long_names" if leg == "long" else "short_names"
    counts = Counter()
    for names in membership[col]:
        counts.update(names)
    n_reb = len(membership)
    top = counts.most_common(5)
    print(f"    {leg} leg ticker concentration, {n_reb} rebalances:")
    for ticker, n in top:
        print(f"      {ticker}: present {n}/{n_reb} months ({n / n_reb:.0%})")

    top_ticker, top_n = top[0]
    if top_n / n_reb < 0.5:
        print(f"    No single ticker present in >50% of months (max {top_n / n_reb:.0%}) -- "
              f"skipping leave-one-out, concentration is not high enough to warrant it.")
        return

    reduced_prices = prices.drop(columns=[top_ticker])
    reduced_signal = signal_fn(reduced_prices)
    result = run_decile_backtest(reduced_prices, reduced_signal, n_deciles=N_DECILES, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    leg_returns = result.daily_returns_long if leg == "long" else result.daily_returns_gross
    hedged, _beta = build_hedged_return_series(leg_returns, market, reb_dates)
    check_plain_alpha(f"    without {top_ticker} (out-of-sample hedged)", hedged.dropna(), reb_dates)


def part_b_asx_concentration_audit() -> None:
    print("\n" + "=" * 90)
    print("PART B -- ticker concentration / leave-one-out check for ASX's two positive findings")
    print("(never checked before, even though the US mirror's identical check, Milestone 26,")
    print("found it mattered there)")
    print("=" * 90)
    prices = load_asx_github_mirror()
    market = market_proxy(prices)
    print(f"\nASX universe: {prices.shape[1]} tickers (vs. the US mirror's 30) -- expect this to come back clean.")

    concentration_and_leave_one_out("ASX momentum (Milestone 22), long leg", momentum_12_1, prices, market, "long")
    concentration_and_leave_one_out("ASX low-volatility (Milestone 25), long leg", low_volatility_score, prices, market, "long")


def main() -> None:
    part_a_us_decade_audit()
    part_b_asx_concentration_audit()


if __name__ == "__main__":
    print("Milestone 27: retroactive audit. Applying Milestone 26's own two tools (non-overlapping")
    print("decade breakdown; ticker concentration + leave-one-out) to the project's earlier")
    print("cumulative-sweep-validated conclusions that were never re-checked this way.")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

"""
Milestone 37 (line Q) tests an explicit limitation this project has named
since its first commit and never checked: "No out-of-sample / walk-forward
validation is wired up by default." Every prior milestone's out-of-sample
hedge (Milestones 7, 10 onward) validates a SINGLE signal's return against
its own trailing history -- a different question from the one a real
systematic-strategy developer actually faces: choosing WHICH signal to
trade among several candidates, using only the data available at decision
time. That kind of selection is exactly where data-snooping / overfitting
risk usually hides -- pick the best-looking backtest among several
candidates and you are, on average, picking noise plus signal, not signal
alone.

This project has coded six signal constructions and tested each
individually. This milestone asks the walk-forward question directly: if
an investor in 1994 had access only to pre-1994 US mirror data, ranked all
six candidate signals by in-sample out-of-sample-hedged significance, and
picked the best-looking one -- would that pick have held up over the
next ~24 years (1994-2017)? 1994 is not an arbitrary date: it is the exact
publication-era cutoff this project has used since Milestone 9 for
momentum's own decay analysis, reused here as the natural in-sample /
out-of-sample split.

An important scope caveat, stated up front rather than glossed over: this
is a statistical selection-bias test, not a literal historical-investor
simulation. Three of the six signal FORMULAS (low-volatility,
Frazzini-Pedersen 2014; MAX, Bali/Cakici/Whitelaw 2011; and to a lesser
extent 52-week-high, George/Hwang 2004) were not published, in the form
coded here, until well after 1994 -- a real 1994 investor could not have
run them. What this milestone tests is narrower and still meaningful: given
a FIXED set of candidate constructions (as this project has coded them),
does selecting the in-sample winner by backtested significance alone
reliably identify the signal that continues to work, or does it just as
often pick a signal whose apparent edge doesn't survive -- the generic
data-snooping risk that applies regardless of when each formula was
discovered.

Reuses run_decile_backtest, build_hedged_return_series, hac_regression,
and market_proxy unchanged; the six signal-scoring functions are called
with each project's own file's own default parameters.

Run: python investigations/walkforward_signal_selection.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return
from data.loaders import load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_significance import hac_regression
from investigations.short_leg_beta import market_proxy
from signals.long_term_reversal import long_term_reversal_score
from signals.low_volatility import low_volatility_score
from signals.max_effect import max_effect_score
from signals.momentum import high_52w_proximity, momentum_12_1
from signals.reversal import short_term_reversal

ANCHOR_DATE = "1994-01-01"  # the same publication-era cutoff used since Milestone 9
N_DECILES = 5
HAC_LAGS_DAILY = 21

SIGNALS = {
    "Momentum (12-1)": momentum_12_1,
    "52-week-high": high_52w_proximity,
    "Short-term reversal": short_term_reversal,
    "Low-volatility": low_volatility_score,
    "MAX effect": max_effect_score,
    "Long-term reversal": long_term_reversal_score,
}


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


def hac_alpha(y: pd.Series, lags: int) -> tuple[float, float]:
    y = y.dropna()
    if len(y) < 20:
        return float("nan"), float("nan")
    fit = hac_regression(y, pd.DataFrame(index=y.index), lags=lags)
    return float(fit.params["const"]), float(fit.pvalues["const"])


def evaluate_signal(name: str, score_fn, prices: pd.DataFrame, market: pd.Series) -> dict:
    signal = score_fn(prices)
    result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    hedged, _beta = build_hedged_return_series(result.daily_returns_gross, market, reb_dates)

    in_sample = hedged.loc[:ANCHOR_DATE].dropna()
    out_sample = hedged.loc[ANCHOR_DATE:].dropna()
    in_alpha, in_p = hac_alpha(in_sample, HAC_LAGS_DAILY)
    out_alpha, out_p = hac_alpha(out_sample, HAC_LAGS_DAILY)
    return {
        "name": name,
        "in_ann": annualized_return(in_sample) if len(in_sample) > 20 else float("nan"),
        "in_p": in_p,
        "in_n": len(in_sample),
        "out_ann": annualized_return(out_sample) if len(out_sample) > 20 else float("nan"),
        "out_p": out_p,
        "out_n": len(out_sample),
    }


def main() -> None:
    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)

    rows = [evaluate_signal(name, fn, prices, market) for name, fn in SIGNALS.items()]

    print(f"Anchor date: {ANCHOR_DATE} (the same publication-era cutoff used since Milestone 9)")
    print(f"\n{'Signal':<22}{'In-sample (pre-1994)':<28}{'Out-of-sample (post-1994)':<28}")
    print("-" * 78)
    for r in rows:
        in_str = f"{r['in_ann']:+7.2%} p={r['in_p']:.4f}{stars(r['in_p'])} (n={r['in_n']})"
        out_str = f"{r['out_ann']:+7.2%} p={r['out_p']:.4f}{stars(r['out_p'])} (n={r['out_n']})"
        print(f"{r['name']:<22}{in_str:<28}{out_str:<28}")

    ranked = sorted(rows, key=lambda r: (r["in_p"] != r["in_p"], r["in_p"]))
    print(f"\n{'=' * 78}\nRanked by in-sample (pre-1994) significance -- what a walk-forward "
          f"selection\nprocess using only data available at the time would have picked:\n{'=' * 78}")
    for rank, r in enumerate(ranked, 1):
        held_up = "HELD UP out-of-sample" if (r["out_p"] == r["out_p"] and r["out_p"] < 0.10) else "did NOT hold up out-of-sample"
        print(f"  {rank}. {r['name']:<22} in-sample p={r['in_p']:.4f}{stars(r['in_p']):3s} "
              f"-> out-of-sample p={r['out_p']:.4f}{stars(r['out_p']):3s}  [{held_up}]")

    winner = ranked[0]
    print(f"\nIn-sample winner: {winner['name']} (p={winner['in_p']:.4f})")
    print(f"That signal's out-of-sample result: ann.ret={winner['out_ann']:+.2%}, "
          f"p={winner['out_p']:.4f}{stars(winner['out_p'])}")


if __name__ == "__main__":
    print("If an investor in 1994 had picked the best-looking of this project's six candidate")
    print("signals using only pre-1994 US mirror data, would that pick have held up since?")
    print("Newey-West (HAC) standard errors, out-of-sample beta-hedged returns throughout.")
    print("*** p<0.01  ** p<0.05  * p<0.10\n")
    main()

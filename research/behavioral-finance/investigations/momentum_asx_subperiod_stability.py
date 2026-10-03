"""
Milestone 34 (line N) closes the last item this project's own Conclusions
have named as genuinely open: whether ASX momentum's edge (Milestone 22,
the cleanest replication in the whole project) is stable across
sub-periods the way the US finding eventually was shown to be (Milestones
9-13), or whether -- like the US mirror's own pre/post-1994 decay, or the
low-volatility inversion's concentration in a single decade -- it is
secretly carried by one narrow window within the six-year ASX sample.

ASX's sample (2009-10-20 to 2015-12-30, ~1501 trading days) is far too
short for the US mirror's decade-by-decade treatment, so this milestone
uses the coarsest split that still says something: three consecutive
~500-trading-day (~2-year) sub-periods, each tested with this project's
standard out-of-sample hedge + HAC methodology. A rolling-beta stability
check (mean/std per sub-period, mirroring the beta-stability diagnostics
already run for the US mirror and ASX low-volatility in earlier
milestones) is included too, since an edge that looks stable in raw return
but rests on wildly different beta exposure across sub-periods would be a
different kind of instability than a return-level one.

Reuses run_decile_backtest, build_hedged_return_series, check_plain_alpha,
hac_regression, and market_proxy unchanged.

Run: python investigations/momentum_asx_subperiod_stability.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return
from data.loaders import load_asx_github_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_mechanism_nse import check_plain_alpha
from investigations.momentum_crash_significance import hac_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

N_DECILES = 5
N_SUBPERIODS = 3


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


def split_into_subperiods(index: pd.DatetimeIndex, n: int) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    boundaries = np.array_split(np.arange(len(index)), n)
    return [(index[b[0]], index[b[-1]]) for b in boundaries]


def run_subperiod(label: str, hedged: pd.Series, start, end) -> None:
    sub = hedged.loc[start:end].dropna()
    if len(sub) < 20:
        print(f"    {label}: insufficient data (n={len(sub)})")
        return
    fit = hac_regression(sub, pd.DataFrame(index=sub.index), lags=21)
    alpha, p = float(fit.params["const"]), float(fit.pvalues["const"])
    print(f"    {label} ({start.date()} to {end.date()}, n={len(sub)}): "
          f"ann.ret={annualized_return(sub):+8.2%}  daily alpha p={p:.4f}{stars(p)}")


def beta_stability(beta_series: pd.Series, subperiods: list[tuple]) -> None:
    print("\n  Rolling-beta stability by sub-period:")
    for i, (start, end) in enumerate(subperiods, 1):
        sub_beta = beta_series.loc[start:end].dropna()
        if len(sub_beta) == 0:
            continue
        print(f"    Sub-period {i} ({start.date()} to {end.date()}): "
              f"mean beta={sub_beta.mean():+.3f}  std={sub_beta.std():.3f}  "
              f"min={sub_beta.min():+.3f}  max={sub_beta.max():+.3f}")


def main() -> None:
    prices = load_asx_github_mirror()
    market = market_proxy(prices)
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index

    subperiods = split_into_subperiods(prices.index, N_SUBPERIODS)
    print(f"ASX sample split into {N_SUBPERIODS} sub-periods of ~{len(prices) // N_SUBPERIODS} trading days each:")
    for i, (start, end) in enumerate(subperiods, 1):
        print(f"  Sub-period {i}: {start.date()} to {end.date()}")

    for leg_name, leg_returns in [
        ("long leg", result.daily_returns_long),
        ("combined long-short", result.daily_returns_gross),
    ]:
        print(f"\n{'=' * 90}\n{leg_name}\n{'=' * 90}")
        hedged, beta_used = build_hedged_return_series(leg_returns, market, reb_dates)
        hedged = hedged.dropna()

        full_daily_ret = annualized_return(hedged)
        print(f"  Full sample: ann.ret={full_daily_ret:+.2%}")
        check_plain_alpha("  full sample (out-of-sample hedged)", hedged, reb_dates)

        print("\n  Sub-period breakdown (out-of-sample-hedged daily alpha):")
        for i, (start, end) in enumerate(subperiods, 1):
            run_subperiod(f"Sub-period {i}", hedged, start, end)

        beta_stability(beta_used, subperiods)


if __name__ == "__main__":
    print("Is ASX momentum's edge (Milestone 22, the cleanest replication in this project)")
    print("stable across sub-periods, or concentrated in one narrow window of its 6-year sample?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

"""
Milestone 14's Quandt-Andrews search found short-term reversal's long leg
has a genuine, statistically significant structural break (bootstrap
p=0.048) around August 1980 -- but offered no explanation for *why* that
date, or whether it reflects anything about markets at all. At the user's
explicit request, this milestone investigates the mechanism directly,
rather than treating "August 1980" as a fact to report and move past.

Three checks:

1. Universe-size diagnostic: for both reversal and (as a control) momentum,
   count how many tickers have valid data and how many end up in the
   decile long leg at each rebalance from the 1970s through the mid-1980s.
2. Data-quality check: scan for extreme (>50% in one day) return moves in
   this era, the usual fingerprint of an unadjusted stock split or a raw
   data error, which would be a mundane and different explanation from a
   genuine small-sample problem.
3. Robustness re-test: rerun each signal's out-of-sample-hedged long-leg
   significance test starting from a range of candidate dates, to see
   whether the "edge" found in earlier milestones depends on including the
   thinnest, earliest years of the sample, or holds up once they're
   excluded.

Run: python investigations/reversal_1980_break_diagnostics.py
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
from signals.momentum import momentum_12_1
from signals.reversal import short_term_reversal

N_DECILES = 5
DIAGNOSTIC_WINDOW = ("1972-01-01", "1985-12-31")
ROBUSTNESS_STARTS = ["1972-01-01", "1978-01-01", "1980-08-29", "1981-01-01",
                      "1983-01-01", "1985-01-01", "1987-01-01", "1990-01-01",
                      "1995-01-01", "2000-01-01"]
HAC_LAGS_DAILY = 21


def month_end_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(index.to_series().groupby([index.year, index.month]).max().values))


def universe_diagnostic(name: str, scores: pd.DataFrame, prices: pd.DataFrame) -> None:
    print(f"\n--- Universe / long-leg size over time: {name} ---")
    reb_dates = month_end_dates(prices.index)
    rows = []
    for d in reb_dates:
        if d not in scores.index:
            continue
        cross_section = scores.loc[d].dropna()
        n = len(cross_section)
        if n == 0:
            continue
        ranked = cross_section.rank(pct=True)
        n_long = int((ranked >= 1.0 - 1.0 / N_DECILES).sum())
        rows.append((d, n, n_long))
    df = pd.DataFrame(rows, columns=["date", "n_universe", "n_long_leg"]).set_index("date")
    sample = df.loc[DIAGNOSTIC_WINDOW[0]:DIAGNOSTIC_WINDOW[1]]
    # print one row every ~6 months to keep output compact
    print(sample.iloc[::12].to_string())
    print(f"  min/median/max long-leg size, {DIAGNOSTIC_WINDOW[0]} to {DIAGNOSTIC_WINDOW[1]}: "
          f"{sample['n_long_leg'].min()} / {sample['n_long_leg'].median():.0f} / {sample['n_long_leg'].max()}")


def data_quality_check(prices: pd.DataFrame) -> None:
    print(f"\n--- Data-quality check: extreme single-day moves, {DIAGNOSTIC_WINDOW[0]} to {DIAGNOSTIC_WINDOW[1]} ---")
    sub = prices.loc[DIAGNOSTIC_WINDOW[0]:DIAGNOSTIC_WINDOW[1]]
    tickers = sub.columns[sub.notna().sum() > 0].tolist()
    print(f"  Tickers with any data in this window: {tickers}")
    rets = sub.pct_change()
    extreme = rets[rets.abs() > 0.5]
    any_found = False
    for col in extreme.columns:
        vals = extreme[col].dropna()
        if len(vals):
            any_found = True
            print(f"  {col}: {len(vals)} day(s) with |return|>50% -- possible data issue")
    if not any_found:
        print("  No single-day moves exceeding 50% found -- rules out a simple unadjusted-split/data-error "
              "explanation for the extreme early returns.")


def hac_alpha(y: pd.Series, lags: int = HAC_LAGS_DAILY) -> tuple[float, float]:
    y = y.dropna()
    if len(y) < 20:
        return float("nan"), float("nan")
    X = pd.DataFrame(index=y.index)
    fit = hac_regression(y, X, lags=lags)
    return float(fit.params["const"]), float(fit.pvalues["const"])


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


def robustness_check(name: str, hedged: pd.Series) -> None:
    print(f"\n--- Robustness of {name}'s long-leg alpha to excluding the earliest years ---")
    for start in ROBUSTNESS_STARTS:
        sub = hedged[hedged.index >= start].dropna()
        if sub.empty:
            continue
        alpha, p = hac_alpha(sub)
        print(f"  from {start}: n={len(sub):6d}  ann_ret={annualized_return(sub):+7.2%}  "
              f"daily alpha p={p:.4f}{stars(p)}")


def main() -> None:
    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)

    momentum_scores = momentum_12_1(prices)
    reversal_scores = short_term_reversal(prices)

    universe_diagnostic("short-term reversal", reversal_scores, prices)
    universe_diagnostic("12-1 momentum (control)", momentum_scores, prices)
    data_quality_check(prices)

    for name, scores in [("short-term reversal", reversal_scores), ("12-1 momentum (control)", momentum_scores)]:
        result = run_decile_backtest(prices, scores, n_deciles=N_DECILES, cost_bps=10.0, min_names_per_side=2)
        reb_dates = result.turnover_by_month.index
        hedged, _beta = build_hedged_return_series(result.daily_returns_long, market, reb_dates)
        robustness_check(name, hedged)


if __name__ == "__main__":
    print("Investigating the mechanism behind Milestone 14's August 1980 reversal break:")
    print("is it a real market regime, or an artifact of a thin, survivorship-biased early universe?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

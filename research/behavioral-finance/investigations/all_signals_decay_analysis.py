"""
Milestones 9-12 built up a specific, well-tested toolkit (a rolling,
out-of-sample beta hedge, split pre/post 1994) and applied it only to 12-1
momentum, because that was the one signal with significant full-sample
alpha to test. But two other signals exist in this project's library --
the 52-week-high signal and short-term reversal -- and both were declared
dead based on a FULL-SAMPLE beta-adjusted regression (Milestones 6-8): no
significant alpha across the whole ~1970-2017 US sample. That full-sample
verdict could be hiding the same pattern found for momentum: a signal
that was genuinely, significantly positive before some point and decayed
to noise since, with the decay masking the earlier edge in a single
full-sample average. This has never been checked, because until Milestone
9-10's toolkit existed there was no reason to look for a decay pattern in
a signal that already looked dead.

This is a genuine exploration, not a retest of an already-answered
question: NSE momentum was already shown (Milestone 8) to have no
significant full-sample alpha, so re-running the pre/post-1994 hedge on it
would just reconfirm a known null. Applying the SAME toolkit to the two
OTHER US signals asks a new question this project has not yet asked: is
"real edge before ~1994, decayed since" a momentum-specific story, or a
broader feature of how predictable the US market's cross-section of
returns was before institutional/quant crowding scaled up in the 1990s?

For each of the three signals (12-1 momentum, 52-week-high proximity,
short-term reversal), on the US mirror, this script builds the long leg,
short leg, and combined book, hedges each with the same rolling
out-of-sample beta hedge used in Milestones 7/10/11 (252-day window), and
reports the pre-1994 vs. post-1994 HAC alpha for every leg.

Run: python investigations/all_signals_decay_analysis.py
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
from investigations.beta_hedged_backtest import ROLLING_BETA_WINDOW, build_hedged_return_series
from investigations.momentum_crash_significance import hac_regression, monthly_returns_at_rebalances, report_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import high_52w_proximity, momentum_12_1
from signals.reversal import short_term_reversal

HAC_LAGS_DAILY = 21
HAC_LAGS_MONTHLY = 6
PUBLICATION_CUTOFF = pd.Timestamp("1994-01-01")

SIGNALS = {
    "12-1 momentum": momentum_12_1,
    "52-week-high": high_52w_proximity,
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


def hac_alpha(y: pd.Series, lags: int) -> tuple[float, float]:
    y = y.dropna()
    if len(y) < 20:
        return float("nan"), float("nan")
    X = pd.DataFrame(index=y.index)
    fit = hac_regression(y, X, lags=lags)
    return float(fit.params["const"]), float(fit.pvalues["const"])


def era_stats(hedged: pd.Series, reb_dates: pd.DatetimeIndex, start: pd.Timestamp, end: pd.Timestamp | None) -> dict:
    era = hedged[hedged.index >= start]
    if end is not None:
        era = era[era.index < end]
    era = era.dropna()
    if era.empty:
        return {"n": 0, "ann_ret": float("nan"), "daily_p": float("nan"), "monthly_p": float("nan")}
    daily_alpha, daily_p = hac_alpha(era, HAC_LAGS_DAILY)
    era_reb = reb_dates[(reb_dates >= era.index.min()) & (reb_dates <= era.index.max())]
    monthly = monthly_returns_at_rebalances(hedged, era_reb).dropna() if len(era_reb) >= 8 else pd.Series(dtype=float)
    _, monthly_p = hac_alpha(monthly, HAC_LAGS_MONTHLY) if len(monthly) >= 8 else (float("nan"), float("nan"))
    return {"n": len(era), "ann_ret": annualized_return(era), "daily_p": daily_p, "monthly_p": monthly_p}


def run_signal(name: str, signal_fn, prices: pd.DataFrame, market: pd.Series, summary: list[dict]) -> None:
    print(f"\n{'#' * 90}\n# {name.upper()}\n{'#' * 90}")
    signal = signal_fn(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index

    legs = [
        ("long leg", result.daily_returns_long),
        ("short leg", result.daily_returns_short),
        ("combined", result.daily_returns_gross),
    ]
    for leg_name, leg_returns in legs:
        hedged, _beta_used = build_hedged_return_series(leg_returns, market, reb_dates)
        pre = era_stats(hedged, reb_dates, prices.index.min(), PUBLICATION_CUTOFF)
        post = era_stats(hedged, reb_dates, PUBLICATION_CUTOFF, None)
        print(f"  {leg_name:10s} | pre-1994:  n={pre['n']:5d}  ann_ret={pre['ann_ret']:+7.2%}  "
              f"daily_p={pre['daily_p']:.3f}{stars(pre['daily_p']):3s} monthly_p={pre['monthly_p']:.3f}{stars(pre['monthly_p'])}")
        print(f"  {'':10s} | post-1994: n={post['n']:5d}  ann_ret={post['ann_ret']:+7.2%}  "
              f"daily_p={post['daily_p']:.3f}{stars(post['daily_p']):3s} monthly_p={post['monthly_p']:.3f}{stars(post['monthly_p'])}")
        summary.append({
            "signal": name, "leg": leg_name,
            "pre_ann_ret": pre["ann_ret"], "pre_daily_p": pre["daily_p"],
            "post_ann_ret": post["ann_ret"], "post_daily_p": post["daily_p"],
        })


def main() -> None:
    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)
    summary: list[dict] = []
    for name, fn in SIGNALS.items():
        run_signal(name, fn, prices, market, summary)

    print(f"\n{'=' * 90}\nSUMMARY -- out-of-sample hedged alpha, pre- vs. post-1994, all three US signals\n{'=' * 90}")
    df = pd.DataFrame(summary)
    print(df.to_string(index=False, formatters={
        "pre_ann_ret": lambda v: f"{v:+.2%}",
        "pre_daily_p": lambda p: f"{p:.3f}{stars(p)}",
        "post_ann_ret": lambda v: f"{v:+.2%}",
        "post_daily_p": lambda p: f"{p:.3f}{stars(p)}",
    }))


if __name__ == "__main__":
    print(f"Rolling out-of-sample beta hedge ({ROLLING_BETA_WINDOW}d window), pre/post-1994 split,")
    print("applied to ALL THREE US signals -- not just momentum. Is 'real pre-1994, decayed since' a")
    print("momentum-specific story, or a market-wide one?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10\n")
    main()

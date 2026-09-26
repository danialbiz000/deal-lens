"""
Milestone 10 found that momentum's post-1994 alpha is not statistically
significant once hedged out-of-sample, in either leg. The user asked to
investigate that result in depth rather than stop there. Two questions it
leaves open:

1. Is the post-1994 weakness a smooth, broad decay (consistent with the
   publication-decay story tested in Milestone 9), or is it concentrated in
   a specific regime -- most plausibly the well-documented 2009 "momentum
   crash" (Daniel & Moskowitz, 2016, "Momentum Crashes", Review of
   Financial Studies): past losers that momentum strategies were
   underweighting/shorting rebounded violently in the market recovery that
   followed the 2008 crisis, producing catastrophic, concentrated losses
   for momentum strategies in a way that is mechanically distinct from a
   slow, uniform crowding-driven decay. If Milestone 10's null result is
   really just a handful of crash months, that is a very different,
   narrower conclusion than "the edge quietly eroded."
2. Is the "no significant post-1994 alpha" finding itself an artifact of
   the specific 252-trading-day rolling hedge window chosen in Milestones
   7/10, rather than a robust feature of the data?

This script runs three checks on the post-1994 hedged return series, built
the same way as Milestone 10 (investigations/momentum_hedged_decay_backtest.py):

  (1) Sub-period breakdown -- splits post-1994 into distinct multi-year eras
      (pre-dot-com-bust, dot-com bust, pre-crisis bull run, 2008-09 crisis,
      post-crisis) and reports the hedged annualized return and HAC alpha
      in each, to see WHERE any weakness or strength is concentrated.
  (2) Momentum-crash-window exclusion test -- carves out a March-August 2009
      window (the period Daniel & Moskowitz identify as the crash) from the
      post-1994 hedged series and re-runs the HAC regression with and
      without it, to see whether excluding it restores significance.
  (3) Hedge-window robustness -- reruns Milestone 10's entire analysis with
      three different rolling beta windows (126, 252, 378 trading days) to
      check whether the post-1994 null result depends on the specific
      window chosen, or holds regardless.

NOTE on the crash window: this project's sandboxed environment cannot reach
an external source to pull Daniel & Moskowitz's exact published crash-date
boundaries, so March 1, 2009 - August 31, 2009 is used as a reasonable,
literature-consistent approximation (the market bottomed March 9, 2009 and
the sharpest momentum reversal losses are documented in the following
months) -- stated explicitly as an approximation, not a precisely sourced
figure, consistent with this project's standard of flagging exactly this
kind of provenance gap elsewhere (see README's "Data provenance" sections).

Run: python investigations/momentum_decay_regime_analysis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return, annualized_vol, sharpe_ratio
from data.loaders import load_us_kaggle_mirror
from investigations.momentum_crash_significance import hac_regression, monthly_returns_at_rebalances, report_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

HAC_LAGS_DAILY = 21
HAC_LAGS_MONTHLY = 6
PUBLICATION_CUTOFF = pd.Timestamp("1994-01-01")
CRASH_START = pd.Timestamp("2009-03-01")
CRASH_END = pd.Timestamp("2009-08-31")

ERAS = [
    ("1994-1999 (post-pub., pre-dot-com)", pd.Timestamp("1994-01-01"), pd.Timestamp("1999-12-31")),
    ("2000-2002 (dot-com bust)", pd.Timestamp("2000-01-01"), pd.Timestamp("2002-12-31")),
    ("2003-2007 (pre-crisis bull run)", pd.Timestamp("2003-01-01"), pd.Timestamp("2007-12-31")),
    ("2008-2009 (crisis + momentum crash)", pd.Timestamp("2008-01-01"), pd.Timestamp("2009-12-31")),
    ("2010-2017 (post-crisis)", pd.Timestamp("2010-01-01"), pd.Timestamp("2017-12-31")),
]


def rolling_beta(strategy_ret: pd.Series, market_ret: pd.Series, as_of: pd.Timestamp, window: int, min_history: int) -> float | None:
    win = strategy_ret.loc[:as_of].tail(window)
    market_win = market_ret.loc[:as_of].tail(window)
    aligned = pd.concat([win.rename("s"), market_win.rename("m")], axis=1).dropna()
    if len(aligned) < min_history or aligned["m"].std() == 0:
        return None
    beta, _ = np.polyfit(aligned["m"], aligned["s"], 1)
    return float(beta)


def build_hedged_return_series(
    combined_ret: pd.Series, market_ret: pd.Series, reb_dates: pd.DatetimeIndex, window: int, min_history: int
) -> pd.Series:
    hedged = pd.Series(np.nan, index=combined_ret.index)
    for i in range(len(reb_dates) - 1):
        start, end = reb_dates[i], reb_dates[i + 1]
        beta = rolling_beta(combined_ret, market_ret, as_of=start, window=window, min_history=min_history)
        if beta is None:
            continue
        mask = (combined_ret.index > start) & (combined_ret.index <= end)
        hedged.loc[mask] = combined_ret.loc[mask] - beta * market_ret.loc[mask]
    return hedged


def hac_alpha(y: pd.Series, lags: int) -> tuple[float, float]:
    y = y.dropna()
    if len(y) < 20:
        return float("nan"), float("nan")
    X = pd.DataFrame(index=y.index)
    fit = hac_regression(y, X, lags=lags)
    return float(fit.params["const"]), float(fit.pvalues["const"])


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


def check1_subperiod_breakdown(hedged: pd.Series, reb_dates: pd.DatetimeIndex, leg_name: str) -> None:
    print(f"\n{'=' * 90}\nCHECK 1 -- Sub-period breakdown ({leg_name})\n{'=' * 90}")
    for label, start, end in ERAS:
        era = hedged[(hedged.index >= start) & (hedged.index <= end)].dropna()
        if era.empty:
            print(f"  {label:40s}  no data")
            continue
        ann_ret = annualized_return(era)
        daily_alpha, daily_p = hac_alpha(era, HAC_LAGS_DAILY)
        era_reb = reb_dates[(reb_dates >= era.index.min()) & (reb_dates <= era.index.max())]
        monthly = monthly_returns_at_rebalances(hedged, era_reb).dropna() if len(era_reb) >= 8 else pd.Series(dtype=float)
        monthly_alpha, monthly_p = hac_alpha(monthly, HAC_LAGS_MONTHLY) if len(monthly) >= 8 else (float("nan"), float("nan"))
        print(f"  {label:40s}  n={len(era):5d}d  ann_ret={ann_ret:+7.2%}  "
              f"daily_alpha_p={daily_p:.3f}{stars(daily_p):3s}  monthly_alpha_p={monthly_p:.3f}{stars(monthly_p)}")


def check2_crash_exclusion(hedged: pd.Series, leg_name: str) -> None:
    print(f"\n{'=' * 90}\nCHECK 2 -- Momentum-crash-window (Mar-Aug 2009) exclusion test ({leg_name})\n{'=' * 90}")
    post = hedged[hedged.index >= PUBLICATION_CUTOFF].dropna()
    crash_mask = (post.index >= CRASH_START) & (post.index <= CRASH_END)
    crash_window = post[crash_mask]
    ex_crash = post[~crash_mask]

    print(f"  Crash window ({CRASH_START.date()} to {CRASH_END.date()}): {len(crash_window)} trading days, "
          f"ann_ret={annualized_return(crash_window):+.2%}, cumulative_ret={((1 + crash_window).prod() - 1):+.2%}")

    a_with, p_with = hac_alpha(post, HAC_LAGS_DAILY)
    a_without, p_without = hac_alpha(ex_crash, HAC_LAGS_DAILY)
    print(f"  Post-1994 daily alpha WITH crash window:    coef={a_with:+.5f}  p={p_with:.3f}{stars(p_with)}  (n={len(post)})")
    print(f"  Post-1994 daily alpha WITHOUT crash window: coef={a_without:+.5f}  p={p_without:.3f}{stars(p_without)}  (n={len(ex_crash)})")
    if p_without < 0.10 <= p_with:
        print("  --> Excluding the crash window RESTORES significance: the post-1994 null result is "
              "concentrated in this episode, not a broad decay.")
    elif p_without < p_with:
        print("  --> Excluding the crash window improves but does not restore significance: the crash "
              "episode is a contributing factor, not the whole story.")
    else:
        print("  --> Excluding the crash window does NOT meaningfully change the result: the post-1994 "
              "weakness is not concentrated in this specific episode.")


def check3_hedge_window_robustness(leg_returns: pd.Series, market: pd.Series, reb_dates: pd.DatetimeIndex, leg_name: str) -> None:
    print(f"\n{'=' * 90}\nCHECK 3 -- Hedge rolling-window robustness ({leg_name})\n{'=' * 90}")
    for window, min_hist in [(126, 63), (252, 126), (378, 189)]:
        hedged = build_hedged_return_series(leg_returns, market, reb_dates, window=window, min_history=min_hist)
        post = hedged[hedged.index >= PUBLICATION_CUTOFF].dropna()
        pre = hedged[hedged.index < PUBLICATION_CUTOFF].dropna()
        pre_alpha, pre_p = hac_alpha(pre, HAC_LAGS_DAILY)
        post_alpha, post_p = hac_alpha(post, HAC_LAGS_DAILY)
        print(f"  window={window:3d}d  pre-1994: ann_ret={annualized_return(pre):+7.2%} p={pre_p:.3f}{stars(pre_p):3s}   "
              f"post-1994: ann_ret={annualized_return(post):+7.2%} p={post_p:.3f}{stars(post_p)}")


def main() -> None:
    prices = load_us_kaggle_mirror()
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    market = market_proxy(prices)
    reb_dates = result.turnover_by_month.index

    for leg_name, leg_returns in [
        ("long leg", result.daily_returns_long),
        ("combined long-short", result.daily_returns_gross),
    ]:
        print(f"\n{'#' * 90}\n# {leg_name.upper()}\n{'#' * 90}")
        hedged = build_hedged_return_series(leg_returns, market, reb_dates, window=252, min_history=126)
        check1_subperiod_breakdown(hedged, reb_dates, leg_name)
        check2_crash_exclusion(hedged, leg_name)
        check3_hedge_window_robustness(leg_returns, market, reb_dates, leg_name)


if __name__ == "__main__":
    print("Deep-dive on Milestone 10's post-1994 null result: is it a broad decay, a concentrated")
    print("2009 momentum-crash episode, or an artifact of the hedge's rolling-window choice?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10\n")
    main()

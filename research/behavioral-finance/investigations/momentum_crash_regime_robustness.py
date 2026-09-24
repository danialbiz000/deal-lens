"""
Every crash-regime finding in this project since Milestone 5 rests on two
arbitrary-looking parameter choices baked into build_regime_dummies()
(investigations/momentum_crash_significance.py): a 21-trading-day realized-
volatility window and a 252-trading-day (~1 year) trailing-return lookback
for the "Bear" flag. Nothing in this project has ever asked whether the two
headline results built on top of those choices -- Milestone 16's "the crash
mechanism was dormant pre-2008, significant post-2008" and Milestone 18's
"no bear-market regime recurred after September 2009" -- are a property of
momentum's actual returns, or an artifact of those two specific numbers.

That question matters more than usual here because Milestone 18's finding
is, by construction, sensitive to exactly this: a SHORTER trailing-return
lookback would register the sharp-but-short 2011 and 2015-16 drawdowns as
bear markets that the 252-day window missed entirely, which would directly
change whether "no bear regime since 2009" still holds. If it doesn't hold
under a shorter, still-reasonable lookback, Milestone 18's core claim is
fragile, not robust. If it does hold across a range of choices, the
opposite: the finding is real, not a byproduct of one specific window.

This milestone reimplements build_regime_dummies with configurable windows
(the original function is untouched -- every earlier milestone that calls
it keeps using exactly the parameters it always has) and re-runs both
checks across a grid:
  - Volatility window: 10, 21 (this project's default since Milestone 5),
    42, and 63 trading days (roughly 2 weeks to 3 months).
  - Bear-market lookback: 126 (~6 months), 189 (~9 months), 252 (this
    project's default), and 378 (~18 months) trading days.
16 combinations total, each checked two ways:
  1. Does a Bear regime ever fire after 2010-01-01 (the exact question
     Milestone 18 answered "no" to at the default 252-day window)?
  2. Does the Milestone 16 pattern -- interaction dormant pre-2008-09,
     significant post-2008-09 -- still show up?

Run: python investigations/momentum_crash_regime_robustness.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from backtest.engine import run_decile_backtest
from data.loaders import load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_significance import hac_regression, report_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

BREAK_DATE = pd.Timestamp("2008-09-01")   # same literature-motivated date as Milestones 14/16/17/18
POST_2010 = pd.Timestamp("2010-01-01")    # same cutoff as Milestone 18's persistence check

VOL_WINDOWS = [10, 21, 42, 63]
BEAR_WINDOWS = [126, 189, 252, 378]
MIN_HISTORY = 252  # unchanged from the original -- needs a full year before classifying anything


def build_regime_dummies_param(prices: pd.DataFrame, vol_window: int, bear_window: int) -> pd.DataFrame:
    """Same construction as momentum_crash_significance.build_regime_dummies
    (expanding-quantile high-vol tercile, trailing-return bear flag, both
    lagged one day) but with the volatility and bear-lookback windows as
    arguments instead of hardcoded constants, so this script can sweep them."""
    market_ret = prices.pct_change().mean(axis=1)
    realized_vol = market_ret.rolling(vol_window).std() * np.sqrt(252)
    expanding_cutoff = realized_vol.expanding(min_periods=MIN_HISTORY).quantile(2.0 / 3.0)
    high_vol = (realized_vol > expanding_cutoff).astype(float)

    market_index = (1.0 + market_ret.fillna(0.0)).cumprod()
    trailing_return = market_index / market_index.shift(bear_window) - 1.0
    bear = (trailing_return < 0).astype(float)

    regimes = pd.DataFrame({"high_vol": high_vol, "bear": bear})
    return regimes.shift(1)


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


def run_interaction(era: pd.Series, era_regimes: pd.DataFrame) -> tuple[float, float]:
    interaction = era_regimes["high_vol"] * era_regimes["bear"]
    X = pd.DataFrame({
        "high_vol": era_regimes["high_vol"],
        "bear": era_regimes["bear"],
        "high_vol_x_bear": interaction,
    })
    aligned = pd.concat([era.rename("y"), X], axis=1).dropna()
    if aligned["high_vol_x_bear"].nunique() < 2 or len(aligned) < 60:
        return float("nan"), float("nan")
    fit = hac_regression(aligned["y"], aligned[X.columns], lags=21)
    return float(fit.params["high_vol_x_bear"]), float(fit.pvalues["high_vol_x_bear"])


def main() -> None:
    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)

    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index

    hedged_long, _beta = build_hedged_return_series(result.daily_returns_long, market, reb_dates)
    pre = hedged_long[hedged_long.index < BREAK_DATE]
    post = hedged_long[hedged_long.index >= BREAK_DATE]

    print("Long leg only. Newey-West (HAC) standard errors, 21-day lag. *** p<0.01  ** p<0.05  * p<0.10\n")
    print(f"{'vol_win':>8s} {'bear_win':>9s} | {'bear fires post-2010?':>23s} | "
          f"{'pre-2008 interaction':>24s} | {'post-2008 interaction':>24s}")
    print("-" * 100)

    default_bear_fires = None
    default_pattern = None
    fires_count = 0

    for bear_window in BEAR_WINDOWS:
        for vol_window in VOL_WINDOWS:
            regimes = build_regime_dummies_param(prices, vol_window, bear_window)

            post2010_bear = regimes.loc[regimes.index >= POST_2010, "bear"]
            bear_fires = bool((post2010_bear == 1.0).any())
            bear_days = int((post2010_bear == 1.0).sum())
            fires_count += int(bear_fires)

            pre_regimes = regimes.reindex(pre.index)
            post_regimes = regimes.reindex(post.index)
            pre_coef, pre_p = run_interaction(pre, pre_regimes)
            post_coef, post_p = run_interaction(post, post_regimes)

            is_default = (vol_window == 21 and bear_window == 252)
            pattern_matches = (pre_p != pre_p or pre_p >= 0.10) and (post_p == post_p and post_p < 0.10)
            marker = "  <- Milestones 16/18 default" if is_default else ""
            if is_default:
                default_bear_fires = bear_fires
                default_pattern = pattern_matches

            print(f"{vol_window:8d} {bear_window:9d} | "
                  f"{('YES (' + str(bear_days) + ' days)') if bear_fires else 'no':>23s} | "
                  f"{pre_coef:+.5f} p={pre_p:.3f}{stars(pre_p):3s}  | "
                  f"{post_coef:+.5f} p={post_p:.3f}{stars(post_p):3s}{marker}")

    n_combos = len(VOL_WINDOWS) * len(BEAR_WINDOWS)
    print(f"\nBear regime fires post-2010 in {fires_count}/{n_combos} parameter combinations.")
    print(f"Default (vol=21, bear=252): bear fires post-2010 = {default_bear_fires}, "
          f"Milestone-16 pattern (dormant pre / significant post) holds = {default_pattern}")


if __name__ == "__main__":
    main()

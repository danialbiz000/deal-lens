"""
Milestone 53 (line AE) closes the last conspicuous gap in this project's
crash-risk toolkit: the Bear+HighVol regime-interaction test (Milestones
16-18, 20, 46-48) and the VaR/CVaR fat-tail profile (Milestone 43) have
only ever been applied to CROSS-SECTIONAL stock-selection strategies
(momentum, low-volatility, MAX) -- never to the turn-of-month effect,
this project's one signal from a genuinely different family: a
long-only, calendar-timing, time-series strategy (Milestone 38) that is
now half of the project's own current recommendation (Milestones 45,
49, 50, 51-53).

This matters for a structural reason: momentum's short leg carries
crash risk because it is short something that snaps back violently in
a rebound (Daniel & Moskowitz 2016) -- a mechanism specific to a
long-short book. Turn-of-month has no short leg at all; it is long the
market (or flat) a handful of days a month. Whether it carries ANY
comparable crash sensitivity, and whether its own realized tail risk on
the days it IS invested resembles the fat-tail understatement Q1's
simulation warned about, has never been checked -- an open question
this project's own toolkit exists to answer, simply never pointed here.

Part 1 tests whether the turn-of-month ADD-ON itself (not a hedged
long-short return, since there is no short leg to hedge) shrinks or
reverses specifically during Bear+HighVol regimes -- a three-way HAC
regression with a turn_of_month x high_vol x bear interaction term, the
calendar-strategy analogue of momentum's own crash-interaction test.
Part 2 profiles empirical vs. Gaussian VaR/CVaR, with bootstrap 90% CIs,
on the market's ACTUAL returns during turn-of-month days -- the days
this strategy is actually invested -- rather than on a zero-heavy
"invested-or-cash" return series where non-trading days would dilute
the tail profile of the days that matter.

Reuses build_regime_dummies, hac_regression from
momentum_crash_significance.py; turn_of_month_flags, HAC_LAGS_DAILY from
turn_of_month_effect.py; market_proxy from short_leg_beta.py;
empirical_var_cvar, gaussian_var_cvar, bootstrap_ci from
momentum_var_cvar_profile.py -- all unchanged.

Run: python investigations/turn_of_month_crash_tail_profile.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd
from scipy import stats

from data.loaders import load_nse_github_mirror, load_us_kaggle_mirror
from investigations.momentum_crash_significance import build_regime_dummies, hac_regression
from investigations.momentum_var_cvar_profile import (
    N_BOOTSTRAP,
    SEED,
    bootstrap_ci,
    empirical_var_cvar,
    gaussian_var_cvar,
)
from investigations.short_leg_beta import market_proxy
from investigations.turn_of_month_effect import HAC_LAGS_DAILY, turn_of_month_flags

CONFIDENCE_LEVELS = [0.95, 0.99, 0.999]


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


def part1_crash_interaction(label: str, prices: pd.DataFrame) -> None:
    market = market_proxy(prices).dropna()
    regimes = build_regime_dummies(prices).reindex(market.index)
    tom = turn_of_month_flags(market.index).astype(float)
    bear_highvol = (regimes["high_vol"] * regimes["bear"]).fillna(0.0)

    X = pd.DataFrame({
        "turn_of_month": tom,
        "bear_highvol": bear_highvol,
        "tom_x_bear_highvol": tom * bear_highvol,
    }, index=market.index)
    aligned = pd.concat([market.rename("y"), X], axis=1).dropna()
    fit = hac_regression(aligned["y"], aligned[X.columns], lags=HAC_LAGS_DAILY)

    tom_coef = float(fit.params["turn_of_month"])
    tom_p = float(fit.pvalues["turn_of_month"])
    inter_coef = float(fit.params["tom_x_bear_highvol"])
    inter_p = float(fit.pvalues["tom_x_bear_highvol"])
    n_bear_highvol_tom_days = int((aligned["turn_of_month"] * aligned["bear_highvol"]).sum())

    print(f"\n{'=' * 100}\n{label} -- does the turn-of-month add-on itself shrink or reverse "
          f"during Bear+HighVol regimes?\n{'=' * 100}")
    print(f"  Baseline turn-of-month add-on: {tom_coef:+.4%}/day  p={tom_p:.4f}{stars(tom_p)}")
    print(f"  Turn-of-month x Bear+HighVol interaction: {inter_coef:+.4%}/day  "
          f"p={inter_p:.4f}{stars(inter_p)}  (n={n_bear_highvol_tom_days} turn-of-month days "
          f"that were also Bear+HighVol)")
    print(f"  Implied turn-of-month add-on DURING a crash regime: {tom_coef + inter_coef:+.4%}/day")


def part2_tail_profile(label: str, prices: pd.DataFrame, rng: np.random.Generator) -> None:
    market = market_proxy(prices).dropna()
    tom = turn_of_month_flags(market.index)
    tom_returns = market[tom].values
    rest_returns = market[~tom].values
    n = len(tom_returns)
    mean, std = tom_returns.mean(), tom_returns.std()
    skew, kurt = stats.skew(tom_returns), stats.kurtosis(tom_returns)

    print(f"\n{'=' * 100}\n{label} -- tail-risk profile on the days this strategy is actually "
          f"invested (n={n} turn-of-month days, mean={mean:+.4%}/day, std={std:.4%}/day, "
          f"skew={skew:+.2f}, excess kurtosis={kurt:+.2f})\n{'=' * 100}")
    print(f"  {'Confidence':<12}{'Gaussian VaR':<14}{'Empirical VaR':<16}{'VaR ratio':<12}"
          f"{'Gaussian CVaR':<15}{'Empirical CVaR':<16}{'CVaR ratio':<11}")
    for conf in CONFIDENCE_LEVELS:
        g_var, g_cvar = gaussian_var_cvar(mean, std, conf)
        e_var, e_cvar = empirical_var_cvar(tom_returns, conf)
        var_ratio = e_var / g_var if g_var != 0 else float("nan")
        cvar_ratio = e_cvar / g_cvar if g_cvar != 0 else float("nan")
        print(f"  {conf:<12.1%}{g_var:<14.3%}{e_var:<16.3%}{var_ratio:<12.2f}"
              f"{g_cvar:<15.3%}{e_cvar:<16.3%}{cvar_ratio:<11.2f}")

    print(f"\n  90% bootstrap CI (resampling turn-of-month days, {N_BOOTSTRAP:,} draws):")
    for conf in CONFIDENCE_LEVELS:
        n_tail_obs = int(np.sum(tom_returns <= np.quantile(tom_returns, 1.0 - conf)))
        var_lo, var_hi, cvar_lo, cvar_hi = bootstrap_ci(tom_returns, conf, rng)
        print(f"    {conf:.1%}: VaR [{var_lo:.3%}, {var_hi:.3%}]  "
              f"CVaR [{cvar_lo:.3%}, {cvar_hi:.3%}]  (~{n_tail_obs} raw tail observations)")

    rest_mean, rest_std = rest_returns.mean(), rest_returns.std()
    print(f"\n  For comparison, rest-of-month days (n={len(rest_returns)}): "
          f"mean={rest_mean:+.4%}/day, std={rest_std:.4%}/day -- turn-of-month days carry "
          f"{'higher' if std > rest_std else 'lower'} volatility per day "
          f"({std / rest_std:.2f}x rest-of-month's).")


def main() -> None:
    print("This project's crash-risk toolkit (Bear+HighVol regime interaction, Milestones 16-18,")
    print("20, 46-48; VaR/CVaR fat-tail profiling, Milestone 43) has only ever been applied to")
    print("cross-sectional long-short strategies. Turn-of-month -- a long-only calendar-timing")
    print("strategy with no short leg, now half of this project's own current recommendation --")
    print("has never been checked. This milestone points both tools at it directly, on both")
    print("markets where it is a genuinely live, walk-forward-validated finding (Milestone 38, 52).\n")

    rng = np.random.default_rng(SEED)
    for label, loader in [("NSE (India)", load_nse_github_mirror), ("US mirror", load_us_kaggle_mirror)]:
        prices = loader()
        part1_crash_interaction(label, prices)
        part2_tail_profile(label, prices, rng)


if __name__ == "__main__":
    main()

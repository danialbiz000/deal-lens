"""
Milestone 50 (line AC) closes the loop this project's own capstone
self-scrutiny phase opened. Milestone 47 found that momentum's own
post-2008-09 Bear+HighVol interaction coefficient -- the single number
Milestone 33's crash-duration stress simulation (and Milestone 42's
crash-cost extension of it) treats as a FIXED, known input -- does not
survive a fuller multiple-testing correction (raw p=0.0081, BH-adjusted
p=0.1384-0.1547). Milestone 33 never accounted for that: its stress
simulation bootstraps day-to-day RESIDUAL noise around the fitted daily
drift (const+high_vol+bear+interaction), but treats the fitted
coefficients themselves as certain, point-estimate inputs, with no
allowance for how uncertain the interaction term specifically is.

This milestone re-runs Milestone 33's exact duration-multiplier stress
test with one addition: a second uncertainty channel, drawing the
regression's own coefficients from their fitted HAC sampling distribution
(mean = the fitted point estimates, covariance = the fitted HAC covariance
matrix) once per simulated "world," on top of the residual bootstrap
already inside each world. This does NOT assume a bigger or smaller
effect than the data supports -- it takes the exact same fitted model
Milestone 33 used and asks how much the reported loss range should widen
once the interaction coefficient's own estimation uncertainty (the
uncertainty Milestone 47 quantified as large enough to erase its
significance under correction) is actually propagated through, rather
than silently assumed away.

Reuses historical_worst_episode_length, fit_post_2008_regression, and
simulate_episode, plus the module-level HAC_LAGS_DAILY, POST_2008,
N_SIMS, SEED, DURATION_MULTIPLIERS constants, from
momentum_crash_severity_stress_test.py (Milestone 33) unchanged.

Run: python investigations/crash_stress_test_uncertainty_propagation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from data.loaders import load_us_kaggle_mirror
from investigations.momentum_crash_severity_stress_test import (
    DURATION_MULTIPLIERS,
    N_SIMS,
    POST_2008,
    SEED,
    fit_post_2008_regression,
    historical_worst_episode_length,
    simulate_episode,
)
from investigations.momentum_crash_significance import build_regime_dummies
from investigations.short_leg_beta import market_proxy

COEF_NAMES = ["const", "high_vol", "bear", "high_vol_x_bear"]


def simulate_episode_with_parameter_uncertainty(
    rng: np.random.Generator, mean_params: np.ndarray, cov_params: np.ndarray,
    residuals: np.ndarray, n_days: int, n_sims: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Like Milestone 33's simulate_episode, but draws a fresh set of
    regression coefficients (hence a fresh daily_drift) per simulated
    'world' from the fitted HAC sampling distribution, instead of holding
    the point-estimate daily_drift fixed across every simulated path."""
    coef_draws = rng.multivariate_normal(mean_params, cov_params, size=n_sims)
    daily_drift_draws = coef_draws.sum(axis=1)  # const + high_vol + bear + interaction, per world
    resid_draws = rng.choice(residuals, size=(n_sims, n_days), replace=True)
    daily_returns = daily_drift_draws[:, None] + resid_draws
    cumulative = np.prod(1.0 + daily_returns, axis=1) - 1.0
    return cumulative, daily_drift_draws


def main() -> None:
    print("Milestone 47 found the interaction coefficient Milestone 33's stress simulation")
    print("treats as a fixed input does not survive a fuller multiple-testing correction")
    print("(BH-adjusted p=0.1384-0.1547). This milestone re-runs Milestone 33's exact stress")
    print("test with that coefficient's own estimation uncertainty propagated through, on top")
    print("of the residual-noise bootstrap Milestone 33 already ran.\n")

    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)
    regimes = build_regime_dummies(prices)

    worst_len = historical_worst_episode_length(regimes, POST_2008)
    fit = fit_post_2008_regression(prices, market, regimes)
    mean_params = fit.params[COEF_NAMES].values
    cov_params = fit.cov_params().loc[COEF_NAMES, COEF_NAMES].values
    daily_drift_point = mean_params.sum()
    daily_drift_se = float(np.sqrt(np.ones(4) @ cov_params @ np.ones(4)))
    residuals = fit.resid.values

    print(f"Worst historical Bear+HighVol episode, post-2008 sample: {worst_len} trading days.")
    print(f"Fitted daily drift in regime (point estimate): {daily_drift_point:+.4%}")
    print(f"HAC standard error of that combined estimate: {daily_drift_se:.4%}")
    print(f"Approximate 90% CI on the daily drift itself: "
          f"({daily_drift_point - 1.645 * daily_drift_se:+.4%}, "
          f"{daily_drift_point + 1.645 * daily_drift_se:+.4%}) -- this is the same estimation "
          f"uncertainty behind Milestone 47's finding that the interaction term does not "
          f"survive correction, now expressed on the scale Milestone 33 actually reports in.\n")

    rng_point = np.random.default_rng(SEED)
    rng_prop = np.random.default_rng(SEED + 1)

    print(f"{'=' * 100}\n"
          f"{'Duration':<22}{'Point-estimate-only (Milestone 33)':<42}"
          f"{'Coefficient uncertainty propagated':<40}\n{'=' * 100}")
    for mult in DURATION_MULTIPLIERS:
        n_days = worst_len * mult
        cum_point = simulate_episode(rng_point, daily_drift_point, residuals, n_days, N_SIMS)
        cum_prop, drift_draws = simulate_episode_with_parameter_uncertainty(
            rng_prop, mean_params, cov_params, residuals, n_days, N_SIMS,
        )
        label = f"{mult}x worst ({n_days}d)"
        print(f"{label:<22}"
              f"mean={cum_point.mean():+7.1%} 5-95pct=({np.percentile(cum_point, 5):+.1%}, "
              f"{np.percentile(cum_point, 95):+.1%}) worst1%={np.percentile(cum_point, 1):+.1%}   "
              f"mean={cum_prop.mean():+7.1%} 5-95pct=({np.percentile(cum_prop, 5):+.1%}, "
              f"{np.percentile(cum_prop, 95):+.1%}) worst1%={np.percentile(cum_prop, 1):+.1%}")

    print(f"\n{'=' * 100}\nWidening of the 90% interval (95th pct minus 5th pct), point-estimate "
          f"vs. propagated\n{'=' * 100}")
    rng_point2 = np.random.default_rng(SEED)
    rng_prop2 = np.random.default_rng(SEED + 1)
    for mult in DURATION_MULTIPLIERS:
        n_days = worst_len * mult
        cum_point = simulate_episode(rng_point2, daily_drift_point, residuals, n_days, N_SIMS)
        cum_prop, _ = simulate_episode_with_parameter_uncertainty(
            rng_prop2, mean_params, cov_params, residuals, n_days, N_SIMS,
        )
        width_point = np.percentile(cum_point, 95) - np.percentile(cum_point, 5)
        width_prop = np.percentile(cum_prop, 95) - np.percentile(cum_prop, 5)
        print(f"  {mult}x worst ({n_days}d): point-estimate width={width_point:.1%}  "
              f"propagated width={width_prop:.1%}  "
              f"widening factor={width_prop / width_point:.2f}x")


if __name__ == "__main__":
    main()

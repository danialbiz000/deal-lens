"""
Milestone 51 (line AD) extends the uncertainty-propagation discipline
Milestone 50 built -- draw a fitted estimate's own parameters from their
sampling distribution rather than treating them as certain -- to the two
other headline point estimates in this project's history built the same
way: a number computed from a fitted or resampled quantity, reported
without ever asking how much THAT quantity's own estimation uncertainty
should widen it.

Part 1 revisits Milestone 43's VaR/CVaR profile. Milestone 43 already
bootstrapped 90% confidence intervals on the empirical VaR and CVaR
separately -- but the project's actual headline number, "the empirical
99.9% CVaR understates risk by 1.71x relative to Gaussian," is a RATIO of
two quantities estimated from the same sample, and no interval was ever
put on the ratio itself. A ratio's own sampling distribution is not
implied by its numerator's and denominator's separate intervals (the two
are correlated, drawn from the same days) -- this section computes it
directly, resampling days once per draw and computing both the empirical
and Gaussian CVaR from that SAME draw, then taking their ratio.

Part 2 revisits Milestone 42's crash-cost interaction sweep. Milestone 42
reported that raising trading costs specifically during Bear+HighVol
rebalances (1.0x-5.0x) worsens the estimated 196-day crash-episode loss
only modestly (-25.6% to -26.7%), calling costs a "second-order" effect
next to the structural regime drift -- but, like Milestone 33's original
stress test before Milestone 50, that conclusion was drawn from point
estimates of a coefficient refit separately at each cost multiplier,
never asking whether the DIFFERENCE between multipliers survives each
fit's own estimation uncertainty. This section reruns Milestone 42's
sweep with Milestone 50's own parameter-uncertainty-propagated simulation
at every multiplier, not just the point-estimate one.

Reuses empirical_var_cvar, gaussian_var_cvar, build_hedged_series, and
RELIABLE_DATA_START from momentum_var_cvar_profile.py (Milestone 43);
build_crash_cost_series and CRASH_COST_MULTIPLIERS from
crash_cost_interaction.py (Milestone 42); historical_worst_episode_length
and simulate_episode from momentum_crash_severity_stress_test.py
(Milestone 33); and simulate_episode_with_parameter_uncertainty, COEF_NAMES
from crash_stress_test_uncertainty_propagation.py (Milestone 50) -- all
unchanged.

Run: python investigations/uncertainty_propagation_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from backtest.engine import run_decile_backtest
from data.loaders import load_asx_github_mirror, load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.crash_cost_interaction import CRASH_COST_MULTIPLIERS, build_crash_cost_series
from investigations.crash_stress_test_uncertainty_propagation import (
    COEF_NAMES,
    simulate_episode_with_parameter_uncertainty,
)
from investigations.momentum_crash_severity_stress_test import (
    historical_worst_episode_length,
    simulate_episode,
)
from investigations.momentum_crash_significance import build_regime_dummies, hac_regression
from investigations.momentum_var_cvar_profile import (
    RELIABLE_DATA_START,
    build_hedged_series,
    empirical_var_cvar,
    gaussian_var_cvar,
)
from investigations.short_leg_beta import market_proxy
from investigations.transaction_cost_realism import apply_cost
from signals.momentum import momentum_12_1

N_BOOTSTRAP = 5_000
SEED_CVAR = 23
SEED_COST = 29
N_SIMS = 20_000
POST_2008 = "2008-09-01"
HAC_LAGS_DAILY = 21
TARGET_CONFIDENCE = 0.999


def cvar_ratio_bootstrap_ci(returns: np.ndarray, confidence: float, rng: np.random.Generator,
                             n_boot: int = N_BOOTSTRAP) -> tuple[float, np.ndarray]:
    """Resamples days once per draw and computes empirical CVaR / Gaussian
    CVaR from that SAME draw, so the ratio's own sampling distribution
    (not just each side's separately) is captured."""
    n = len(returns)
    ratios = np.empty(n_boot)
    for i in range(n_boot):
        sample = rng.choice(returns, size=n, replace=True)
        mean, std = sample.mean(), sample.std()
        _, e_cvar = empirical_var_cvar(sample, confidence)
        _, g_cvar = gaussian_var_cvar(mean, std, confidence)
        ratios[i] = e_cvar / g_cvar if g_cvar != 0 else np.nan
    point_mean, point_std = returns.mean(), returns.std()
    _, e_cvar_point = empirical_var_cvar(returns, confidence)
    _, g_cvar_point = gaussian_var_cvar(point_mean, point_std, confidence)
    point_ratio = e_cvar_point / g_cvar_point
    return point_ratio, ratios


def part1_cvar_ratio_uncertainty() -> None:
    print(f"{'=' * 100}\nPart 1: does Milestone 43's headline CVaR-understatement RATIO (not just "
          f"each side separately) hold up to resampling?\n{'=' * 100}\n")
    rng = np.random.default_rng(SEED_CVAR)

    us_prices = load_us_kaggle_mirror()
    us_hedged = build_hedged_series(us_prices)
    us_reliable = us_hedged.loc[RELIABLE_DATA_START:].dropna().values
    point_ratio, ratios = cvar_ratio_bootstrap_ci(us_reliable, TARGET_CONFIDENCE, rng)
    lo, hi = np.nanpercentile(ratios, 5), np.nanpercentile(ratios, 95)
    print(f"US mirror, from {RELIABLE_DATA_START} (Milestone 43's own headline series, "
          f"n={len(us_reliable)}):")
    print(f"  99.9% CVaR ratio (empirical/Gaussian): point estimate={point_ratio:.2f}x  "
          f"90% bootstrap CI=({lo:.2f}x, {hi:.2f}x)")
    print(f"  (Milestone 43 reported 1.71x as a single number; the honest range around it is "
          f"{hi - lo:.2f}x wide at 90% confidence, from only {int((us_reliable <= np.quantile(us_reliable, 1 - TARGET_CONFIDENCE)).sum())} "
          f"raw tail observations beyond the 99.9% threshold.)\n")

    asx_hedged = build_hedged_series(load_asx_github_mirror())
    asx_returns = asx_hedged.dropna().values
    point_ratio_asx, ratios_asx = cvar_ratio_bootstrap_ci(asx_returns, TARGET_CONFIDENCE, rng)
    lo_asx, hi_asx = np.nanpercentile(ratios_asx, 5), np.nanpercentile(ratios_asx, 95)
    n_tail_asx = int((asx_returns <= np.quantile(asx_returns, 1 - TARGET_CONFIDENCE)).sum())
    print(f"ASX mirror, full sample (n={len(asx_returns)}):")
    print(f"  99.9% CVaR ratio (empirical/Gaussian): point estimate={point_ratio_asx:.2f}x  "
          f"90% bootstrap CI=({lo_asx:.2f}x, {hi_asx:.2f}x)")
    print(f"  ({n_tail_asx} raw tail observations beyond the 99.9% threshold -- this CI should be "
          f"read as evidence the point estimate is essentially unusable at this confidence level "
          f"on this sample size, not as a precise range.)\n")


def part2_crash_cost_uncertainty() -> None:
    print(f"{'=' * 100}\nPart 2: does Milestone 42's cost-multiplier sweep survive the same "
          f"parameter-uncertainty propagation Milestone 50 applied to Milestone 33?\n{'=' * 100}\n")

    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)
    regimes = build_regime_dummies(prices)
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    turnover = result.turnover_by_month
    reb_dates = turnover.index
    regime_at_reb = regimes.reindex(reb_dates)
    worst_len = historical_worst_episode_length(regimes, POST_2008)

    rows = []
    for mult in CRASH_COST_MULTIPLIERS:
        cost_series, _flag = build_crash_cost_series(turnover, regime_at_reb, mult)
        net_long = apply_cost(result.daily_returns_long, turnover, cost_series)
        hedged, _beta = build_hedged_return_series(net_long, market, reb_dates)
        post = hedged[hedged.index >= POST_2008].dropna()
        post_regimes = regimes.reindex(post.index)
        interaction = post_regimes["high_vol"] * post_regimes["bear"]
        X = pd.DataFrame({
            "high_vol": post_regimes["high_vol"], "bear": post_regimes["bear"],
            "high_vol_x_bear": interaction,
        })
        fit = hac_regression(post, X, lags=HAC_LAGS_DAILY)
        mean_params = fit.params[COEF_NAMES].values
        cov_params = fit.cov_params().loc[COEF_NAMES, COEF_NAMES].values
        residuals = fit.resid.values
        daily_drift_point = mean_params.sum()

        rng_point = np.random.default_rng(SEED_COST)
        rng_prop = np.random.default_rng(SEED_COST + 1)
        cum_point = simulate_episode(rng_point, daily_drift_point, residuals, worst_len, N_SIMS)
        cum_prop, _drift_draws = simulate_episode_with_parameter_uncertainty(
            rng_prop, mean_params, cov_params, residuals, worst_len, N_SIMS,
        )
        rows.append({
            "mult": mult, "mean_point": cum_point.mean(), "mean_prop": cum_prop.mean(),
            "lo_point": np.percentile(cum_point, 5), "hi_point": np.percentile(cum_point, 95),
            "lo_prop": np.percentile(cum_prop, 5), "hi_prop": np.percentile(cum_prop, 95),
        })

    print(f"{'Multiplier':<12}{'Point mean':<14}{'Point 90% CI':<26}{'Propagated mean':<18}"
          f"{'Propagated 90% CI':<26}")
    for r in rows:
        point_ci = f"({r['lo_point']:+.1%}, {r['hi_point']:+.1%})"
        prop_ci = f"({r['lo_prop']:+.1%}, {r['hi_prop']:+.1%})"
        print(f"{r['mult']:<12.1f}{r['mean_point']:<+14.1%}{point_ci:<26}"
              f"{r['mean_prop']:<+18.1%}{prop_ci:<26}")

    baseline = rows[0]
    worst = rows[-1]
    point_gap = worst["mean_point"] - baseline["mean_point"]
    print(f"\nPoint-estimate gap between 1.0x and {worst['mult']:.1f}x cost multiplier: "
          f"{point_gap:+.2%} of episode return (Milestone 42's own reported effect).")
    overlap = not (worst["hi_prop"] < baseline["lo_prop"] or baseline["hi_prop"] < worst["lo_prop"])
    print(f"Do the two multipliers' propagated 90% intervals overlap once parameter uncertainty "
          f"is included? {'YES -- overlapping' if overlap else 'NO -- distinguishable'} "
          f"(baseline propagated: [{baseline['lo_prop']:+.1%}, {baseline['hi_prop']:+.1%}], "
          f"{worst['mult']:.1f}x propagated: [{worst['lo_prop']:+.1%}, {worst['hi_prop']:+.1%}]).")


def main() -> None:
    print("Milestone 50 propagated a fitted coefficient's own HAC estimation uncertainty through")
    print("Milestone 33's crash-duration stress test. This milestone applies the same discipline")
    print("to the two other point estimates in this project built the same way: a ratio computed")
    print("from a resampled quantity (Milestone 43's CVaR ratio) and a coefficient refit at each")
    print("point in a sweep (Milestone 42's crash-cost multipliers), neither of which had its own")
    print("estimation uncertainty carried through to the final reported number.\n")
    part1_cvar_ratio_uncertainty()
    part2_crash_cost_uncertainty()


if __name__ == "__main__":
    main()

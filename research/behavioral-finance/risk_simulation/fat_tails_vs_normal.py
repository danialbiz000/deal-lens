"""
Illustrates, via Monte Carlo, why a Gaussian, calm-regime-calibrated VaR model
understates tail risk once returns exhibit (a) fatter-than-normal marginal
tails and (b) a stress regime in which pairwise correlations jump toward 1 --
the mechanism most commonly cited for why LTCM's diversification/hedging
assumptions failed in autumn 1998 (see ../case_studies/ltcm_1998.md).

This is a stylized simulation, not a reconstruction of LTCM's actual book --
see ../README.md "Explicit limitations". It runs entirely offline (no market
data needed), so its printed output is a real, reproducible result of this
repo, unlike the signal backtest which needs live data this sandbox couldn't
reach.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

N_ASSETS = 6
N_DAYS = 500_000
STRESS_PROB = 0.01  # ~1 stress day in 100 -- roughly one bad episode a year
CALM_CORR = 0.25  # modest pairwise correlation most of the time
STRESS_CORR = 0.92  # correlations collapse toward 1 under flight-to-quality
CALM_DAILY_VOL = 0.010  # 1.0% daily vol per asset, calm regime
STRESS_VOL_MULT = 3.0  # vol roughly triples in the stress regime
T_DOF = 4  # Student-t degrees of freedom -> fat tails
LEVERAGE_WEIGHTS = np.array([2.0, -2.0, 1.5, -1.5, 1.0, -1.0])  # leveraged relative-value book
CONFIDENCE = 0.99
SEED = 7


def _corr_matrix(rho: float, n: int) -> np.ndarray:
    return np.eye(n) * (1 - rho) + np.full((n, n), rho)


def gaussian_var(weights: np.ndarray, corr: np.ndarray, vol: np.ndarray, confidence: float = CONFIDENCE) -> float:
    """Closed-form parametric (Gaussian) VaR for a linear portfolio, calibrated
    only on calm-regime correlation/vol -- i.e. what a risk model looks like if
    fit on a "normal" historical window, the way LTCM's and many banks' models
    were calibrated before autumn 1998."""
    cov = corr * np.outer(vol, vol)
    port_vol = np.sqrt(weights @ cov @ weights)
    z = stats.norm.ppf(confidence)
    return z * port_vol


def simulate_true_process(rng: np.random.Generator, n_days: int = N_DAYS) -> np.ndarray:
    """Simulate portfolio daily P&L under the *true* mixture process: calm
    regime most days (moderate correlation, moderate vol), stress regime a
    small fraction of days (correlation -> STRESS_CORR, vol x STRESS_VOL_MULT),
    with Student-t marginals in both regimes for realistic fat tails."""
    n = N_ASSETS
    calm_L = np.linalg.cholesky(_corr_matrix(CALM_CORR, n))
    stress_L = np.linalg.cholesky(_corr_matrix(STRESS_CORR, n))

    is_stress = rng.random(n_days) < STRESS_PROB

    t_shocks = stats.t.rvs(df=T_DOF, size=(n_days, n), random_state=rng)
    # rescale Student-t draws to unit variance so CALM_DAILY_VOL / STRESS_VOL_MULT
    # are the actual marginal vols applied, not inflated by the t distribution's
    # own variance (Var[t_v] = v/(v-2) for v>2)
    t_shocks /= np.sqrt(T_DOF / (T_DOF - 2))

    calm_returns = t_shocks @ calm_L.T * CALM_DAILY_VOL
    stress_returns = t_shocks @ stress_L.T * (CALM_DAILY_VOL * STRESS_VOL_MULT)

    daily_returns = np.where(is_stress[:, None], stress_returns, calm_returns)
    return daily_returns @ LEVERAGE_WEIGHTS


def main() -> None:
    rng = np.random.default_rng(SEED)

    calm_corr = _corr_matrix(CALM_CORR, N_ASSETS)
    calm_vol = np.full(N_ASSETS, CALM_DAILY_VOL)

    true_pnl = simulate_true_process(rng)
    worst_day = -true_pnl.min()

    print(f"=== True process: Student-t (df={T_DOF}) fat tails + regime-switching correlation ===")
    print(f"  simulated days: {N_DAYS:,}  (stress regime ~{STRESS_PROB:.1%} of days)")
    print(f"  worst single day in {N_DAYS:,}-day simulation: {worst_day:.4%} of book")
    print()

    # Report at two depths into the tail: 99% is the textbook VaR level (and
    # already sits right at the boundary of the stress regime here); 99.9%
    # is deep enough into the tail that it is dominated by stress-regime days
    # -- which is the more honest illustration of what "fat tails + regime
    # switching" costs a model calibrated only on calm-regime history.
    for confidence in (0.99, 0.999):
        model_var = gaussian_var(LEVERAGE_WEIGHTS, calm_corr, calm_vol, confidence)
        empirical_var = -np.quantile(true_pnl, 1 - confidence)
        tail_mask = true_pnl <= -empirical_var
        cvar = -true_pnl[tail_mask].mean() if tail_mask.any() else float("nan")

        print(f"=== {confidence:.1%} tail ===")
        print(f"  Gaussian, calm-regime-calibrated VaR: {model_var:.4%} of book")
        print(f"  True (empirical) VaR:                 {empirical_var:.4%} of book")
        print(f"  True expected shortfall / CVaR:        {cvar:.4%} of book")
        print(f"  --> Gaussian model UNDERESTIMATES VaR by {empirical_var / model_var:.2f}x, "
              f"CVaR by {cvar / model_var:.2f}x")
        print()


if __name__ == "__main__":
    main()

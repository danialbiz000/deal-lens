"""
Milestone 33 (line L) answers, as directly as the data allows, the specific
open question this project's own Conclusions have named since Milestone 21
and never resolved: "whether the crash mechanism would reactivate in a
genuinely severe future crisis, as opposed to the milder episodes this
sample happens to contain, is a question no amount of further re-testing
of THIS HISTORY can answer." That's true of re-testing -- but this
project's own Q1 methodology (risk_simulation/fat_tails_vs_normal.py) shows
the right response to "the history doesn't contain a severe-enough
episode" is not to give up, but to build a scenario simulation grounded in
what the data DOES support.

The one thing 47 years of daily data does pin down with real statistical
confidence (Milestone 17, HAC p=0.0081) is the DAILY magnitude of the
momentum-crash effect once it's active: on a day where the market is both
in a bear regime and a high-volatility regime, momentum's long leg has
historically lost an extra ~0.15%/day (net of its normal drift) on top of
residual daily noise with ~0.67% standard deviation. What the sample
cannot pin down is how LONG a Bear+HighVol regime can persist -- the
worst episode in this project's entire post-2008 sample lasted 196 trading
days (2008-09-03 to 2009-07-29, i.e. the 2008-09 crisis itself). A
genuinely more severe future crisis is, almost by definition, one where
that regime persists longer than anything in this sample -- 1930s-style
bear markets ran for 2-3+ years, far outside this project's post-1970
sample's experience.

This milestone does NOT assume a bigger daily effect than the data
supports (that would be an unfounded extrapolation) -- it takes the
already-estimated daily drift and residual distribution as fixed and asks
a duration question instead: if a future Bear+HighVol regime persisted
2x, 3x, or 4x longer than the worst episode this sample ever produced,
what would the resulting momentum long-leg drawdown distribution look
like? Daily residuals are bootstrap-resampled from the actual post-2008
regression residuals (not assumed Gaussian), the same "let the data speak"
preference as everywhere else in this project.

Reuses build_regime_dummies, hac_regression, run_decile_backtest,
build_hedged_return_series unchanged.

Run: python investigations/momentum_crash_severity_stress_test.py
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
from investigations.momentum_crash_significance import build_regime_dummies, hac_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

HAC_LAGS_DAILY = 21
POST_2008 = "2008-09-01"
N_SIMS = 20_000
SEED = 11
DURATION_MULTIPLIERS = [1, 2, 3, 4]


def historical_worst_episode_length(regimes: pd.DataFrame, start: str) -> int:
    post = regimes[regimes.index >= start]
    interaction = (post["high_vol"] * post["bear"]).fillna(0)
    max_run, cur = 0, 0
    for v in interaction:
        cur = cur + 1 if v == 1 else 0
        max_run = max(max_run, cur)
    return max_run


def fit_post_2008_regression(prices: pd.DataFrame, market: pd.Series, regimes: pd.DataFrame):
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    hedged, _beta = build_hedged_return_series(result.daily_returns_long, market, reb_dates)
    post = hedged[hedged.index >= POST_2008].dropna()
    post_regimes = regimes.reindex(post.index)
    interaction = post_regimes["high_vol"] * post_regimes["bear"]
    X = pd.DataFrame({
        "high_vol": post_regimes["high_vol"], "bear": post_regimes["bear"],
        "high_vol_x_bear": interaction,
    })
    fit = hac_regression(post, X, lags=HAC_LAGS_DAILY)
    return fit


def simulate_episode(rng: np.random.Generator, daily_drift: float, residuals: np.ndarray,
                      n_days: int, n_sims: int) -> np.ndarray:
    """Bootstrap n_sims independent paths of n_days, each day's return =
    daily_drift + a resampled-with-replacement historical residual. Returns
    the array of cumulative (compounded) returns, one per simulated path."""
    draws = rng.choice(residuals, size=(n_sims, n_days), replace=True)
    daily_returns = daily_drift + draws
    cumulative = np.prod(1.0 + daily_returns, axis=1) - 1.0
    return cumulative


def main() -> None:
    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)
    regimes = build_regime_dummies(prices)

    worst_len = historical_worst_episode_length(regimes, POST_2008)
    print(f"Worst historical Bear+HighVol episode, post-2008 sample: {worst_len} trading days "
          f"(the 2008-09 crisis itself).")

    fit = fit_post_2008_regression(prices, market, regimes)
    const, hv, bear, inter = (fit.params["const"], fit.params["high_vol"],
                               fit.params["bear"], fit.params["high_vol_x_bear"])
    daily_drift_in_regime = const + hv + bear + inter
    residuals = fit.resid.values
    print(f"\nFitted post-2008 regression (Milestone 17's own model):")
    print(f"  const={const:+.5f}  high_vol={hv:+.5f}  bear={bear:+.5f}  interaction={inter:+.5f}  "
          f"(interaction p={fit.pvalues['high_vol_x_bear']:.4f})")
    print(f"  Daily drift on a Bear+HighVol day = const+high_vol+bear+interaction = "
          f"{daily_drift_in_regime:+.4%}")
    print(f"  Residual pool: n={len(residuals)}, std={residuals.std():.4%} "
          f"(bootstrapped, not assumed Gaussian)")

    rng = np.random.default_rng(SEED)
    print(f"\n{'=' * 90}\nBootstrap stress simulation: {N_SIMS:,} paths per duration, "
          f"duration = N x the worst historical episode ({worst_len} days)\n{'=' * 90}")
    for mult in DURATION_MULTIPLIERS:
        n_days = worst_len * mult
        cum = simulate_episode(rng, daily_drift_in_regime, residuals, n_days, N_SIMS)
        print(f"\n  {mult}x historical worst ({n_days} trading days, ~{n_days / 21:.1f} months):")
        print(f"    mean cumulative long-leg return: {cum.mean():+.1%}")
        print(f"    median: {np.median(cum):+.1%}   "
              f"5th pct: {np.percentile(cum, 5):+.1%}   95th pct: {np.percentile(cum, 95):+.1%}")
        print(f"    worst 1% of simulated paths: {np.percentile(cum, 1):+.1%}")


if __name__ == "__main__":
    print("How much worse could momentum's crash-risk drawdown get if a future Bear+HighVol")
    print("regime persisted longer than anything in this project's own historical sample?")
    print("Daily effect size and residual distribution held fixed at their fitted, statistically")
    print("significant post-2008 estimates (Milestone 17) -- only the REGIME DURATION is varied.")
    main()

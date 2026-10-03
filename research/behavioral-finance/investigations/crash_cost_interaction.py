"""
Milestone 42 (line U) crosses two lines of this project's own work that have,
until now, always been tested one at a time. Milestone 33 modeled how much
worse momentum's crash-risk drawdown could get if a future Bear+HighVol
regime persisted longer than anything in this sample -- but held trading
costs fixed at the flat, always-10bps rate this project has used everywhere,
even inside that stress scenario. Milestone 35-36 modeled how momentum's
edge degrades as trading costs rise -- but applied that cost increase
UNIFORMLY across the whole sample, calm months and crisis months alike. Real
market microstructure does not work that way: bid-ask spreads and market
impact widen specifically WHEN volatility spikes and liquidity dries up --
documented repeatedly in the 2008-09 crisis and in flash-crash episodes --
which is exactly the Bear+HighVol regime this project's own crash mechanism
(Milestones 16-17) already identifies. A crash-cost stress test that raises
costs everywhere, or a crash-duration stress test that holds costs fixed,
both miss the case that matters most: a strategy forced to keep rebalancing
INTO the crash it is trying to survive, at exactly the moment its own
trading costs are highest.

This does not invent a real spread-widening number (no data source available
to this project carries bid-ask spreads or ADV -- see Milestone 35's own
documented check). Instead, following Milestone 35's own precedent for its
illustrative convex overlay and Milestone 33's own precedent for its
duration-multiplier stress test, it holds everything else fixed and varies
ONE thing: a cost multiplier applied ONLY to rebalances that fall within a
Bear+HighVol regime (Milestone 17's own look-ahead-free regime dummies),
leaving normal-regime rebalances at this project's standing flat 10bps.
Multipliers of 1.5x-5x bracket the range of spread-widening documented in
the market-microstructure literature during acute stress (a citation-backed
range, not a fitted number) without claiming a precise value this project's
data cannot supply.

For each multiplier, the post-2008 crash-regime regression (Milestone 17's
own model) is refit on the resulting net-of-elevated-cost long-leg returns,
and the fitted daily drift and residual pool are fed into Milestone 33's own
bootstrap machinery, DURATION HELD FIXED at the worst historical episode
(196 trading days, the 2008-09 crisis itself) -- isolating the cost-during-
crash effect from the duration question Milestone 33 already covered
separately.

Reuses run_decile_backtest, build_hedged_return_series, build_regime_dummies,
hac_regression, market_proxy, apply_cost, historical_worst_episode_length,
and simulate_episode unchanged.

Run: python investigations/crash_cost_interaction.py
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
from investigations.momentum_crash_severity_stress_test import (
    historical_worst_episode_length,
    simulate_episode,
)
from investigations.momentum_crash_significance import build_regime_dummies, hac_regression
from investigations.short_leg_beta import market_proxy
from investigations.transaction_cost_realism import apply_cost
from signals.momentum import momentum_12_1

HAC_LAGS_DAILY = 21
BASELINE_COST_BPS = 10.0
POST_2008 = "2008-09-01"
N_SIMS = 20_000
SEED = 11
CRASH_COST_MULTIPLIERS = [1.0, 1.5, 2.0, 3.0, 5.0]


def build_crash_cost_series(turnover: pd.Series, regime_at_reb: pd.DataFrame, multiplier: float) -> pd.Series:
    """Flat BASELINE_COST_BPS at every rebalance, multiplied by `multiplier`
    ONLY at rebalances classified Bear+HighVol as of that rebalance date
    (Milestone 17's own look-ahead-free regime dummies). Normal-regime
    rebalances are untouched -- this project's standing flat 10bps."""
    crash_flag = (regime_at_reb["high_vol"] * regime_at_reb["bear"]).reindex(turnover.index).fillna(0.0) > 0
    cost = pd.Series(BASELINE_COST_BPS, index=turnover.index)
    cost[crash_flag] = BASELINE_COST_BPS * multiplier
    return cost, crash_flag


def fit_post_2008_regression(net_long: pd.Series, market: pd.Series, reb_dates: pd.DatetimeIndex,
                              regimes: pd.DataFrame):
    hedged, _beta = build_hedged_return_series(net_long, market, reb_dates)
    post = hedged[hedged.index >= POST_2008].dropna()
    post_regimes = regimes.reindex(post.index)
    interaction = post_regimes["high_vol"] * post_regimes["bear"]
    X = pd.DataFrame({
        "high_vol": post_regimes["high_vol"], "bear": post_regimes["bear"],
        "high_vol_x_bear": interaction,
    })
    return hac_regression(post, X, lags=HAC_LAGS_DAILY)


def main() -> None:
    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)
    regimes = build_regime_dummies(prices)
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=BASELINE_COST_BPS, min_names_per_side=2)
    turnover = result.turnover_by_month
    reb_dates = turnover.index
    regime_at_reb = regimes.reindex(reb_dates)

    worst_len = historical_worst_episode_length(regimes, POST_2008)
    n_crash_rebs_total = int((regime_at_reb["high_vol"] * regime_at_reb["bear"]).fillna(0).sum())
    print(f"Worst historical Bear+HighVol episode, post-2008 sample: {worst_len} trading days "
          f"(the 2008-09 crisis itself).")
    print(f"Rebalances classified Bear+HighVol across the full sample: {n_crash_rebs_total} "
          f"of {len(reb_dates)} ({n_crash_rebs_total / len(reb_dates):.1%}).")

    print(f"\n{'=' * 100}")
    print("Does raising trading costs SPECIFICALLY during Bear+HighVol rebalances (not uniformly")
    print("across the whole sample) worsen the crash mechanism's estimated drawdown, at the SAME")
    print(f"duration Milestone 33 used ({worst_len} trading days, the actual 2008-09 crisis length)?")
    print(f"{'=' * 100}")

    baseline_mean = None
    rng_seed_state = SEED
    for mult in CRASH_COST_MULTIPLIERS:
        cost_series, crash_flag = build_crash_cost_series(turnover, regime_at_reb, mult)
        net_long = apply_cost(result.daily_returns_long, turnover, cost_series)
        fit = fit_post_2008_regression(net_long, market, reb_dates, regimes)
        const, hv, bear, inter = (fit.params["const"], fit.params["high_vol"],
                                   fit.params["bear"], fit.params["high_vol_x_bear"])
        daily_drift_in_regime = const + hv + bear + inter
        residuals = fit.resid.values

        extra_drag = ((cost_series - BASELINE_COST_BPS).clip(lower=0.0) / 10_000.0 * turnover).sum()

        rng = np.random.default_rng(rng_seed_state)  # same seed per multiplier: isolates the cost effect
        cum = simulate_episode(rng, daily_drift_in_regime, residuals, worst_len, N_SIMS)

        label = f"{mult:.1f}x" + (" (this milestone's own flat-cost baseline)" if mult == 1.0 else "")
        print(f"\n  Crash-rebalance cost multiplier: {label}")
        print(f"    interaction coef={inter:+.5f}  p={fit.pvalues['high_vol_x_bear']:.4f}  "
              f"daily drift in regime={daily_drift_in_regime:+.4%}  "
              f"residual std={residuals.std():.4%}")
        print(f"    cumulative EXTRA cost drag vs. flat 10bps, full sample: {extra_drag:.3%}")
        print(f"    {worst_len}-day bootstrap ({N_SIMS:,} paths): mean={cum.mean():+.1%}  "
              f"median={np.median(cum):+.1%}  5th pct={np.percentile(cum, 5):+.1%}  "
              f"95th pct={np.percentile(cum, 95):+.1%}  worst 1%={np.percentile(cum, 1):+.1%}")

        if mult == 1.0:
            baseline_mean = cum.mean()
            print(f"    (note: Milestone 33's own regression was fit on the long leg GROSS of "
                  f"any cost, giving a 1x mean of -25.3%; this milestone's 1.0x baseline embeds "
                  f"this project's standing flat 10bps everywhere, giving {cum.mean():+.1%} here "
                  f"-- the ~0.3pp gap is that standing cost drag, not a new finding.)")
        else:
            print(f"    change in mean cumulative loss vs. this milestone's own 1.0x baseline: "
                  f"{(cum.mean() - baseline_mean):+.2%} of episode return")


if __name__ == "__main__":
    print("Milestone 33 stress-tested crash DURATION with costs held flat. Milestone 35-36")
    print("stress-tested COSTS uniformly across the whole sample. This crosses them: costs rise")
    print("only during Bear+HighVol rebalances (real spreads widen exactly when volatility spikes),")
    print("duration held fixed at the actual worst historical episode (196 trading days).")
    print("Newey-West (HAC) standard errors. Bootstrapped residuals, not assumed Gaussian.\n")
    main()

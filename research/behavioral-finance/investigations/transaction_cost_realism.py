"""
Milestone 35 (line B) tests this project's own longest-standing modeling
simplification, named as an explicit limitation since the project's first
commit: "Transaction costs are a simple linear model, not a real
market-impact model." Every backtest result in this project (momentum's
confirmed edge included) nets out a flat cost_bps per unit of turnover
(backtest/engine.py), regardless of how large that turnover is at any one
rebalance -- a real trading desk's costs are not flat this way; the
well-documented "square-root law" of market impact (Almgren & Chriss 2000,
and a large empirical literature since) finds a trade's cost RATE rises
with the square root of its size relative to typical trading volume, so
total impact cost scales roughly as size^1.5, not size^1.0.

Building a literature-calibrated impact model properly requires average
daily dollar volume (ADV) per name, to convert "how many shares this
rebalance trades" into "what fraction of a normal day's volume that is"
-- the actual driver of impact cost. Checked directly against this
project's own three working data sources before writing a line of this
script: none of them carry volume. `load_nse_github_mirror`,
`load_us_kaggle_mirror`, and `load_asx_github_mirror` (data/loaders.py)
all pivot on a single Close/Last-Sale price column; the yfinance/Stooq
loaders that DO carry volume need general internet access this sandbox's
egress proxy blocks (confirmed again just now -- see README.md "Important
limitation of this environment"). Inventing ADV numbers to force a
"real" impact model would be exactly the kind of unfounded assumption
this project's honesty standard exists to prevent.

So this milestone does two things that stay strictly inside what the data
actually supports, rather than one thing that doesn't:

  1. A linear-cost BREAKEVEN sweep -- the flat cost_bps this project has
     always used, swept from the 10bps default up to 200bps, on momentum's
     two confirmed-edge markets (US, ASX), to find the cost level at which
     the out-of-sample-hedged alpha stops being distinguishable from zero.
     This needs no ADV assumption at all: cost_bps and turnover (already
     computed by every backtest) are the only inputs.

  2. An explicitly-ILLUSTRATIVE convex overlay, following the same
     precedent this project already set for the Q1 fat-tail simulation
     ("calibrated loosely to the LTCM episode's qualitative shape... not
     fit to LTCM's actual undisclosed book" -- README.md, Explicit
     limitations): a square-root-law-*shaped* cost curve, where the
     effective cost rate at a given rebalance scales with the square root
     of that rebalance's turnover relative to the strategy's own median
     turnover (so total dollar cost scales as turnover^1.5, matching the
     literature's finding), calibrated to this project's OWN observed
     turnover distribution rather than to any assumed ADV number. This
     answers "does the SHAPE of a realistic impact curve concentrate cost
     damage in a strategy's highest-turnover months, beyond what a flat
     rate already charges" -- a real, checkable question -- without
     pretending to know an actual dollar cost this project cannot measure.

Reuses run_decile_backtest, build_hedged_return_series, check_plain_alpha,
hac_regression, and market_proxy unchanged.

Run: python investigations/transaction_cost_realism.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return
from data.loaders import load_asx_github_mirror, load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_mechanism_nse import check_plain_alpha
from investigations.momentum_crash_significance import hac_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

N_DECILES = 5
BASELINE_COST_BPS = 10.0
COST_SWEEP_BPS = [10, 25, 50, 75, 100, 150, 200]
IMPACT_GAMMA = 0.5  # square-root law: cost RATE scales with turnover^gamma


def apply_cost(gross_daily: pd.Series, turnover: pd.Series, cost_bps_per_reb: pd.Series) -> pd.Series:
    """gross_daily minus a cost drag applied on each rebalance date, where
    cost_bps_per_reb may vary by date (flat sweep, or the convex overlay)."""
    net = gross_daily.copy()
    drag = turnover * (cost_bps_per_reb / 10_000.0)
    for reb_date, d in drag.items():
        if reb_date in net.index:
            net.loc[reb_date] -= d
    return net


def convex_impact_bps(turnover: pd.Series, base_bps: float, gamma: float) -> pd.Series:
    """Illustrative square-root-law-shaped cost rate: base_bps at the
    strategy's own median turnover, scaling up/down with
    (turnover / median_turnover)^gamma. Calibrated to this project's own
    turnover distribution, not to an assumed ADV -- see module docstring."""
    median_t = turnover.median()
    if median_t == 0:
        return pd.Series(base_bps, index=turnover.index)
    return base_bps * (turnover / median_t).clip(lower=1e-6) ** gamma


def run_market(label: str, prices: pd.DataFrame, pre_break_date: str | None = None) -> None:
    print(f"\n{'=' * 92}\n{label}\n{'=' * 92}")
    market = market_proxy(prices)
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=BASELINE_COST_BPS,
                                  min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    turnover = result.turnover_by_month

    print(f"Monthly one-way turnover: mean={turnover.mean():.1%}  median={turnover.median():.1%}  "
          f"min={turnover.min():.1%}  max={turnover.max():.1%}  (n={len(turnover)} rebalances)")

    print(f"\n{'-' * 92}\nLinear-cost breakeven sweep, full sample (combined long-short book, "
          f"out-of-sample hedged)\n{'-' * 92}")
    for bps in COST_SWEEP_BPS:
        flat = pd.Series(float(bps), index=turnover.index)
        net = apply_cost(result.daily_returns_gross, turnover, flat)
        hedged, _beta = build_hedged_return_series(net, market, reb_dates)
        label_bps = f"{bps}bps" + (" (baseline)" if bps == BASELINE_COST_BPS else "")
        check_plain_alpha(f"  {label_bps}", hedged, reb_dates)

    if pre_break_date is not None:
        print(f"\n{'-' * 92}\nSame sweep, restricted to this project's own established edge window "
              f"(pre-{pre_break_date}, Milestones 13-14)\n{'-' * 92}")
        for bps in COST_SWEEP_BPS:
            flat = pd.Series(float(bps), index=turnover.index)
            net = apply_cost(result.daily_returns_gross, turnover, flat)
            hedged, _beta = build_hedged_return_series(net, market, reb_dates)
            hedged_pre = hedged.loc[:pre_break_date]
            label_bps = f"{bps}bps" + (" (baseline)" if bps == BASELINE_COST_BPS else "")
            check_plain_alpha(f"  {label_bps}", hedged_pre, reb_dates)

    print(f"\n{'-' * 92}\nIllustrative convex (square-root-law-shaped) overlay vs. flat baseline, "
          f"both at {BASELINE_COST_BPS:.0f}bps median rate\n{'-' * 92}")
    convex_bps = convex_impact_bps(turnover, BASELINE_COST_BPS, IMPACT_GAMMA)
    print(f"  Effective cost rate under convex overlay: "
          f"min={convex_bps.min():.1f}bps  median={convex_bps.median():.1f}bps  max={convex_bps.max():.1f}bps "
          f"(vs. flat {BASELINE_COST_BPS:.0f}bps always)")
    flat_baseline = pd.Series(BASELINE_COST_BPS, index=turnover.index)
    net_flat = apply_cost(result.daily_returns_gross, turnover, flat_baseline)
    net_convex = apply_cost(result.daily_returns_gross, turnover, convex_bps)
    hedged_flat, _ = build_hedged_return_series(net_flat, market, reb_dates)
    hedged_convex, _ = build_hedged_return_series(net_convex, market, reb_dates)
    check_plain_alpha("  flat (baseline)", hedged_flat, reb_dates)
    check_plain_alpha("  convex overlay", hedged_convex, reb_dates)
    total_drag_flat = (turnover * BASELINE_COST_BPS / 10_000.0).sum()
    total_drag_convex = (turnover * convex_bps / 10_000.0).sum()
    print(f"  Cumulative cost drag over the sample: flat={total_drag_flat:.2%}  "
          f"convex={total_drag_convex:.2%}  (ratio={total_drag_convex / total_drag_flat:.2f}x)")


def main() -> None:
    us_prices = load_us_kaggle_mirror()
    run_market("US mirror", us_prices, pre_break_date="2008-09-01")

    asx_prices = load_asx_github_mirror()
    run_market("ASX mirror", asx_prices)


if __name__ == "__main__":
    print("Does momentum's confirmed edge survive more realistic transaction cost assumptions")
    print("than this project's standing flat linear cost_bps-per-unit-turnover model?")
    print("Part 1: linear-cost breakeven sweep (no assumptions beyond the flat model itself).")
    print("Part 2: an explicitly illustrative square-root-law-shaped convex overlay, calibrated")
    print("to this project's own turnover distribution -- no real ADV data is available from any")
    print("of this project's three working data sources (checked directly; see module docstring).")
    main()

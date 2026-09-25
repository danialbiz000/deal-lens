"""
Milestone 39 (line C) closes the loop between two of this project's own
findings that have never been tested together. Milestone 31 compared the
current equal-weighted three-signal composite against a momentum-only
variant and found the full composite scored better on GROSS,
out-of-sample-hedged returns on both markets where momentum is confirmed
-- but that comparison, like every comparison in this project before
Milestone 35, never applied a transaction-cost model at all (it used
`daily_returns_gross`, not `daily_returns_net`, and never looked at
turnover). Milestone 35 then found momentum's own US edge is meaningfully
cost-fragile -- real but sitting closer to the margin than its raw
significance suggested. This milestone asks the obvious combined
question Milestone 31 couldn't have asked yet: does blending in two
components with no demonstrated individual skill (52-week-high,
reversal) change the portfolio's TURNOVER enough to matter once
realistic costs are applied, and does the "full composite beats
momentum-only" conclusion survive it?

Three variants (identical to Milestone 31's), re-evaluated at the same
linear-cost sweep Milestone 35 established (10-200bps), plus each
variant's own turnover -- since a blend that trades more often for the
same gross edge is a strictly worse deal once costs are real.

Reuses run_decile_backtest, build_hedged_return_series, check_plain_alpha,
hac_regression, market_proxy, and apply_cost unchanged.

Run: python investigations/composite_cost_realism_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return
from data.loaders import load_asx_github_mirror, load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_mechanism_nse import check_plain_alpha
from investigations.short_leg_beta import market_proxy
from investigations.transaction_cost_realism import apply_cost
from signals.composite import composite_score
from signals.momentum import momentum_12_1

N_DECILES = 5
BASELINE_COST_BPS = 10.0
COST_SWEEP_BPS = [10, 25, 50, 75, 100, 150, 200]

MARKETS = {
    "US mirror": load_us_kaggle_mirror,
    "ASX mirror": load_asx_github_mirror,
}


def momentum_only_score(prices):
    return composite_score(prices, weights={"momentum": 1.0, "high_52w": 0.0, "reversal": 0.0})


VARIANTS = {
    "Equal-weighted composite (momentum + 52w-high + reversal)": composite_score,
    "Evidence-weighted: momentum only (via composite z-score)": momentum_only_score,
    "Momentum alone (signals/momentum.py directly)": lambda p: momentum_12_1(p),
}


def run_variant(variant_name: str, signal_fn, prices: pd.DataFrame, market: pd.Series) -> None:
    signal = signal_fn(prices)
    result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=BASELINE_COST_BPS,
                                  min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    if len(reb_dates) == 0:
        print(f"\n  {variant_name}: no usable rebalances")
        return
    turnover = result.turnover_by_month
    print(f"\n  {variant_name}:")
    print(f"    monthly one-way turnover: mean={turnover.mean():.1%}  median={turnover.median():.1%}")

    for bps in COST_SWEEP_BPS:
        flat = pd.Series(float(bps), index=turnover.index)
        net = apply_cost(result.daily_returns_gross, turnover, flat)
        hedged, _beta = build_hedged_return_series(net, market, reb_dates)
        label = f"{bps}bps" + (" (baseline)" if bps == BASELINE_COST_BPS else "")
        check_plain_alpha(f"    {label}", hedged, reb_dates)


def main() -> None:
    for market_name, loader in MARKETS.items():
        prices = loader()
        market = market_proxy(prices)
        print(f"\n{'=' * 92}\n{market_name}\n{'=' * 92}")
        for variant_name, signal_fn in VARIANTS.items():
            run_variant(variant_name, signal_fn, prices, market)


if __name__ == "__main__":
    print("Milestone 31 found the full equal-weighted composite beats a momentum-only variant")
    print("on GROSS, out-of-sample-hedged returns -- but never applied a transaction-cost model.")
    print("Does blending in two components with no demonstrated individual skill change turnover")
    print("enough to matter once realistic costs (Milestone 35's sweep) are applied?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

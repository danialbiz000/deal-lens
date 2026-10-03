"""
Demo / proof of generalization for the Behavioral Signal & Stress-Risk
Analytics toolkit (toolkit/report.py).

ASX 52-week-high is a genuine "new customer" test case: Milestone 24
tested it for alpha independent of momentum (found none -- it's highly
correlated with momentum, 0.76-0.82, and acts as noise reduction on the
composite rather than an independent source) but it has never once been
run through this project's crash-regime-interaction test or its VaR/CVaR
tail-risk profile. This script is the first time it has.

This is exactly how the toolkit is meant to be used: point it at an
out-of-sample-hedged return series this project's own existing
machinery can build (`build_hedged_return_series`, unchanged since
Milestone 7) and the underlying price panel, and it runs the same
checks Milestones 46 and 53 built for two completely different signals.

Run: python toolkit/demo_52w_high_asx.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

from backtest.engine import run_decile_backtest
from data.loaders import load_asx_github_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.short_leg_beta import market_proxy
from signals.momentum import high_52w_proximity
from toolkit import full_report

N_DECILES = 5
COST_BPS = 10.0


def main() -> None:
    print("Milestone 24 tested ASX 52-week-high for alpha independent of momentum and found")
    print("none -- but no milestone has ever run it through the crash-interaction or VaR/CVaR")
    print("tests. This demo points the generalized toolkit at it for the first time, as a")
    print("worked proof that the toolkit extracted from this project's own signals applies to")
    print("one it has never touched.\n")

    prices = load_asx_github_mirror()
    market = market_proxy(prices)
    signal = high_52w_proximity(prices)
    result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=COST_BPS, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    hedged, _beta = build_hedged_return_series(result.daily_returns_gross, market, reb_dates)

    report = full_report("ASX 52-week-high (combined leg, out-of-sample hedged)", hedged, prices)
    print(report.summary())


if __name__ == "__main__":
    main()

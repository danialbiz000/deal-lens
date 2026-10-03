"""
Milestone 22 tested only momentum on ASX (Australia), this project's third
independent market. NSE and the US Kaggle mirror were both tested on all
three signals (momentum, 52-week-high, short-term reversal) from the very
first pass, back in Milestone 3 -- ASX has an incomplete picture by
comparison. This milestone closes that gap: 52-week-high and short-term
reversal, on ASX, with the identical out-of-sample hedge + HAC methodology
Milestone 22 used for momentum.

Reuses run_decile_backtest, build_hedged_return_series, check_plain_alpha,
and market_proxy unchanged; only the signal function and the market data
source change.

Run: python investigations/all_signals_asx_replication.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return
from data.loaders import load_asx_github_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_mechanism_nse import check_plain_alpha
from investigations.short_leg_beta import market_proxy
from signals.momentum import high_52w_proximity
from signals.reversal import short_term_reversal

SIGNALS = {
    "52-week-high": high_52w_proximity,
    "short-term reversal": short_term_reversal,
}


def run_signal(name: str, signal_fn, prices, market) -> None:
    signal = signal_fn(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index

    print(f"\n{'=' * 90}\n{name}\n{'=' * 90}")
    for leg_name, leg_returns in [
        ("long leg", result.daily_returns_long),
        ("combined long-short", result.daily_returns_gross),
    ]:
        raw_ann = annualized_return(leg_returns.dropna())
        hedged, beta_used = build_hedged_return_series(leg_returns, market, reb_dates)
        hedged = hedged.dropna()
        print(f"\n{leg_name}: raw ann. return (unhedged, full sample) = {raw_ann:+.2%}, "
              f"n_hedged_days={len(hedged)}, mean beta={beta_used.mean():.3f}")
        check_plain_alpha(f"{leg_name} (out-of-sample hedged)", hedged, reb_dates)


def main() -> None:
    prices = load_asx_github_mirror()
    market = market_proxy(prices)
    print(f"ASX mirror: {prices.shape[1]} companies, {prices.shape[0]} trading days "
          f"({prices.index.min().date()} to {prices.index.max().date()}).")

    for name, signal_fn in SIGNALS.items():
        run_signal(name, signal_fn, prices, market)


if __name__ == "__main__":
    print("Do 52-week-high and short-term reversal replicate on ASX, completing the")
    print("three-signal picture Milestone 22 only ran for momentum?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

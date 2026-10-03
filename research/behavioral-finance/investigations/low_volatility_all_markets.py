"""
Milestone 25: a genuinely new signal, tested on all three markets from the
start with this project's current best methodology, rather than repeating
the project's own methodological history one market at a time. Every signal
in this project so far (momentum, 52-week-high, short-term reversal) is a
trend/reversal construction built purely from price history. The
low-volatility anomaly (Ang, Hodrick, Xing & Zhang 2006; Frazzini & Pedersen
2014's "betting against beta") is a different kind of bet entirely: rank
names by trailing realized volatility and go long the calmest decile, short
the most volatile one. Standard CAPM says expected return should rise with
volatility/beta; the anomaly is that historically it hasn't.

Reuses run_decile_backtest, build_hedged_return_series, check_plain_alpha,
and market_proxy unchanged; only the signal (signals/low_volatility.py, new
this milestone) and the three existing data sources change.

Run: python investigations/low_volatility_all_markets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return
from data.loaders import load_asx_github_mirror, load_nse_github_mirror, load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_mechanism_nse import check_plain_alpha
from investigations.short_leg_beta import market_proxy
from signals.low_volatility import low_volatility_score

MARKETS = {
    "NSE (India)": load_nse_github_mirror,
    "US Kaggle mirror": load_us_kaggle_mirror,
    "ASX (Australia)": load_asx_github_mirror,
}


def run_market(name: str, loader) -> None:
    prices = loader()
    market = market_proxy(prices)
    signal = low_volatility_score(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index

    print(f"\n{'=' * 90}\n{name}  ({prices.shape[1]} names, {prices.shape[0]} trading days, "
          f"{prices.index.min().date()} to {prices.index.max().date()})\n{'=' * 90}")

    for leg_name, leg_returns in [
        ("long leg (low-vol)", result.daily_returns_long),
        ("combined long-short", result.daily_returns_gross),
    ]:
        raw_ann = annualized_return(leg_returns.dropna())
        hedged, beta_used = build_hedged_return_series(leg_returns, market, reb_dates)
        hedged = hedged.dropna()
        print(f"\n{leg_name}: raw ann. return (unhedged, full sample) = {raw_ann:+.2%}, "
              f"n_hedged_days={len(hedged)}, mean beta={beta_used.mean():.3f}")
        check_plain_alpha(f"{leg_name} (out-of-sample hedged)", hedged, reb_dates)


def main() -> None:
    for name, loader in MARKETS.items():
        run_market(name, loader)


if __name__ == "__main__":
    print("Does the low-volatility anomaly (long calm names, short volatile ones) replicate")
    print("across NSE, US, and ASX, tested with this project's current best methodology?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

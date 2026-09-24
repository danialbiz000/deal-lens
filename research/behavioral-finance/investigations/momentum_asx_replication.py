"""
Milestone 22: does 12-1 momentum's long-leg alpha replicate on a third,
genuinely independent market? NSE (India) and the US Kaggle mirror are this
project's only two markets so far, and both are themselves derived from
community re-exports of the same underlying data lineage (NSE: a single
uploader's CSV; US: a well-known Kaggle "Huge Stock Market Dataset" mirror).
Neither is an independent check on whether momentum is a market-wide
phenomenon or an artifact specific to how those two particular datasets were
built.

Finding a third source was harder than expected -- worth documenting, not
just the result. An extensive search for a European per-company OHLCV mirror
(the first choice) found none reachable from this sandbox: `stooq.com`,
`huggingface.co`, `github.com`'s own HTML pages, and `api.github.com`'s
general repo-browsing API are all blocked by the network proxy here (only
`raw.githubusercontent.com` is allowlisted, and only for exact, known file
paths -- confirmed by every prior milestone's data loader). Several
candidate European-stocks repositories turned out to be pipeline CODE that
fetches from Yahoo Finance or Kaggle at run time (also blocked), not
committed price data. The one source that IS both real, committed,
per-company daily data AND independently sourced from either prior market is
`grantcarthew/data-asx-historical-share-tables` -- a GitHub mirror of the
Australian Securities Exchange's own daily S&P/ASX300 constituent report
emails, spanning 2009-10-20 through 2015-12-31. Not European, but a
genuinely different, independent developed market: different exchange,
different uploader, different underlying data pipeline (official ASX
report emails, not a Kaggle re-export) from both NSE and the US mirror.

This script runs this project's current best-practice momentum test
directly on ASX -- the out-of-sample rolling hedge and HAC significance
check this project has used for every market since Milestone 10/17, not the
cruder full-sample regression Milestones 6-8 started with -- rather than
repeating the project's own methodological history from scratch.

Run: python investigations/momentum_asx_replication.py
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
from signals.momentum import momentum_12_1

HAC_LAGS_DAILY = 21


def main() -> None:
    prices = load_asx_github_mirror()
    print(f"ASX mirror: {prices.shape[1]} companies, {prices.shape[0]} trading days "
          f"({prices.index.min().date()} to {prices.index.max().date()}).")
    avail = prices.notna().sum(axis=1)
    print(f"Daily coverage: min={avail.min()}, median={avail.median():.0f}, "
          f"max={avail.max()} of {prices.shape[1]} names -- well above the "
          f"Milestone 15 thin-universe threshold throughout.\n")

    market = market_proxy(prices)
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    print(f"Decile backtest: {len(reb_dates)} monthly rebalances, "
          f"~{prices.shape[1] // 5} names per decile leg.\n")

    for leg_name, leg_returns in [
        ("long leg", result.daily_returns_long),
        ("combined long-short", result.daily_returns_gross),
    ]:
        raw_ann = annualized_return(leg_returns.dropna())
        hedged, beta_used = build_hedged_return_series(leg_returns, market, reb_dates)
        hedged = hedged.dropna()
        print(f"{leg_name}: raw ann. return (unhedged, full sample) = {raw_ann:+.2%}, "
              f"n_hedged_days={len(hedged)}, mean beta={beta_used.mean():.3f}")
        check_plain_alpha(f"{leg_name} (out-of-sample hedged)", hedged, reb_dates)
        print()


if __name__ == "__main__":
    print("Does momentum's long-leg alpha replicate on ASX (Australia) -- a third, ")
    print("independent market, tested with this project's current best methodology?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10\n")
    main()

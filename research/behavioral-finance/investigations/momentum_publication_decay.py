"""
Tests the specific decay risk flagged in README.md since this project's first
commit, and left untested through Milestone 8: momentum was published by
Jegadeesh & Titman in the Journal of Finance in March 1993, and momentum
premia are well documented in the literature (e.g. McLean & Pontiff, 2016,
"Does Academic Research Destroy Stock Return Predictability?") to weaken
after an anomaly becomes public knowledge -- traders crowd into it and arbitrage
part of the edge away.

Milestone 8 found large, highly significant alpha in 12-1 momentum's long leg
and combined book on the US mirror (annualized ~+8-15%/yr, p<0.01). This
script splits that same result into a PRE-1994 and POST-1994 sub-sample
(cutoff: 1994-01-01, one year after publication) and re-runs the identical
CAPM-style HAC regression on each half separately. If the alpha is a real,
persistent effect, it should show up in both halves. If it's a decayed,
now-arbitraged-away effect, it should be concentrated pre-1994 and weak or
gone post-1994.

Run: python investigations/momentum_publication_decay.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from backtest.engine import run_decile_backtest
from data.loaders import load_us_kaggle_mirror
from investigations.momentum_crash_significance import hac_regression, monthly_returns_at_rebalances, report_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

HAC_LAGS_DAILY = 21
HAC_LAGS_MONTHLY = 6
PUBLICATION_CUTOFF = pd.Timestamp("1994-01-01")  # ~1yr after Jegadeesh & Titman (1993)


def run_era(label: str, y: pd.Series, market: pd.Series, reb_dates: pd.DatetimeIndex) -> None:
    if y.dropna().empty:
        print(f"  {label}: no data in this era")
        return
    n_days = len(y.dropna())
    years = n_days / 252
    print(f"\n  -- {label} ({n_days} trading days, ~{years:.1f} years) --")

    X_daily = pd.DataFrame({"market_return": market.reindex(y.index)})
    report_regression("daily:  y ~ const(alpha) + market_return(beta)",
                       hac_regression(y, X_daily, lags=HAC_LAGS_DAILY))

    era_reb_dates = reb_dates[(reb_dates >= y.index.min()) & (reb_dates <= y.index.max())]
    if len(era_reb_dates) < 8:
        print("    (too few rebalances in this era for a monthly regression)")
        return
    monthly_y = monthly_returns_at_rebalances(y, era_reb_dates)
    monthly_market = monthly_returns_at_rebalances(market, era_reb_dates)
    aligned = pd.concat([monthly_y.rename("y"), monthly_market.rename("m")], axis=1).dropna()
    X_monthly = aligned[["m"]].rename(columns={"m": "market_return"})
    report_regression("monthly: y ~ const(alpha) + market_return(beta)",
                       hac_regression(aligned["y"], X_monthly, lags=HAC_LAGS_MONTHLY))


def main() -> None:
    prices = load_us_kaggle_mirror()
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    market = market_proxy(prices)

    first_reb = result.turnover_by_month.index.min()
    sample_mask = prices.index >= first_reb
    reb_dates = result.turnover_by_month.index

    print(f"Full sample: {first_reb.date()} to {prices.index.max().date()}  "
          f"({len(reb_dates)} rebalances)")
    n_pre = (reb_dates < PUBLICATION_CUTOFF).sum()
    n_post = (reb_dates >= PUBLICATION_CUTOFF).sum()
    print(f"Split at {PUBLICATION_CUTOFF.date()} (~1yr after Jegadeesh & Titman, 1993): "
          f"{n_pre} pre-publication rebalances, {n_post} post-publication rebalances.")

    for leg_name, leg_returns in [
        ("long leg", result.daily_returns_long),
        ("combined long-short", result.daily_returns_gross),
    ]:
        print(f"\n{'=' * 78}\n{leg_name}\n{'=' * 78}")
        y = leg_returns[sample_mask]
        pre = y[y.index < PUBLICATION_CUTOFF]
        post = y[y.index >= PUBLICATION_CUTOFF]
        run_era("PRE-1994 (before/around publication)", pre, market, reb_dates)
        run_era("POST-1994 (after publication)", post, market, reb_dates)


if __name__ == "__main__":
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

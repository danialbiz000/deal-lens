"""
Tests the simplest remaining candidate explanation for why the 52-week-high
signal's short leg loses money: plain market-beta exposure, not anything
specific to "losers" or to crash regimes.

Milestone 5 (investigations/momentum_crash_significance.py) formally rejected
momentum-crash risk as the mechanism -- the short leg showed no significant
regime-conditioning anywhere. That leaves a more mundane possibility
untested: if the basket of stocks "far from their 52-week high" still moves
with the broader market (positive beta), and the market had a positive
average return over both sample periods (2000-2021 for NSE, 1970s/listing-
date-2017 for the US), then a SHORT position in that basket would lose money
on average for a completely ordinary reason -- being short a rising market --
with no crash mechanism, no anchoring bias, and no behavioral story required.

This is a standard CAPM-style test: regress the long leg's and the short
leg's daily (and monthly) returns on the same equal-weighted market proxy
used elsewhere in this project, with Newey-West (HAC) standard errors. Two
things matter:
  - the BETA: is the short leg's exposure to the market significantly
    positive, and how large (close to 1 would mean "basically just short
    the market")?
  - the ALPHA (the regression intercept): is there still a significant
    negative return left over after controlling for market exposure? If
    alpha is small/insignificant once beta is accounted for, the "problem"
    is beta, not stock selection. If alpha stays significantly negative,
    something beyond plain market exposure is still going on.

Run: python investigations/short_leg_beta.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd
import statsmodels.api as sm

from backtest.engine import run_decile_backtest
from data.loaders import load_nse_github_mirror, load_us_kaggle_mirror
from investigations.momentum_crash_significance import (
    hac_regression,
    monthly_returns_at_rebalances,
    report_regression,
)
from signals.momentum import high_52w_proximity

HAC_LAGS_DAILY = 21
HAC_LAGS_MONTHLY = 6


def market_proxy(prices: pd.DataFrame) -> pd.Series:
    """Same equal-weighted market proxy used in momentum_crash_significance.py
    -- no external index is available for either mirror."""
    return prices.pct_change().mean(axis=1)


def run_for_market(name: str, prices: pd.DataFrame) -> None:
    print(f"\n{'=' * 78}\n{name}\n{'=' * 78}")
    signal = high_52w_proximity(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    market = market_proxy(prices)

    first_reb = result.turnover_by_month.index.min()
    sample_mask = prices.index >= first_reb
    reb_dates = result.turnover_by_month.index

    print(f"Market proxy: annualized mean return "
          f"{market[sample_mask].mean() * 252:.2%}, "
          f"annualized vol {market[sample_mask].std() * (252 ** 0.5):.2%} "
          f"over the sample used below.")

    legs = [
        ("long leg only", result.daily_returns_long),
        ("short leg only", result.daily_returns_short),
        ("combined long-short", result.daily_returns_gross),
    ]

    print("\n### DAILY frequency (CAPM-style: y ~ const + market_return; HAC lag=21) ###")
    for leg_name, leg_returns in legs:
        y = leg_returns[sample_mask]
        X = pd.DataFrame({"market_return": market[sample_mask]})
        print(f"\n-- {leg_name} --")
        report_regression("y ~ const(alpha) + market_return(beta)", hac_regression(y, X, lags=HAC_LAGS_DAILY))

    print("\n### MONTHLY frequency (HAC lag=6) ###")
    monthly_market = monthly_returns_at_rebalances(market, reb_dates)
    for leg_name, leg_returns in legs:
        monthly_leg = monthly_returns_at_rebalances(leg_returns, reb_dates)
        aligned = pd.concat([monthly_leg.rename("leg"), monthly_market.rename("market")], axis=1).dropna()
        X = aligned[["market"]].rename(columns={"market": "market_return"})
        print(f"\n-- {leg_name} --")
        report_regression(
            "y ~ const(alpha) + market_return(beta)",
            hac_regression(aligned["leg"], X, lags=HAC_LAGS_MONTHLY),
        )


if __name__ == "__main__":
    print("CAPM-style regression against an equal-weighted market proxy built from the same universe.")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    run_for_market("NSE (India)", load_nse_github_mirror())
    run_for_market("US Kaggle mirror", load_us_kaggle_mirror())

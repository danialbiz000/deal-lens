"""
Applies the same beta-hygiene check that debunked the 52-week-high signal
(investigations/short_leg_beta.py, Milestone 6) to the other two signals in
this project's library: 12-1 month momentum and short-term reversal.

Why this matters: short-term reversal was the ONE signal in this project's
original empirical results (README.md, NSE run) that looked like a genuine,
positive, cost-adjusted edge -- the closest thing to a real behavioral
finding this project had. That claim was never re-checked for the same
uncontrolled-beta artifact that turned out to fully explain the 52-week-high
signal's losses. If reversal's "edge" is also just beta exposure, that's a
significant correction to this project's headline empirical result, not a
footnote. If it survives, that's the strongest evidence in this whole
project for a genuine, beta-independent behavioral edge.

Same CAPM-style regression as Milestone 6/short_leg_beta.py: leg return =
alpha + beta * market_return, Newey-West (HAC) standard errors, daily and
monthly frequency, both markets, for both signals' long and short legs plus
the combined long-short book.

Run: python investigations/momentum_reversal_beta.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from backtest.engine import run_decile_backtest
from data.loaders import load_nse_github_mirror, load_us_kaggle_mirror
from investigations.momentum_crash_significance import hac_regression, monthly_returns_at_rebalances
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1
from signals.reversal import short_term_reversal

HAC_LAGS_DAILY = 21
HAC_LAGS_MONTHLY = 6

SIGNALS = {
    "12-1 momentum": momentum_12_1,
    "short-term reversal": short_term_reversal,
}


def stars(p: float) -> str:
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def alpha_beta_row(y: pd.Series, market: pd.Series, lags: int) -> tuple[float, float, float, float]:
    """Returns (alpha, alpha_p, beta, beta_p) for y ~ const + market."""
    X = pd.DataFrame({"market_return": market})
    fit = hac_regression(y, X, lags=lags)
    return (
        float(fit.params["const"]), float(fit.pvalues["const"]),
        float(fit.params["market_return"]), float(fit.pvalues["market_return"]),
    )


def run_for_market(name: str, prices: pd.DataFrame, summary_rows: list[dict]) -> None:
    print(f"\n{'=' * 90}\n{name}\n{'=' * 90}")
    market = market_proxy(prices)

    for signal_name, signal_fn in SIGNALS.items():
        signal = signal_fn(prices)
        result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
        first_reb = result.turnover_by_month.index.min()
        sample_mask = prices.index >= first_reb
        reb_dates = result.turnover_by_month.index

        print(f"\n--- {signal_name} ---")

        legs = [
            ("long leg", result.daily_returns_long),
            ("short leg", result.daily_returns_short),
            ("combined", result.daily_returns_gross),
        ]

        for leg_name, leg_returns in legs:
            y_daily = leg_returns[sample_mask]
            alpha_d, ap_d, beta_d, bp_d = alpha_beta_row(y_daily, market[sample_mask], HAC_LAGS_DAILY)

            monthly_leg = monthly_returns_at_rebalances(leg_returns, reb_dates)
            monthly_market = monthly_returns_at_rebalances(market, reb_dates)
            aligned = pd.concat([monthly_leg.rename("leg"), monthly_market.rename("mkt")], axis=1).dropna()
            alpha_m, ap_m, beta_m, bp_m = alpha_beta_row(aligned["leg"], aligned["mkt"], HAC_LAGS_MONTHLY)

            print(f"  {leg_name:10s} | daily:  alpha={alpha_d:+.5f} (p={ap_d:.3f}{stars(ap_d)})  "
                  f"beta={beta_d:+.2f} (p={bp_d:.3f}{stars(bp_d)})")
            print(f"  {'':10s} | monthly: alpha={alpha_m:+.5f} (p={ap_m:.3f}{stars(ap_m)})  "
                  f"beta={beta_m:+.2f} (p={bp_m:.3f}{stars(bp_m)})")

            summary_rows.append({
                "market": name, "signal": signal_name, "leg": leg_name,
                "daily_alpha_p": ap_d, "monthly_alpha_p": ap_m,
            })


if __name__ == "__main__":
    print("CAPM-style regression (leg return = alpha + beta * market_return), Newey-West (HAC) SEs.")
    print("*** p<0.01  ** p<0.05  * p<0.10")
    summary: list[dict] = []
    run_for_market("NSE (India)", load_nse_github_mirror(), summary)
    run_for_market("US Kaggle mirror", load_us_kaggle_mirror(), summary)

    print(f"\n{'=' * 90}\nSUMMARY: alpha significance after controlling for market beta\n{'=' * 90}")
    df = pd.DataFrame(summary)
    print(df.to_string(index=False, formatters={
        "daily_alpha_p": lambda p: f"{p:.3f}{stars(p)}",
        "monthly_alpha_p": lambda p: f"{p:.3f}{stars(p)}",
    }))

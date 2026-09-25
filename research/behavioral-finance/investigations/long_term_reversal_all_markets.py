"""
Milestone 30 (line A: breadth): a third genuinely new signal, and this time
a deliberately different family from both prior additions. Milestones 25
and 28 both tested "lottery demand" signals (low-volatility, MAX), which
Milestone 29 showed are substantially the same underlying mechanism on the
US mirror. Long-term reversal (De Bondt & Thaler 1985) is a different story
entirely: multi-year overreaction, the opposite prediction from momentum's
12-1 month underreaction, at a much longer horizon than short-term
reversal's ~1 month. Tested on all three markets from the start with this
project's current best methodology, including an immediate non-overlapping
decade breakdown of any significant US result (the standing lesson since
Milestone 26).

Reuses run_decile_backtest, build_hedged_return_series, check_plain_alpha,
and market_proxy unchanged; only the signal (signals/long_term_reversal.py,
new this milestone) and the three existing data sources change. ASX's
2009-2015 sample is too short for a 5-year formation window to produce many
usable rebalances -- reported with that caveat explicit, not silently
omitted.

Run: python investigations/long_term_reversal_all_markets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return
from data.loaders import load_asx_github_mirror, load_nse_github_mirror, load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_mechanism_nse import check_plain_alpha
from investigations.momentum_crash_significance import hac_regression
from investigations.short_leg_beta import market_proxy
from signals.long_term_reversal import long_term_reversal_score

MARKETS = {
    "NSE (India)": load_nse_github_mirror,
    "US Kaggle mirror": load_us_kaggle_mirror,
    "ASX (Australia)": load_asx_github_mirror,
}
US_DECADE_WINDOWS = [
    ("1970-01-01", "1979-12-31"),
    ("1980-01-01", "1989-12-31"),
    ("1990-01-01", "1999-12-31"),
    ("2000-01-01", "2009-12-31"),
    ("2010-01-01", "2017-12-31"),
]
HAC_LAGS_DAILY = 21


def stars(p: float) -> str:
    if p != p:
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def us_decade_breakdown(hedged: pd.Series) -> None:
    print("\n  -- US mirror only: non-overlapping decade breakdown of the combined book "
          "(checked immediately, per the Milestone 26 lesson) --")
    for start, end in US_DECADE_WINDOWS:
        sub = hedged.loc[start:end].dropna()
        if len(sub) < 20:
            print(f"    {start[:4]}-{end[:4]}: insufficient data (n={len(sub)})")
            continue
        fit = hac_regression(sub, pd.DataFrame(index=sub.index), lags=HAC_LAGS_DAILY)
        alpha, p = float(fit.params["const"]), float(fit.pvalues["const"])
        print(f"    {start[:4]}-{end[:4]}: n={len(sub):5d}  ann.ret={annualized_return(sub):+8.2%}  "
              f"daily alpha p={p:.4f}{stars(p)}")


def run_market(name: str, loader) -> None:
    prices = loader()
    market = market_proxy(prices)
    signal = long_term_reversal_score(prices)
    n_valid_dates = signal.notna().any(axis=1).sum()
    print(f"\n{'=' * 90}\n{name}  ({prices.shape[1]} names, {prices.shape[0]} trading days, "
          f"{prices.index.min().date()} to {prices.index.max().date()}, "
          f"{n_valid_dates} dates with a valid formation-period return)\n{'=' * 90}")
    if n_valid_dates < 60:
        print(f"  NOTE: fewer than 60 valid formation dates -- the 5-year lookback barely "
              f"fits this market's history. Results below should be read with that caveat.")

    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    if len(reb_dates) == 0:
        print("  No usable rebalances at all -- signal too sparse for this market's history.")
        return

    combined_hedged = None
    for leg_name, leg_returns in [
        ("long leg (past losers)", result.daily_returns_long),
        ("combined long-short", result.daily_returns_gross),
    ]:
        raw_ann = annualized_return(leg_returns.dropna())
        hedged, beta_used = build_hedged_return_series(leg_returns, market, reb_dates)
        hedged = hedged.dropna()
        print(f"\n{leg_name}: raw ann. return (unhedged, full sample) = {raw_ann:+.2%}, "
              f"n_hedged_days={len(hedged)}, mean beta={beta_used.mean():.3f}")
        check_plain_alpha(f"{leg_name} (out-of-sample hedged)", hedged, reb_dates)
        if leg_name.startswith("combined"):
            combined_hedged = hedged

    if name == "US Kaggle mirror" and combined_hedged is not None:
        us_decade_breakdown(combined_hedged)


def main() -> None:
    for name, loader in MARKETS.items():
        run_market(name, loader)


if __name__ == "__main__":
    print("Does long-term reversal (long past 5-year losers, short past 5-year winners,")
    print("excluding the most recent year) replicate across NSE, US, and ASX?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

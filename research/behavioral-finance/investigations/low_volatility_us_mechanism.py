"""
Milestone 26 investigates the mechanism behind Milestone 25's most striking
result: on the US Kaggle mirror, the low-volatility anomaly doesn't just
fail to replicate, it significantly INVERTS -- the hedged combined book
loses 20.70%/yr (daily, p=0.0002) and 18.09%/yr (monthly, p=0.0004), meaning
high-volatility names significantly outperformed low-volatility ones, net of
beta, over 1970-2017. Milestone 25's own robustness check ruled out a repeat
of Milestone 16's exact pre-1985 thin-universe/data-error problem for
reversal (a ten-start-date sweep found the inversion significant or
near-significant from 1978 through 1995, weakening only from 2000). That
check answers "is the *whole* result an early-window artifact?" but not
"why does it invert at all, and where does the effect actually live?" --
questions this milestone investigates directly, rather than reporting an
unexplained inversion as this project's own final word on it.

This project's US mirror has no market-cap, sector, or fundamentals data --
only price history for a fixed 30-ticker universe of tickers that are all,
by construction, today's mega-cap survivors (Milestone 16's finding, which
applies to this same dataset regardless of which signal is being tested).
Four checks with the data actually available:

1. Decile-membership diagnostic: with only 30 tickers and 5-way ranking,
   each leg holds ~6 names -- not Milestone 16's 2-4-stock extreme, but
   still small enough that a handful of tickers could dominate the result.
   Count actual leg sizes over time.
2. Ticker-concentration check: which names actually populate the high-vol
   (short) and low-vol (long) legs most often during the significant
   1978-1995 window? If the same few tickers dominate throughout, the
   "anomaly" may be a handful of individual stock histories, the same
   diagnosis Milestone 16 made for reversal.
3. Decade-by-decade (non-overlapping) breakdown: Milestone 25's robustness
   check only asked "does it hold from X onward" (cumulative windows, which
   can't distinguish a steady effect from one concentrated in a single early
   decade). This runs the HAC test on non-overlapping decade windows
   directly to locate where the inversion actually lives.
4. Leave-one-ticker-out check: identify the single ticker most responsible
   for the short (high-vol) leg's return in the decade(s) found to matter,
   drop it from the universe entirely, and rerun the full combined-book test
   to see whether the inversion is a broad-based cross-sectional effect or
   one stock's history wearing a factor-anomaly's clothes.

Run: python investigations/low_volatility_us_mechanism.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

from collections import Counter

import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return
from data.loaders import load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_mechanism_nse import check_plain_alpha
from investigations.momentum_crash_significance import hac_regression
from investigations.short_leg_beta import market_proxy
from signals.low_volatility import low_volatility_score

N_DECILES = 5
SIGNIFICANT_WINDOW = ("1978-01-01", "1995-12-31")
DECADE_WINDOWS = [
    ("1970-01-01", "1979-12-31"),
    ("1980-01-01", "1989-12-31"),
    ("1990-01-01", "1999-12-31"),
    ("2000-01-01", "2009-12-31"),
    ("2010-01-01", "2017-12-31"),
]
HAC_LAGS_DAILY = 21


def month_end_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(index.to_series().groupby([index.year, index.month]).max().values))


def leg_membership(scores: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    reb_dates = month_end_dates(prices.index)
    rows = []
    for d in reb_dates:
        if d not in scores.index:
            continue
        cross_section = scores.loc[d].dropna()
        n = len(cross_section)
        if n == 0:
            continue
        ranked = cross_section.rank(pct=True)
        long_names = ranked[ranked >= 1.0 - 1.0 / N_DECILES].index.tolist()
        short_names = ranked[ranked <= 1.0 / N_DECILES].index.tolist()
        rows.append((d, n, len(long_names), len(short_names), long_names, short_names))
    return pd.DataFrame(
        rows, columns=["date", "n_universe", "n_long", "n_short", "long_names", "short_names"]
    ).set_index("date")


def membership_size_diagnostic(membership: pd.DataFrame) -> None:
    print("\n--- Check 1: decile leg size over time (n_deciles=5, so ~1/5 of 30 tickers per leg) ---")
    print(membership[["n_universe", "n_long", "n_short"]].iloc[::24].to_string())
    print(f"  min/median/max long-leg size, full sample: "
          f"{membership['n_long'].min()} / {membership['n_long'].median():.0f} / {membership['n_long'].max()}")
    print(f"  min/median/max short-leg size, full sample: "
          f"{membership['n_short'].min()} / {membership['n_short'].median():.0f} / {membership['n_short'].max()}")


def concentration_check(membership: pd.DataFrame) -> None:
    print(f"\n--- Check 2: ticker concentration in the significant window "
          f"{SIGNIFICANT_WINDOW[0]} to {SIGNIFICANT_WINDOW[1]} ---")
    sub = membership.loc[SIGNIFICANT_WINDOW[0]:SIGNIFICANT_WINDOW[1]]
    n_reb = len(sub)
    for leg_label, col in [("low-vol (long) leg", "long_names"), ("high-vol (short) leg", "short_names")]:
        counts = Counter()
        for names in sub[col]:
            counts.update(names)
        top = counts.most_common(8)
        print(f"\n  {leg_label}, {n_reb} rebalances:")
        for ticker, n in top:
            print(f"    {ticker}: present {n}/{n_reb} months ({n / n_reb:.0%})")


def decade_breakdown(hedged: pd.Series) -> dict[str, float]:
    print("\n--- Check 3: non-overlapping decade breakdown of the hedged combined book ---")
    top_short_leg_ticker_by_decade = {}
    for start, end in DECADE_WINDOWS:
        sub = hedged.loc[start:end].dropna()
        if len(sub) < 20:
            print(f"  {start[:4]}-{end[:4]}: insufficient data (n={len(sub)})")
            continue
        fit = hac_regression(sub, pd.DataFrame(index=sub.index), lags=HAC_LAGS_DAILY)
        alpha, p = float(fit.params["const"]), float(fit.pvalues["const"])
        star = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""
        print(f"  {start[:4]}-{end[:4]}: n={len(sub):5d}  ann.ret={annualized_return(sub):+8.2%}  "
              f"daily alpha p={p:.4f}{star}")
        top_short_leg_ticker_by_decade[f"{start[:4]}-{end[:4]}"] = (annualized_return(sub), p)
    return top_short_leg_ticker_by_decade


def leave_one_out_check(prices: pd.DataFrame, market: pd.Series, drop_ticker: str) -> None:
    print(f"\n--- Check 4: leave-one-out, dropping '{drop_ticker}' from the universe entirely ---")
    reduced_prices = prices.drop(columns=[drop_ticker])
    signal = low_volatility_score(reduced_prices)
    result = run_decile_backtest(reduced_prices, signal, n_deciles=N_DECILES, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    hedged, beta_used = build_hedged_return_series(result.daily_returns_gross, market, reb_dates)
    hedged = hedged.dropna()
    raw_ann = annualized_return(result.daily_returns_gross.dropna())
    print(f"  combined book without {drop_ticker}: raw ann.ret={raw_ann:+.2%}, "
          f"n_hedged_days={len(hedged)}, mean beta={beta_used.mean():.3f}")
    check_plain_alpha(f"combined book, {drop_ticker} excluded (out-of-sample hedged)", hedged, reb_dates)


def main() -> None:
    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)
    signal = low_volatility_score(prices)

    membership = leg_membership(signal, prices)
    membership_size_diagnostic(membership)
    concentration_check(membership)

    result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    hedged, _beta = build_hedged_return_series(result.daily_returns_gross, market, reb_dates)
    decade_breakdown(hedged.dropna())

    # Re-run the ticker with the highest short-leg presence in the significant
    # window through the leave-one-out check, whatever it turns out to be.
    sub = membership.loc[SIGNIFICANT_WINDOW[0]:SIGNIFICANT_WINDOW[1]]
    short_counts = Counter()
    for names in sub["short_names"]:
        short_counts.update(names)
    top_short_ticker = short_counts.most_common(1)[0][0]
    leave_one_out_check(prices, market, top_short_ticker)


if __name__ == "__main__":
    print("Investigating the mechanism behind Milestone 25's US low-volatility inversion:")
    print("is it a broad-based cross-sectional effect, or concentrated in a handful of names/one era?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

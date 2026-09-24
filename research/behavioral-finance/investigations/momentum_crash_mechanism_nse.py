"""
Milestone 16 found the classic Daniel & Moskowitz (2016) momentum-crash
mechanism (Bear x High-Volatility regime interaction) explains momentum's
2008-09 break on the US mirror: dormant pre-2008 (p=0.42), significant
post-2008 (p=0.008). That result was found on one market. This milestone
asks whether the same mechanism shows up on NSE (India) -- a genuine
out-of-market check, not a re-run of an already-settled question:
Milestone 8 established NSE momentum has no significant full-sample alpha,
but using a single STATIC full-sample beta regression, not the rolling,
out-of-sample hedge this project built in Milestone 7 and has used for
every US momentum test since Milestone 10. That more rigorous methodology
has never been applied to NSE momentum before -- this script does both:
re-checks NSE momentum's hedged alpha with the project's own best method,
and tests whether the crash-risk MECHANISM itself is present in a market
that lived through the same 2008 global crisis.

Before trusting any of this, first check the data-density lesson Milestone
15 forced onto this project: NSE's momentum long leg holds 6-10 names
throughout the 2000-2021 sample (vs. the US mirror's notorious 2-4 names
in the 1970s-80s) -- a reasonable, not-degenerate portfolio size, so a
significance result here is not vulnerable to the same thin-universe
artifact. (Checked separately; see README "Data provenance" discussion.)

Two checks, reusing Milestone 7/10's hedge code and Milestone 16's
regime-regression code unchanged:
  1. Plain hedged-alpha significance (daily AND monthly -- this project's
     standard dual-frequency check, since daily HAC significance has
     repeatedly proven less trustworthy than monthly for small-universe,
     monthly-rebalanced portfolios throughout this project), full sample
     and split at the same 2008-09-01 date used since Milestone 14.
  2. The Bear x High-Vol crash-regime regression from Milestone 16,
     applied to NSE for the first time, same split.

Run: python investigations/momentum_crash_mechanism_nse.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return
from data.loaders import load_nse_github_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_significance import (
    build_regime_dummies,
    hac_regression,
    monthly_returns_at_rebalances,
    report_regression,
)
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

HAC_LAGS_DAILY = 21
HAC_LAGS_MONTHLY = 6
BREAK_DATE = pd.Timestamp("2008-09-01")  # same literature-motivated date as Milestones 14-16


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


def hac_alpha(y: pd.Series, lags: int) -> tuple[float, float]:
    y = y.dropna()
    if len(y) < 20:
        return float("nan"), float("nan")
    X = pd.DataFrame(index=y.index)
    fit = hac_regression(y, X, lags=lags)
    return float(fit.params["const"]), float(fit.pvalues["const"])


def check_plain_alpha(label: str, hedged: pd.Series, reb_dates: pd.DatetimeIndex) -> None:
    era = hedged.dropna()
    if era.empty:
        print(f"\n  {label}: no data")
        return
    a_d, p_d = hac_alpha(era, HAC_LAGS_DAILY)
    era_reb = reb_dates[(reb_dates >= era.index.min()) & (reb_dates <= era.index.max())]
    monthly = monthly_returns_at_rebalances(hedged, era_reb).dropna() if len(era_reb) >= 8 else pd.Series(dtype=float)
    a_m, p_m = hac_alpha(monthly, HAC_LAGS_MONTHLY) if len(monthly) >= 8 else (float("nan"), float("nan"))
    print(f"  {label:12s} | daily:  ann_ret={annualized_return(era):+7.2%}  p={p_d:.4f}{stars(p_d):3s} "
          f"(n={len(era)})   monthly: ann_ret={a_m*12:+7.2%}  p={p_m:.4f}{stars(p_m)} (n={len(monthly)})")


def check_crash_regime(label: str, hedged: pd.Series, regimes: pd.DataFrame) -> None:
    era = hedged.dropna()
    if era.empty:
        print(f"\n  {label}: no data")
        return
    era_regimes = regimes.reindex(era.index)
    interaction = era_regimes["high_vol"] * era_regimes["bear"]
    X = pd.DataFrame({
        "high_vol": era_regimes["high_vol"],
        "bear": era_regimes["bear"],
        "high_vol_x_bear": interaction,
    })
    print(f"\n  -- {label} ({len(era)} trading days) --")
    print(f"     Bear+HighVol regime frequency in this era: {interaction.mean():.1%} of days")
    fit = hac_regression(era, X, lags=HAC_LAGS_DAILY)
    report_regression("hedged_return ~ const + high_vol + bear + high_vol*bear  (HAC)", fit)


def main() -> None:
    prices = load_nse_github_mirror()
    market = market_proxy(prices)
    regimes = build_regime_dummies(prices)

    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index

    for leg_name, leg_returns in [
        ("long leg", result.daily_returns_long),
        ("combined long-short", result.daily_returns_gross),
    ]:
        print(f"\n{'=' * 90}\n{leg_name}\n{'=' * 90}")
        hedged, _beta = build_hedged_return_series(leg_returns, market, reb_dates)
        pre = hedged[hedged.index < BREAK_DATE]
        post = hedged[hedged.index >= BREAK_DATE]

        print("\nCheck 1 -- plain hedged-alpha significance (daily vs. monthly):")
        check_plain_alpha("FULL SAMPLE", hedged, reb_dates)
        check_plain_alpha("PRE-2008-09", pre, reb_dates)
        check_plain_alpha("POST-2008-09", post, reb_dates)

        print("\nCheck 2 -- Bear x High-Vol momentum-crash regime regression:")
        check_crash_regime("FULL SAMPLE (2000-2021)", hedged, regimes)
        check_crash_regime("PRE-2008-09", pre, regimes)
        check_crash_regime("POST-2008-09", post, regimes)


if __name__ == "__main__":
    print("NSE: does the OOS-hedged methodology find alpha momentum's static-regression test missed,")
    print("and does the classic momentum-crash mechanism (Milestone 16) show up here too?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

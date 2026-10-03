"""
Milestone 13 found momentum's long leg broke sharply around the 2008-09
financial crisis rather than decaying smoothly since 1994. Milestone 14
formally confirmed a real level shift at that literature-motivated date.
Milestone 11 checked, with a fixed calendar window (Mar-Aug 2009), whether
the break was just the momentum crash -- and found the crash window
mattered for the long leg but did not fully explain either leg's result.
None of that used this project's own most rigorous crash-risk
methodology: the look-ahead-free Bear x High-Volatility regime-interaction
regression built in Milestones 5-6 (momentum_crash_significance.py),
which tested the classic Daniel & Moskowitz (2016) momentum-crash
mechanism -- past losers (the short leg, or in a long-only book, the
market's own downside) snapping back hard after a bear-market low -- and
found it NOT significant for the 52-week-high signal, full-sample.

This milestone asks a sharper, mechanism-level question: does that same
Bear x High-Vol interaction, applied to momentum's own out-of-sample-
hedged long leg and split at the literature-motivated 2008-09-01 date,
explain the post-2008 break? If the interaction term is significant only
post-2008 (or the post-2008 period has structurally more Bear+HighVol
exposure than pre-2008), that is direct evidence the break IS the
momentum-crash mechanism activating, not just a coincidentally-timed
regime shift with an unknown cause. If not, the 2008-09 break remains an
empirically confirmed but mechanistically unexplained fact.

Reuses build_regime_dummies and hac_regression unchanged from
momentum_crash_significance.py for exact consistency with Milestones 5-6's
already-validated methodology.

Run: python investigations/momentum_crash_mechanism_2008.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from backtest.engine import run_decile_backtest
from data.loaders import load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_significance import build_regime_dummies, hac_regression, report_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

HAC_LAGS_DAILY = 21
BREAK_DATE = pd.Timestamp("2008-09-01")  # same literature-motivated date as Milestone 14


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


def run_era(label: str, hedged: pd.Series, regimes: pd.DataFrame) -> None:
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
    prices = load_us_kaggle_mirror()
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
        run_era("PRE-2008-09 (before the literature-motivated break)", pre, regimes)
        run_era("POST-2008-09 (after the break)", post, regimes)


if __name__ == "__main__":
    print("Does the classic momentum-crash mechanism (Bear x High-Vol interaction,")
    print("Milestones 5-6's own methodology) explain momentum's 2008-09 structural break?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

"""
Milestone 18 tested whether the momentum-crash mechanism (Milestone 16)
persisted past the 2008-09 crisis and found no way to test that question at
all: under this project's default 252-day bear-market lookback, no bear
regime recurred anywhere in the US sample after September 2009, so the
post-crisis window had zero Bear+High-Vol observations to test the
interaction against. Milestone 19 then found that "no bear regime
recurred" is itself a lookback-dependent artifact -- at shorter, equally
standard lookbacks (126 and 189 trading days, roughly 6 and 9 months) a
bear regime DOES fire post-2010, clustered in 2010-11 (the European
debt-crisis selloff) and 2015-16 (the Aug 2015-Feb 2016 drawdown), giving
148 and 31 Bear+High-Vol days respectively to actually test persistence
against.

This milestone closes that loop: re-running Milestone 18's persistence
test, but under the two lookback windows where a second bear regime
genuinely exists, to ask the question Milestone 18 could not -- did the
crash mechanism reactivate in 2011 or 2015-16, or has it stayed dormant
outside the one crisis it was originally confirmed in, even now that there
is something to test it against?

Reuses build_regime_dummies_param (Milestone 19), build_hedged_return_series
(Milestone 7/10), hac_regression/report_regression (Milestone 5-6), and
check_plain_alpha (Milestone 17) unchanged.

Run: python investigations/momentum_crash_mechanism_recurrence.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from backtest.engine import run_decile_backtest
from data.loaders import load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_mechanism_nse import check_plain_alpha
from investigations.momentum_crash_regime_robustness import build_regime_dummies_param
from investigations.momentum_crash_significance import hac_regression, report_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

BREAK_DATE = pd.Timestamp("2008-09-01")
CRISIS_END = pd.Timestamp("2009-12-31")
POST_2010 = pd.Timestamp("2010-01-01")
VOL_WINDOW = 21          # this project's default -- only the bear lookback varies here
BEAR_WINDOWS = [126, 189]  # the two windows Milestone 19 found actually see a post-2010 bear regime
HAC_LAGS_DAILY = 21


def run_era(label: str, hedged: pd.Series, era_regimes: pd.DataFrame) -> None:
    era = hedged.dropna()
    if era.empty:
        print(f"\n  {label}: no data")
        return
    regimes = era_regimes.reindex(era.index)
    interaction = regimes["high_vol"] * regimes["bear"]
    X = pd.DataFrame({
        "high_vol": regimes["high_vol"],
        "bear": regimes["bear"],
        "high_vol_x_bear": interaction,
    })
    print(f"\n  -- {label} ({len(era)} trading days) --")
    print(f"     Bear+HighVol regime frequency in this era: {interaction.mean():.1%} of days "
          f"({int(interaction.sum())} days)")
    fit = hac_regression(era, X, lags=HAC_LAGS_DAILY)
    report_regression("hedged_return ~ const + high_vol + bear + high_vol*bear  (HAC)", fit)


def main() -> None:
    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)

    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index

    hedged_long, _beta = build_hedged_return_series(result.daily_returns_long, market, reb_dates)
    pre = hedged_long[hedged_long.index < BREAK_DATE]
    crisis = hedged_long[(hedged_long.index >= BREAK_DATE) & (hedged_long.index <= CRISIS_END)]
    post_crisis = hedged_long[hedged_long.index > CRISIS_END]

    print("Long leg only. Does the crash-mechanism interaction reactivate in 2011 or 2015-16,")
    print("now that a bear regime actually exists there under shorter, equally standard lookbacks?")
    print("Newey-West (HAC) standard errors, 21-day lag. *** p<0.01  ** p<0.05  * p<0.10")

    for bear_window in BEAR_WINDOWS:
        print(f"\n{'=' * 90}\nBear-market lookback = {bear_window} trading days "
              f"(vol window = {VOL_WINDOW}, this project's default)\n{'=' * 90}")
        regimes = build_regime_dummies_param(prices, VOL_WINDOW, bear_window)

        print("\nCheck 1 -- plain hedged-alpha significance (daily vs. monthly), post-2010 only:")
        check_plain_alpha("POST-2010 (2010-01 onward)", post_crisis, reb_dates)

        print("\nCheck 2 -- Bear x High-Vol crash-regime regression:")
        run_era("PRE-2008-09 (unchanged reference)", pre, regimes)
        run_era("CRISIS 2008-09/2009-12 (unchanged reference)", crisis, regimes)
        run_era(f"POST-2010 (bear lookback={bear_window}d -- the new test)", post_crisis, regimes)


if __name__ == "__main__":
    main()

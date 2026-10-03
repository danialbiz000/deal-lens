"""
Milestone 16 found the Bear x High-Volatility momentum-crash mechanism
explains momentum's 2008-09 structural break on the US mirror: dormant
pre-2008 (p=0.42), significant post-2008 (p=0.008), tested on the whole
2008-09-01-onward window as one block. Milestone 17 confirmed the same
mechanism is US-specific (it does not replicate on NSE).

Neither result asks whether "significant post-2008" means a PERMANENT
regime change in how momentum's long leg is exposed to crash risk, or
just reflects the acute 2008-09 crisis itself dominating that block's
regression -- with the mechanism actually dormant again once the crisis
passed. Those two stories have very different implications: a permanent
regime change means the risk model this project would recommend (Part
VI.1) needs a standing crash-hedge; a crisis-specific artifact means the
2008-09 window is an outlier event, not a structural feature to hedge
against going forward.

This milestone splits the post-2008-09 block from Milestones 14/16 into
two: the acute crisis (2008-09-01 to 2009-12-31, ~16 months covering the
crash and the sharp 2009 momentum-crash rebound Milestone 11 already
flagged as the single most extreme sub-period in the whole sample) and
the post-crisis era (2010-01-01 onward, ~8 years of data through the end
of the US mirror's coverage in Nov 2017 -- including the 2011 European
debt-crisis selloff and the Aug 2015-Feb 2016 drawdown, so it is not a
calm-only window). If the interaction term is significant only in the
first block, Milestone 16's "explained by crash risk" finding was really
"explained by one crisis," not a standing feature. If it is significant
in both, the crash-risk regime looks like it persisted.

Reuses build_regime_dummies, hac_regression and report_regression
unchanged from momentum_crash_significance.py, and check_plain_alpha's
dual daily/monthly HAC check unchanged from momentum_crash_mechanism_nse.py
(Milestone 17), for exact methodological consistency.

Run: python investigations/momentum_crash_mechanism_persistence.py
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
from investigations.momentum_crash_significance import build_regime_dummies, hac_regression, report_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

HAC_LAGS_DAILY = 21
BREAK_DATE = pd.Timestamp("2008-09-01")   # same literature-motivated date as Milestones 14/16/17
CRISIS_END = pd.Timestamp("2009-12-31")   # acute crisis + 2009 momentum-crash rebound (Milestone 11)


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
        crisis = hedged[(hedged.index >= BREAK_DATE) & (hedged.index <= CRISIS_END)]
        post_crisis = hedged[hedged.index > CRISIS_END]

        print(f"\nWindow sizes: pre-2008-09 n={len(pre.dropna())}  "
              f"crisis(2008-09..2009-12) n={len(crisis.dropna())}  "
              f"post-crisis(2010-01 onward) n={len(post_crisis.dropna())}")

        print("\nCheck 1 -- plain hedged-alpha significance (daily vs. monthly):")
        check_plain_alpha("PRE-2008-09", pre, reb_dates)
        check_plain_alpha("CRISIS 2008-09/2009-12", crisis, reb_dates)
        check_plain_alpha("POST-CRISIS 2010-01+", post_crisis, reb_dates)

        print("\nCheck 2 -- Bear x High-Vol momentum-crash regime regression:")
        run_era("PRE-2008-09 (before the literature-motivated break)", pre, regimes)
        run_era("CRISIS 2008-09-01 to 2009-12-31 (acute crisis + 2009 rebound)", crisis, regimes)
        run_era("POST-CRISIS 2010-01-01 onward (through end of sample)", post_crisis, regimes)


if __name__ == "__main__":
    print("Is momentum's post-2008 crash-risk exposure (Milestone 16) a permanent regime change,")
    print("or was it driven specifically by the acute 2008-09 crisis window?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

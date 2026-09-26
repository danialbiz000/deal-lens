"""
Milestone 46 (line X) applies this project's own crash-mechanism test
(Milestones 16-17: the Bear x High-Volatility regime-interaction
regression that explains momentum's 2008-09 break) to the two other
signals with an asymmetric, short-a-high-beta-leg construction:
low-volatility (long calm names, short volatile ones) and MAX (long
low-lottery names, short high-lottery ones). Both signals, like momentum,
are short something that plausibly snaps back hard in a post-crash
rebound: momentum is short recent losers (typically high-beta), and
low-volatility/MAX are both short the high-volatility/high-lottery leg,
also typically higher-beta. The theoretical mechanism Daniel & Moskowitz
(2016) describe for momentum -- a beaten-down, high-beta short leg
rallying hard exactly when the market snaps back from a bear low -- has
never been checked against a signal built the same way but for a
different behavioral reason.

This has not been tested before: Milestone 26's decade breakdown of the
US low-volatility inversion checked WHEN the effect concentrated (the
1990s) but never asked WHETHER it concentrates specifically in
Bear+HighVol regimes, the mechanism-level question this project's own
crash-risk toolkit was built to answer. Milestone 29's MAX/low-volatility
control regression checked whether the two signals share a REDUNDANT
mechanism with each other, not whether either carries momentum's OWN
crash-risk signature.

Tested on the two markets where these signals actually show something:
low-volatility on the US mirror (the strong, well-documented inversion)
and ASX (the one live long-leg-only positive result); MAX on the US
mirror (its only notable, if largely low-volatility-explained, result).
All three legs (long, short, combined) are checked, since the theory
specifically predicts SHORT-leg damage, not symmetric damage.

Reuses build_regime_dummies, hac_regression, report_regression,
build_hedged_return_series, and market_proxy unchanged from Milestones
5-6 and 16-17.

Run: python investigations/crash_mechanism_lottery_signals.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return
from data.loaders import load_asx_github_mirror, load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_significance import (
    build_regime_dummies,
    hac_regression,
    report_regression,
)
from investigations.short_leg_beta import market_proxy
from signals.low_volatility import low_volatility_score
from signals.max_effect import max_effect_score

HAC_LAGS_DAILY = 21
N_DECILES = 5


def check_crash_regime(label: str, hedged: pd.Series, regimes: pd.DataFrame) -> None:
    era = hedged.dropna()
    if era.empty or len(era) < 20:
        print(f"\n  {label}: insufficient data")
        return
    era_regimes = regimes.reindex(era.index)
    interaction = era_regimes["high_vol"] * era_regimes["bear"]
    X = pd.DataFrame({
        "high_vol": era_regimes["high_vol"],
        "bear": era_regimes["bear"],
        "high_vol_x_bear": interaction,
    })
    print(f"\n  -- {label} ({len(era)} trading days, "
          f"ann.ret={annualized_return(era):+.2%}) --")
    print(f"     Bear+HighVol regime frequency: {interaction.mean():.1%} of days")
    fit = hac_regression(era, X, lags=HAC_LAGS_DAILY)
    report_regression("hedged_return ~ const + high_vol + bear + high_vol*bear  (HAC)", fit)


def run_signal(signal_name: str, score_fn, market_name: str, loader) -> None:
    print(f"\n{'=' * 96}\n{signal_name} on {market_name}\n{'=' * 96}")
    prices = loader()
    market = market_proxy(prices)
    regimes = build_regime_dummies(prices)
    signal = score_fn(prices)
    result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index

    for leg_name, leg_returns in [
        ("long leg (calm/low-lottery names)", result.daily_returns_long),
        ("short leg (volatile/high-lottery names -- theory predicts damage here)", result.daily_returns_short),
        ("combined long-short", result.daily_returns_gross),
    ]:
        hedged, _beta = build_hedged_return_series(leg_returns, market, reb_dates)
        check_crash_regime(leg_name, hedged, regimes)


def main() -> None:
    run_signal("Low-volatility", low_volatility_score, "US mirror", load_us_kaggle_mirror)
    run_signal("Low-volatility", low_volatility_score, "ASX mirror", load_asx_github_mirror)
    run_signal("MAX effect", max_effect_score, "US mirror", load_us_kaggle_mirror)


if __name__ == "__main__":
    print("Momentum's crash risk (Milestones 16-17) is a Bear+HighVol regime interaction hurting")
    print("its short (high-beta) leg. Low-volatility and MAX are both short a high-beta-like leg")
    print("(high-volatility / high-lottery names) for a different behavioral reason. Does the same")
    print("mechanism show up there too -- never tested before on either signal.")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10\n")
    main()

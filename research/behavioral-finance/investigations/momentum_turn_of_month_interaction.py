"""
Milestone 40 (line R) asks a question this project's own history makes
necessary but has never tested: momentum (Milestone 34's confirmed edge on
US and ASX) and the turn-of-month effect (Milestone 38, the first new
signal since momentum to positively replicate on more than one market) are
each independently validated -- but are they actually INDEPENDENT? Both
have now been shown to decay over the same publication-era timeframe
(Milestones 9-14 for momentum, Milestone 38's own sub-period check for
turn-of-month), which raises a real possibility: if momentum's own edge
happens to cluster on turn-of-month days, the two "separate" findings could
be one mechanism counted twice -- the exact pattern this project already
found once for MAX and low-volatility (Milestone 29) and diagnosed with
exactly this kind of direct regression, not a mere correlation coefficient.

This milestone regresses momentum's own OUT-OF-SAMPLE-HEDGED daily return
series (the same series used for every momentum significance test since
Milestone 7) on the turn-of-month dummy (Milestone 38's exact definition),
on both markets where momentum is confirmed. If the turn-of-month add-on
is small and insignificant, the two findings are safely orthogonal and can
be treated as genuinely independent evidence. If it is large and
significant, momentum's own edge is itself partly a calendar effect, a
real interaction this project's practical framework should know about
before treating the two signals as addable, uncorrelated sources of edge.

Reuses run_decile_backtest, build_hedged_return_series, hac_regression,
market_proxy, and turn_of_month_flags unchanged.

Run: python investigations/momentum_turn_of_month_interaction.py
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
from investigations.momentum_crash_significance import hac_regression
from investigations.short_leg_beta import market_proxy
from investigations.turn_of_month_effect import turn_of_month_flags
from signals.momentum import momentum_12_1

N_DECILES = 5
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


def run_market(label: str, prices: pd.DataFrame) -> None:
    print(f"\n{'=' * 92}\n{label}\n{'=' * 92}")
    market = market_proxy(prices)
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    hedged, _beta = build_hedged_return_series(result.daily_returns_gross, market, reb_dates)
    hedged = hedged.dropna()

    tom = turn_of_month_flags(hedged.index)
    tom_mean = hedged[tom].mean()
    non_tom_mean = hedged[~tom].mean()
    print(f"Trading days: {len(hedged)} total, {int(tom.sum())} turn-of-month "
          f"({tom.mean():.1%} of days)")
    print(f"  Momentum's hedged mean daily return, turn-of-month days:  {tom_mean:+.4%}  "
          f"(implied ann.: {tom_mean * 252:+.2%})")
    print(f"  Momentum's hedged mean daily return, rest-of-month days:  {non_tom_mean:+.4%}  "
          f"(implied ann.: {non_tom_mean * 252:+.2%})")

    X = pd.DataFrame({"turn_of_month": tom.astype(float)}, index=hedged.index)
    fit = hac_regression(hedged, X, lags=HAC_LAGS_DAILY)
    const, tom_coef = float(fit.params["const"]), float(fit.params["turn_of_month"])
    p = float(fit.pvalues["turn_of_month"])
    print(f"  HAC regression: rest-of-month daily alpha (const)={const:+.4%}  "
          f"p={float(fit.pvalues['const']):.4f}{stars(float(fit.pvalues['const']))}")
    print(f"                  turn-of-month ADD-ON={tom_coef:+.4%}/day  "
          f"p={p:.4f}{stars(p)}")
    full_ann = annualized_return(hedged)
    print(f"  Full-sample momentum ann.ret (for context): {full_ann:+.2%}")


def main() -> None:
    run_market("US mirror", load_us_kaggle_mirror())
    run_market("ASX mirror", load_asx_github_mirror())


if __name__ == "__main__":
    print("Momentum (Milestone 34) and the turn-of-month effect (Milestone 38) are each")
    print("independently validated -- but are they actually independent? Regressing momentum's")
    print("own out-of-sample-hedged return on the turn-of-month dummy: a large, significant")
    print("add-on would mean momentum's edge is itself partly a calendar effect, not a")
    print("genuinely separate source of edge from Milestone 38's finding.")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

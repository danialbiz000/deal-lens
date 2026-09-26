"""
Milestone 44 (line V) closes a gap this project's own cost-realism work
(Milestones 35-36, 39) left open: the flat-cost breakeven sweep has only
ever been applied to momentum and the momentum-vs-composite comparison.
This project has coded six cross-sectional signals plus one calendar
effect; the other four -- low-volatility, MAX, long-term reversal,
turn-of-month -- have never been checked against realistic trading costs
at all, even though momentum's own cost-fragility (the US mirror losing
significance between 50-75bps) proves this project's signals do NOT all
respond to costs the same way.

Before running a pointless sweep, this milestone first asks what there
actually IS to protect from cost erosion. Milestones 25-30's own verdicts:
MAX's only notable result (the US inversion) was shown by Milestone 29 to
be low-volatility's own mechanism, not an independent finding -- there is
no MAX-specific edge anywhere to cost-test. Long-term reversal replicated
on no market at all (Milestone 30) -- nothing to test either. That leaves
exactly two live positive findings never checked against costs: ASX
low-volatility's long leg alone (Milestone 25, monthly p=0.0099, the
combined book was NOT significant) and the turn-of-month effect on NSE and
the US mirror (Milestone 38, both p<0.01 full-sample, though already known
to have decayed in the most recent era).

For ASX low-volatility: reuses this project's exact Milestone 35 cost
machinery (apply_cost, build_hedged_return_series) on the long leg alone,
the only leg with a demonstrated result, sweeping the same 10-200bps range.

For turn-of-month: a genuinely different cost model is needed, since this
is a long-only market-timing strategy, not a cross-sectional decile
rebalance -- there is no run_decile_backtest turnover series to reuse. A
strategy that trades only the turn-of-month window enters the market at
the start of each ~4-day window and exits back to cash at the end of it,
roughly once per calendar month (~12 round trips/year). This milestone
charges a round-trip cost (entering AND exiting, 2x the swept cost_bps)
once per window occurrence, deducted from that window's own cumulative
return, and re-tests significance at the same 10-200bps sweep values used
everywhere else in this project for comparability.

Reuses build_hedged_return_series, apply_cost, hac_regression,
market_proxy, and turn_of_month_flags unchanged.

Run: python investigations/cost_realism_remaining_signals.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from backtest.engine import run_decile_backtest
from data.loaders import load_asx_github_mirror, load_nse_github_mirror, load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_significance import hac_regression, monthly_returns_at_rebalances
from investigations.short_leg_beta import market_proxy
from investigations.transaction_cost_realism import apply_cost
from investigations.turn_of_month_effect import turn_of_month_flags
from signals.low_volatility import low_volatility_score

N_DECILES = 5
BASELINE_COST_BPS = 10.0
COST_SWEEP_BPS = [10, 25, 50, 75, 100, 150, 200]


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


def low_vol_asx_sweep() -> None:
    print(f"\n{'=' * 92}\nASX low-volatility, LONG LEG ONLY (Milestone 25's one live positive "
          f"result among low-vol/MAX/long-term-reversal)\n{'=' * 92}")
    prices = load_asx_github_mirror()
    market = market_proxy(prices)
    signal = low_volatility_score(prices)
    result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=BASELINE_COST_BPS,
                                  min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    turnover = result.turnover_by_month
    print(f"Monthly one-way turnover: mean={turnover.mean():.1%}  median={turnover.median():.1%}  "
          f"(n={len(turnover)} rebalances)")
    print(f"{'Cost':<18}{'Daily ann.ret':<16}{'Daily p':<12}{'Monthly ann.ret':<18}{'Monthly p':<10}")
    for bps in COST_SWEEP_BPS:
        flat = pd.Series(float(bps), index=turnover.index)
        net_long = apply_cost(result.daily_returns_long, turnover, flat)
        hedged, _beta = build_hedged_return_series(net_long, market, reb_dates)
        hedged = hedged.dropna()
        fit_d = hac_regression(hedged, pd.DataFrame(index=hedged.index))
        p_d = float(fit_d.pvalues["const"])
        ann_d = (1.0 + hedged).prod() ** (252.0 / len(hedged)) - 1.0

        monthly = monthly_returns_at_rebalances(hedged, reb_dates)
        fit_m = hac_regression(monthly, pd.DataFrame(index=monthly.index), lags=6)
        p_m = float(fit_m.pvalues["const"])
        ann_m = (1.0 + monthly).prod() ** (12.0 / len(monthly)) - 1.0

        label = f"{bps}bps" + (" (baseline)" if bps == BASELINE_COST_BPS else "")
        print(f"{label:<18}{ann_d:<+16.2%}{p_d:<9.4f}{stars(p_d):<3}{ann_m:<+18.2%}{p_m:<7.4f}{stars(p_m)}")


def turn_of_month_cost_sweep(label: str, prices: pd.DataFrame) -> None:
    print(f"\n{'=' * 92}\n{label}: turn-of-month with round-trip trading costs\n{'=' * 92}")
    market = market_proxy(prices).dropna()
    tom = turn_of_month_flags(market.index)

    # identify each window occurrence (a contiguous run of TOM==True days): the
    # ENTRY cost is charged on the first day of the run (buying into the market),
    # the EXIT cost on the last day (selling back to cash) -- a realistic round
    # trip, not both costs dumped onto a single day.
    run_id = (tom != tom.shift(1)).cumsum()
    tom_run_id = run_id[tom]
    occurrence_starts = tom_run_id.groupby(tom_run_id).apply(lambda s: s.index.min())
    occurrence_ends = tom_run_id.groupby(tom_run_id).apply(lambda s: s.index.max())
    n_occurrences = len(occurrence_starts)
    print(f"Trading days: {len(market)} total, {int(tom.sum())} turn-of-month days across "
          f"{n_occurrences} window occurrences (~{n_occurrences / (len(market) / 252):.1f}/yr)")

    for bps in COST_SWEEP_BPS:
        leg_cost = bps / 10_000.0  # one full turnover per entry, one per exit
        net = market.copy()
        for start_date in occurrence_starts:
            net.loc[start_date] -= leg_cost
        for end_date in occurrence_ends:
            net.loc[end_date] -= leg_cost
        X = pd.DataFrame({"turn_of_month": tom.astype(float)}, index=net.index)
        fit = hac_regression(net, X)
        coef, p = float(fit.params["turn_of_month"]), float(fit.pvalues["turn_of_month"])
        label_bps = f"{bps}bps" + (" (baseline)" if bps == BASELINE_COST_BPS else "")
        print(f"  {label_bps:<18} turn-of-month add-on={coef:+.4%}/day  "
              f"(implied ann.: {coef * 252:+.2%})  p={p:.4f}{stars(p)}")


def main() -> None:
    print("Before sweeping costs, checking what there actually is to protect: MAX (Milestone 29)")
    print("and long-term reversal (Milestone 30) have NO positive finding anywhere in this")
    print("project -- nothing to cost-test. That leaves ASX low-volatility's long leg (Milestone")
    print("25) and turn-of-month on NSE/US (Milestone 38) as this project's only other live")
    print("positive findings never checked against realistic costs.\n")

    low_vol_asx_sweep()
    turn_of_month_cost_sweep("NSE (India)", load_nse_github_mirror())
    turn_of_month_cost_sweep("US mirror", load_us_kaggle_mirror())


if __name__ == "__main__":
    main()

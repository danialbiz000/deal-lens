"""
Milestone 45 (line W) tries to build this project's first genuinely
multi-signal, multi-market practical product: a combined portfolio of
ASX momentum and the turn-of-month effect, the two most-scrutinized
"genuinely independent" findings this project has (Milestone 40 showed
momentum and turn-of-month don't share a mechanism, and Milestone 41's
multiple-testing correction confirmed both survive as real, distinct
findings).

Before building it, this milestone checks the premise directly, rather
than assuming it: does any ONE market actually have both signals live at
once? It does not. Milestone 38 found turn-of-month significant on NSE
and the US mirror but explicitly NOT on ASX (p=0.5548) -- so "ASX momentum
+ ASX turn-of-month" is not a real combination; ASX has nothing on the
calendar side to add. And NSE's own momentum result (this project's very
first empirical table) shows no edge at all -- flat to slightly negative,
never rigorously confirmed -- so "NSE momentum + NSE turn-of-month" isn't
real either. The only two signal/market pairs where this project actually
has a currently-live, statistically real edge are ASX momentum (the
cleanest, most repeatedly-stress-tested finding in the whole project) and
NSE turn-of-month (the strongest calendar result, per Milestone 38's own
table) -- in DIFFERENT markets.

That turns out to be the more interesting construction anyway: not "two
signals sharing one market's risk," but two structurally unrelated bets
(cross-sectional stock selection vs. calendar-driven market timing) in two
economically unrelated markets (Australian equities vs. Indian equities),
combined into one book. If this project's independence findings (Milestone
40) and multiple-testing survivors (Milestone 41) are real, this is the
closest thing to a genuine diversification test this project can run.

Both legs are built cost-adjusted at this project's own standing 10bps
baseline -- ASX momentum via the decile-rebalance cost model (Milestone
35), NSE turn-of-month via the round-trip market-timing cost model
(Milestone 44) -- since a "practical product" milestone should not quietly
revert to the gross-return convention used for pure significance testing
elsewhere in this project.

Reuses run_decile_backtest, build_hedged_return_series, apply_cost,
turn_of_month_flags, hac_regression, market_proxy, and the standard
performance metrics unchanged.

Run: python investigations/cross_market_combined_portfolio.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return, annualized_vol, max_drawdown, sharpe_ratio
from data.loaders import load_asx_github_mirror, load_nse_github_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_significance import hac_regression
from investigations.short_leg_beta import market_proxy
from investigations.transaction_cost_realism import apply_cost
from investigations.turn_of_month_effect import turn_of_month_flags
from signals.momentum import momentum_12_1

BASELINE_COST_BPS = 10.0
LEG_WEIGHT = 0.5  # equal-dollar-weighted combination


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


def asx_momentum_leg() -> pd.Series:
    """ASX momentum's out-of-sample-hedged, cost-adjusted (10bps decile
    rebalance) daily return series -- this project's cleanest edge."""
    prices = load_asx_github_mirror()
    market = market_proxy(prices)
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=BASELINE_COST_BPS,
                                  min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    flat = pd.Series(BASELINE_COST_BPS, index=result.turnover_by_month.index)
    net = apply_cost(result.daily_returns_gross, result.turnover_by_month, flat)
    hedged, _beta = build_hedged_return_series(net, market, reb_dates)
    return hedged.dropna()


def nse_turn_of_month_leg() -> pd.Series:
    """NSE turn-of-month's cost-adjusted (10bps round-trip) daily return
    series -- long the market on turn-of-month days net of entry/exit
    cost, flat (in cash) otherwise. Reuses Milestone 44's cost model."""
    prices = load_nse_github_mirror()
    market = market_proxy(prices).dropna()
    tom = turn_of_month_flags(market.index)
    run_id = (tom != tom.shift(1)).cumsum()
    tom_run_id = run_id[tom]
    starts = tom_run_id.groupby(tom_run_id).apply(lambda s: s.index.min())
    ends = tom_run_id.groupby(tom_run_id).apply(lambda s: s.index.max())
    leg_cost = BASELINE_COST_BPS / 10_000.0
    strategy = pd.Series(0.0, index=market.index)
    strategy[tom] = market[tom]
    for d in starts:
        strategy.loc[d] -= leg_cost
    for d in ends:
        strategy.loc[d] -= leg_cost
    return strategy


def report(label: str, daily: pd.Series) -> None:
    fit = hac_regression(daily, pd.DataFrame(index=daily.index))
    p = float(fit.pvalues["const"])
    print(f"  {label:<28} ann.ret={annualized_return(daily):+8.2%}  "
          f"ann.vol={annualized_vol(daily):7.2%}  Sharpe={sharpe_ratio(daily):+6.2f}  "
          f"maxDD={max_drawdown(daily):8.2%}  p(mean=0)={p:.4f}{stars(p)}")


def main() -> None:
    print("Checking the premise first: does any ONE market have both a live momentum edge")
    print("AND a live turn-of-month edge? Milestone 38: turn-of-month is NOT significant on")
    print("ASX (p=0.5548). This project's own first empirical table: NSE momentum shows no")
    print("edge at all. So the only real combination is cross-market: ASX momentum + NSE")
    print("turn-of-month -- two unrelated mechanisms in two unrelated markets.\n")

    asx = asx_momentum_leg()
    nse = nse_turn_of_month_leg()

    print(f"{'=' * 100}\nStandalone legs, each leg's OWN full history "
          f"(both cost-adjusted at this project's 10bps baseline)\n{'=' * 100}")
    report("ASX momentum (hedged)", asx)
    report("NSE turn-of-month", nse)

    # ASX is the shorter-duration series (this project's own recurring limiting factor,
    # e.g. Milestone 34) -- clip the combined book to ASX's own date range, the honest
    # comparable window, rather than a raw index union that would silently dilute the
    # portfolio with years where the ASX leg has no data (and so contributes nothing,
    # not "zero return," an entirely different and misleading thing).
    window_index = nse.index[(nse.index >= asx.index.min()) & (nse.index <= asx.index.max())]
    combined_index = asx.index.union(window_index)
    asx_aligned = asx.reindex(combined_index).fillna(0.0)
    nse_aligned = nse.reindex(combined_index).fillna(0.0)
    combined = LEG_WEIGHT * asx_aligned + LEG_WEIGHT * nse_aligned
    print(f"\nCombined book window: {combined_index.min().date()} to "
          f"{combined_index.max().date()} (ASX's own date range, n={len(combined_index)} "
          f"trading days) -- NOT the full NSE history, to avoid diluting the book with "
          f"years the ASX leg was never actually allocated to.")

    overlap_index = asx.index.intersection(nse.index)
    corr = asx.reindex(overlap_index).corr(nse.reindex(overlap_index))
    print(f"Correlation between the two legs' daily returns "
          f"(n={len(overlap_index)} overlapping trading days): {corr:+.4f}")

    asx_same_window = asx.reindex(combined_index).fillna(0.0)
    nse_same_window = nse.reindex(combined_index).fillna(0.0)
    print(f"\n{'=' * 100}\n50/50 combined book vs. each leg, same window (ASX's own date range)\n{'=' * 100}")
    report("Combined (50% ASX + 50% NSE)", combined)
    report("ASX alone, same window", asx_same_window)
    report("NSE alone, same window", nse_same_window)

    sharpe_asx, sharpe_nse, sharpe_combined = (sharpe_ratio(asx_same_window), sharpe_ratio(nse_same_window),
                                                sharpe_ratio(combined))
    dd_asx, dd_nse, dd_combined = (max_drawdown(asx_same_window), max_drawdown(nse_same_window),
                                    max_drawdown(combined))
    print(f"\nSharpe (same window throughout): ASX alone={sharpe_asx:+.2f}  "
          f"NSE alone={sharpe_nse:+.2f}  combined={sharpe_combined:+.2f}  "
          f"(simple average of the two standalone Sharpes: "
          f"{(sharpe_asx + sharpe_nse) / 2:+.2f})")
    print(f"Max drawdown (same window): ASX alone={dd_asx:.2%}  NSE alone={dd_nse:.2%}  "
          f"combined={dd_combined:.2%}")


if __name__ == "__main__":
    print("Milestone 40 showed momentum and turn-of-month don't share a mechanism; Milestone")
    print("41 showed both survive a formal multiple-testing correction. This milestone asks")
    print("whether combining this project's two genuinely independent live findings into one")
    print("practical, cost-adjusted book produces real diversification, not just an assumed one.\n")
    main()

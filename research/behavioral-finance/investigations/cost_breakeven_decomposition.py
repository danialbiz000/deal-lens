"""
Milestone 36 (line O) digs into the asymmetry Milestone 35 found but did not
explain: ASX momentum shrugged off costs 20x its baseline, while the US
mirror's pre-2008-09 edge -- this project's single most heavily
stress-tested finding -- broke down between 50-75bps. Turnover alone
doesn't obviously explain a gap that large: US monthly one-way turnover
(49.6%) is only ~1.3x ASX's (38.4%), nowhere near enough to explain why one
market's breakeven sits 20x higher than the other's.

This milestone decomposes the gap into its two arithmetic drivers -- raw
edge magnitude and turnover rate -- using the closed-form relationship a
flat linear cost model implies: annualized cost drag is approximately
turnover_annualized * cost_bps / 10,000, so the breakeven cost (where drag
equals the gross edge) is approximately gross_annual_return /
turnover_annualized * 10,000. It then finds the EXACT breakeven via
bisection on the project's own out-of-sample-hedged + HAC pipeline (the
closed-form is an approximation that ignores what hedging does to the
return series) and compares the two, to see how much of the 50-75bps vs.
200bps+ gap is pure edge-size, how much is turnover, and how much the
simple arithmetic story misses.

Finally, and deliberately not skipped: this milestone turns the same
scrutiny on Milestone 35's own model. A flat cost_bps applied identically
to both markets implicitly assumes ASX trades exactly as cheaply as the US
mega-cap mirror -- a real trading desk would expect the opposite (a
~200-300-constituent mid/large-cap Australian universe should, if
anything, face WIDER spreads and thinner order books than 30 US mega-caps,
not equal ones). This project cannot quantify that gap without real
bid-ask/ADV data it has already confirmed it doesn't have (Milestone 35) --
but naming the direction of the bias is still honest and necessary: ASX's
apparent cost-robustness is partly an artifact of an assumption that
almost certainly favors it, not proof a real ASX deployment would be
cheap to trade.

Reuses run_decile_backtest, build_hedged_return_series, check_plain_alpha,
hac_regression, market_proxy, and apply_cost unchanged.

Run: python investigations/cost_breakeven_decomposition.py
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
from investigations.transaction_cost_realism import apply_cost
from signals.momentum import momentum_12_1

N_DECILES = 5
BASELINE_COST_BPS = 10.0
HAC_LAGS_DAILY = 21
SIG_THRESHOLD = 0.10
BISECT_LO, BISECT_HI, BISECT_TOL = 0.0, 500.0, 0.5


def hedged_alpha_at_cost(gross: pd.Series, turnover: pd.Series, market: pd.Series,
                          reb_dates: pd.DatetimeIndex, bps: float,
                          window: tuple[str | None, str | None] = (None, None)) -> tuple[float, float, float]:
    """Returns (annualized_return, HAC daily alpha, HAC p-value) for the
    hedged, net-of-cost series at this cost level. annualized_return uses
    the actual compounded (geometric) growth of the realized series -- the
    same quantity Milestone 35's sweep reported -- while the HAC alpha is
    the arithmetic mean daily return; the two cross zero at different cost
    levels once compounding/variance drag matters, so both are tracked."""
    flat = pd.Series(float(bps), index=turnover.index)
    net = apply_cost(gross, turnover, flat)
    hedged, _beta = build_hedged_return_series(net, market, reb_dates)
    start, end = window
    if start is not None or end is not None:
        hedged = hedged.loc[start:end]
    era = hedged.dropna()
    if len(era) < 20:
        return float("nan"), float("nan"), float("nan")
    fit = hac_regression(era, pd.DataFrame(index=era.index), lags=HAC_LAGS_DAILY)
    return annualized_return(era), float(fit.params["const"]), float(fit.pvalues["const"])


GRID_STEP_BPS = 5.0


def find_breakeven(gross: pd.Series, turnover: pd.Series, market: pd.Series,
                    reb_dates: pd.DatetimeIndex, window: tuple[str | None, str | None],
                    target: str) -> float | None:
    """Finds the FIRST cost_bps (walking up from 0) where either the
    compounded annualized return (target='zero') or the HAC p-value
    (target='sig') crosses its threshold. A p-value is not monotonic in
    cost -- it measures distance from zero either direction, so it can dip
    below the threshold again once cost pushes the point estimate strongly
    negative -- so this scans a coarse grid for the first sign change
    (positive-metric -> non-positive) rather than bisecting the two
    endpoints directly, then refines with a local bisection. Returns None
    if no crossing is found within [BISECT_LO, BISECT_HI]."""
    def metric(bps: float) -> float:
        ann_ret, _alpha, p = hedged_alpha_at_cost(gross, turnover, market, reb_dates, bps, window)
        return ann_ret if target == "zero" else (SIG_THRESHOLD - p)

    prev_bps, prev_m = BISECT_LO, metric(BISECT_LO)
    if prev_m != prev_m or prev_m <= 0:
        return None  # no edge to begin with (nan or already non-positive at zero cost)

    bps = BISECT_LO + GRID_STEP_BPS
    while bps <= BISECT_HI:
        m = metric(bps)
        if m == m and m <= 0:
            lo, hi = prev_bps, bps
            while hi - lo > BISECT_TOL:
                mid = (lo + hi) / 2
                if metric(mid) > 0:
                    lo = mid
                else:
                    hi = mid
            return (lo + hi) / 2
        prev_bps, prev_m = bps, m
        bps += GRID_STEP_BPS
    return None


def analyze_market(label: str, prices: pd.DataFrame, window: tuple[str | None, str | None] = (None, None)) -> None:
    print(f"\n{'=' * 92}\n{label}\n{'=' * 92}")
    market = market_proxy(prices)
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=BASELINE_COST_BPS,
                                  min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    turnover = result.turnover_by_month
    gross = result.daily_returns_gross

    hedged_baseline, _ = build_hedged_return_series(gross, market, reb_dates)
    start, end = window
    hedged_window = hedged_baseline.loc[start:end].dropna() if (start or end) else hedged_baseline.dropna()
    gross_ann = annualized_return(hedged_window)
    turnover_window = turnover.loc[start:end] if (start or end) else turnover
    turnover_ann = turnover_window.mean() * 12.0

    closed_form_bps = gross_ann / turnover_ann * 10_000.0 if turnover_ann > 0 else float("nan")
    print(f"Gross hedged ann.return (window): {gross_ann:+.2%}")
    print(f"Annualized turnover (12 x mean monthly): {turnover_ann:.2%}")
    print(f"Closed-form breakeven estimate (return / turnover): {closed_form_bps:,.0f}bps")

    be_zero = find_breakeven(gross, turnover, market, reb_dates, window, target="zero")
    be_sig = find_breakeven(gross, turnover, market, reb_dates, window, target="sig")
    print(f"Bisected exact breakeven (point estimate crosses zero): "
          f"{be_zero:,.0f}bps" if be_zero is not None else
          f"Bisected exact breakeven (point estimate crosses zero): not reached within {BISECT_HI:.0f}bps")
    print(f"Bisected exact breakeven (HAC p crosses {SIG_THRESHOLD}): "
          f"{be_sig:,.0f}bps" if be_sig is not None else
          f"Bisected exact breakeven (HAC p crosses {SIG_THRESHOLD}): not reached within {BISECT_HI:.0f}bps")


def main() -> None:
    us_prices = load_us_kaggle_mirror()
    analyze_market("US mirror, restricted to pre-2008-09-01 (the project's established edge window)",
                    us_prices, window=(None, "2008-09-01"))

    asx_prices = load_asx_github_mirror()
    analyze_market("ASX mirror, full sample", asx_prices)


if __name__ == "__main__":
    print("Milestone 35 found ASX momentum robust to 200bps+ while the US mirror's pre-2008-09")
    print("edge breaks down between 50-75bps. Turnover differs by only ~1.3x -- what actually")
    print("drives a breakeven gap this large? Decomposing edge magnitude vs. turnover rate,")
    print("and finding the exact breakeven via bisection rather than the coarse 10-200bps sweep.")
    main()

"""
Closes the loop opened by Milestone 9 (momentum_publication_decay.py) the
same way Milestone 7 (beta_hedged_backtest.py) closed the loop opened by
Milestone 6: a static, full-sample regression coefficient is not the same
thing as a real, tradeable strategy. Milestone 8/9 established that 12-1
momentum's long leg and combined book carry significant alpha with the
combined book's beta close to zero -- via a single regression coefficient
per sub-sample. This script builds the same ROLLING, OUT-OF-SAMPLE beta
hedge used in Milestone 7 (re-estimated every rebalance from only the
preceding ~1 year of daily returns, applied forward, never looking ahead)
and asks the sharper question: does an actually-tradeable, continuously
re-hedged momentum book still show significant alpha, and does that
survive specifically in the POST-1994 sub-period Milestone 9 flagged as
the honest, decayed number to size against?

This is a materially different, and independently more convincing, test
than Milestone 9's regression: Milestone 9 fits one beta per sub-sample
using the whole sub-sample's data (in-sample). Here beta is re-estimated
monthly from only trailing data, exactly as a real fund would have to
operate it, and the same PUBLICATION_CUTOFF split from Milestone 9 is
applied to the resulting hedged daily return series.

Run: python investigations/momentum_hedged_decay_backtest.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return, annualized_vol, sharpe_ratio
from data.loaders import load_us_kaggle_mirror
from investigations.beta_hedged_backtest import ROLLING_BETA_WINDOW, build_hedged_return_series
from investigations.momentum_crash_significance import hac_regression, monthly_returns_at_rebalances, report_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

HAC_LAGS_DAILY = 21
HAC_LAGS_MONTHLY = 6
PUBLICATION_CUTOFF = pd.Timestamp("1994-01-01")  # same cutoff as Milestone 9


def report_era(label: str, hedged: pd.Series, reb_dates: pd.DatetimeIndex) -> None:
    covered = hedged.dropna()
    if covered.empty:
        print(f"\n  -- {label}: no hedged coverage in this era --")
        return
    n_days = len(covered)
    years = n_days / 252
    print(f"\n  -- {label} ({n_days} hedged trading days, ~{years:.1f} years) --")
    print(f"     ann_ret={annualized_return(covered):.2%}  ann_vol={annualized_vol(covered):.2%}  "
          f"sharpe={sharpe_ratio(covered):.2f}")

    X_const = pd.DataFrame(index=covered.index)
    report_regression(f"  daily:  hedged_return ~ const (HAC lag={HAC_LAGS_DAILY})",
                       hac_regression(covered, X_const, lags=HAC_LAGS_DAILY))

    era_reb_dates = reb_dates[(reb_dates >= covered.index.min()) & (reb_dates <= covered.index.max())]
    if len(era_reb_dates) < 8:
        print("     (too few rebalances in this era for a monthly regression)")
        return
    monthly = monthly_returns_at_rebalances(hedged, era_reb_dates).dropna()
    if len(monthly) < 8:
        print("     (too few monthly observations in this era for a monthly regression)")
        return
    X_const_m = pd.DataFrame(index=monthly.index)
    report_regression(f"  monthly: hedged_return ~ const (HAC lag={HAC_LAGS_MONTHLY})",
                       hac_regression(monthly, X_const_m, lags=HAC_LAGS_MONTHLY))


def main() -> None:
    prices = load_us_kaggle_mirror()
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    market = market_proxy(prices)
    reb_dates = result.turnover_by_month.index

    print(f"Rolling out-of-sample beta hedge (re-estimated every rebalance from the preceding "
          f"{ROLLING_BETA_WINDOW} trading days only), applied to 12-1 momentum.")
    print(f"Split at {PUBLICATION_CUTOFF.date()} (Milestone 9's publication-decay cutoff).\n")

    for leg_name, leg_returns in [
        ("long leg", result.daily_returns_long),
        ("combined long-short", result.daily_returns_gross),
    ]:
        print(f"{'=' * 78}\n{leg_name}\n{'=' * 78}")
        hedged, beta_used = build_hedged_return_series(leg_returns, market, reb_dates)
        covered = hedged.notna()
        print(f"Hedge coverage: {int(covered.sum())} trading days.  "
              f"Beta used: mean={beta_used[covered].mean():+.3f}  std={beta_used[covered].std():.3f}")

        pre = hedged[hedged.index < PUBLICATION_CUTOFF]
        post = hedged[hedged.index >= PUBLICATION_CUTOFF]
        report_era("Full hedged sample", hedged, reb_dates)
        report_era("PRE-1994", pre, reb_dates)
        report_era("POST-1994 (Milestone 9's honest, decayed sub-sample)", post, reb_dates)
        print()


if __name__ == "__main__":
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10\n")
    main()

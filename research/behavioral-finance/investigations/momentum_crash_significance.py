"""
Turns the pattern-matching in investigations/momentum_crash_risk.py into a
formal statistical test, at the user's explicit request. Two upgrades over
that script:

1. **Regime thresholds are now look-ahead-free.** momentum_crash_risk.py cut
   the realized-volatility tercile using the FULL sample's distribution (a
   diagnostic shortcut, flagged there as a limitation). Here the tercile
   cutoffs are computed on an EXPANDING window (each day's "High vol" label
   uses only volatility data up to and including the previous day) -- so the
   regime classification itself, not just the return that follows it, is
   something a live system could have computed in real time.

2. **Regime effects are tested for statistical significance**, not just
   reported as numerically different. Daily strategy returns are regressed
   on regime dummies (High-vol, Bear, and their interaction) using
   Newey-West (HAC) standard errors with a 21-trading-day lag -- the
   standard correction in this literature for serial correlation from
   monthly-rebalanced, overlapping-holding-period returns (the same
   correction style Daniel & Moskowitz use for momentum-crash regressions).
   A separate regression tests whether returns fall monotonically as the
   volatility tercile rises (a linear trend test, not just eyeballing three
   numbers).

Run: python investigations/momentum_crash_significance.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd
import statsmodels.api as sm

from backtest.engine import run_decile_backtest
from data.loaders import load_nse_github_mirror, load_us_kaggle_mirror
from signals.momentum import high_52w_proximity

VOL_WINDOW = 21             # trading days, ~1 month, for realized volatility
MARKET_STATE_WINDOW = 252   # trading days, ~1 year, for trailing market return
MIN_EXPANDING_HISTORY = 252  # don't classify regimes until this much vol history exists
HAC_LAGS = 21                # Newey-West lag length, matches the monthly rebalance/holding cycle


def build_regime_dummies(prices: pd.DataFrame) -> pd.DataFrame:
    """Look-ahead-free regime dummies: HighVol (realized vol above its own
    EXPANDING 2/3 quantile as of yesterday) and Bear (trailing 12-month
    market return negative as of yesterday). Both lagged one day.
    """
    market_ret = prices.pct_change().mean(axis=1)
    realized_vol = market_ret.rolling(VOL_WINDOW).std() * np.sqrt(252)

    expanding_cutoff = realized_vol.expanding(min_periods=MIN_EXPANDING_HISTORY).quantile(2.0 / 3.0)
    high_vol = (realized_vol > expanding_cutoff).astype(float)
    # also keep the raw tercile RANK (0/1/2) via expanding terciles, for the
    # monotonicity trend regression
    low_cutoff = realized_vol.expanding(min_periods=MIN_EXPANDING_HISTORY).quantile(1.0 / 3.0)
    vol_rank = pd.Series(np.nan, index=prices.index)
    vol_rank[realized_vol <= low_cutoff] = 0.0
    vol_rank[(realized_vol > low_cutoff) & (realized_vol <= expanding_cutoff)] = 1.0
    vol_rank[realized_vol > expanding_cutoff] = 2.0

    market_index = (1.0 + market_ret.fillna(0.0)).cumprod()
    trailing_return = market_index / market_index.shift(MARKET_STATE_WINDOW) - 1.0
    bear = (trailing_return < 0).astype(float)

    regimes = pd.DataFrame({"high_vol": high_vol, "vol_rank": vol_rank, "bear": bear})
    return regimes.shift(1)  # lag: today's regime label is as of yesterday's close


def hac_regression(y: pd.Series, X: pd.DataFrame, lags: int = HAC_LAGS):
    aligned = pd.concat([y.rename("y"), X], axis=1).dropna()
    model = sm.OLS(aligned["y"], sm.add_constant(aligned[X.columns]))
    return model.fit(cov_type="HAC", cov_kwds={"maxlags": lags})


def stars(p: float) -> str:
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def report_regression(label: str, result) -> None:
    print(f"  {label}  (n={int(result.nobs)}, R2={result.rsquared:.3f})")
    for name in result.params.index:
        coef = result.params[name]
        t = result.tvalues[name]
        p = result.pvalues[name]
        print(f"    {name:20s} coef={coef:+9.5f}  t={t:+6.2f}  p={p:.4f}  {stars(p)}")


def monthly_returns_at_rebalances(daily: pd.Series, reb_dates: pd.DatetimeIndex) -> pd.Series:
    """Compound daily returns within each (reb_date, next_reb_date] holding
    period into one observation per rebalance -- the frequency the strategy
    actually operates at, and the frequency Daniel & Moskowitz (2016) test
    momentum-crash effects at in the original paper."""
    values = {}
    for i in range(len(reb_dates) - 1):
        start, end = reb_dates[i], reb_dates[i + 1]
        period = daily[(daily.index > start) & (daily.index <= end)]
        if period.empty:
            continue
        values[end] = (1.0 + period).prod() - 1.0
    return pd.Series(values)


def run_for_market(name: str, prices: pd.DataFrame) -> None:
    print(f"\n{'=' * 78}\n{name}\n{'=' * 78}")
    signal = high_52w_proximity(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    regimes = build_regime_dummies(prices)

    first_reb = result.turnover_by_month.index.min()
    sample_mask = prices.index >= first_reb

    interaction = regimes["high_vol"] * regimes["bear"]
    X_regime_daily = pd.DataFrame({
        "high_vol": regimes["high_vol"],
        "bear": regimes["bear"],
        "high_vol_x_bear": interaction,
    })[sample_mask]
    X_trend_daily = regimes[["vol_rank"]][sample_mask]

    reb_dates = result.turnover_by_month.index
    # regime as of the START of each holding period (the rebalance date itself)
    regime_at_reb = regimes.reindex(reb_dates)

    daily_legs = [
        ("combined long-short", result.daily_returns_gross),
        ("long leg only", result.daily_returns_long),
        ("short leg only", result.daily_returns_short),
    ]

    print("\n### DAILY frequency (n ~ thousands of days; HAC lag=21) ###")
    for leg_name, leg_returns in daily_legs:
        y = leg_returns[sample_mask]
        print(f"\n-- {leg_name} --")
        report_regression(
            "Regime-dummy: y ~ const + high_vol + bear + high_vol*bear",
            hac_regression(y, X_regime_daily),
        )
        report_regression(
            "Monotonicity: y ~ const + vol_rank (0=Low,1=Mid,2=High)",
            hac_regression(y, X_trend_daily),
        )

    print("\n### MONTHLY frequency (n ~ number of rebalances; HAC lag=6) ###")
    print("(one return per holding period -- matches the paper's own testing frequency,")
    print(" and removes daily-return noise/autocorrelation as a power/HAC-adequacy concern)")
    for leg_name, leg_returns in daily_legs:
        monthly = monthly_returns_at_rebalances(leg_returns, reb_dates)
        X_regime_m = pd.DataFrame({
            "high_vol": regime_at_reb["high_vol"],
            "bear": regime_at_reb["bear"],
            "high_vol_x_bear": regime_at_reb["high_vol"] * regime_at_reb["bear"],
        }).reindex(monthly.index)
        X_trend_m = regime_at_reb[["vol_rank"]].reindex(monthly.index)
        print(f"\n-- {leg_name} --")
        report_regression(
            "Regime-dummy: y ~ const + high_vol + bear + high_vol*bear",
            hac_regression(monthly, X_regime_m, lags=6),
        )
        report_regression(
            "Monotonicity: y ~ const + vol_rank (0=Low,1=Mid,2=High)",
            hac_regression(monthly, X_trend_m, lags=6),
        )


if __name__ == "__main__":
    print("Newey-West (HAC) standard errors, 21-trading-day lag. "
          "*** p<0.01  ** p<0.05  * p<0.10")
    run_for_market("NSE (India)", load_nse_github_mirror())
    run_for_market("US Kaggle mirror", load_us_kaggle_mirror())

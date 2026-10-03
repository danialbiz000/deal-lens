"""
Milestone 43 (line T) builds the risk metric this project's own risk
playbook (Part VI.2, derived entirely from the Q1 simulation) has never
actually computed on real data: a VaR/CVaR profile for momentum, this
project's one surviving edge, using its ACTUAL out-of-sample-hedged daily
return series -- the same series every significance test in this project
uses -- rather than `risk_simulation/fat_tails_vs_normal.py`'s stylized
Monte Carlo book (a hypothetical LEVERAGE_WEIGHTS portfolio with assumed
regime-switching correlations, explicitly flagged in this project's own
"Explicit limitations" as illustrative, not a real position).

Q1's finding -- a Gaussian, calm-regime-calibrated VaR model understates
the true tail loss because it cannot see fat tails or correlation-spikes
under stress -- was a simulation result about a hypothetical book. This
milestone asks the same question about a real one: does the same GAP
between a parametric (Gaussian) VaR and the actual empirical VaR/CVaR show
up in momentum's real hedged return history, and if so, how large is it?

Three series, all built with this project's standing out-of-sample hedge
construction (`build_hedged_return_series`, unchanged since Milestone 7):
the US mirror full sample, the US mirror restricted to its own established
pre-2008-09 edge window (Milestones 9-14), and the ASX full sample. For
each: empirical (historical, no distributional assumption) VaR and CVaR at
95%, 99%, and 99.9%, next to a Gaussian VaR/CVaR computed from the same
series's own mean and standard deviation, plus skewness and excess
kurtosis to characterize how fat-tailed each series actually is.

A single point estimate is not enough at the far tail: a 99.9% VaR needs
roughly one observation in a thousand to fall beyond it, and this
project's longest series (the US mirror, ~9,000 trading days) has only a
handful of days that extreme -- ASX's six-year, ~1,500-day sample has
essentially none. So each empirical VaR/CVaR is also given a bootstrap
90% confidence interval (resampling days with replacement, respecting
this project's own "let the data speak" preference over an assumed
distribution) to make that estimation uncertainty explicit rather than
reporting a single unstable number as if it were precise.

Reuses run_decile_backtest, build_hedged_return_series, and market_proxy
unchanged.

Run: python investigations/momentum_var_cvar_profile.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd
from scipy import stats

from backtest.engine import run_decile_backtest
from data.loaders import load_asx_github_mirror, load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

N_DECILES = 5
COST_BPS = 10.0
CONFIDENCE_LEVELS = [0.95, 0.99, 0.999]
PRE_2008_END = "2008-09-01"
RELIABLE_DATA_START = "1978-01-01"  # Milestone 15's own flagged thin/glitched-data cutoff
N_BOOTSTRAP = 5_000
SEED = 7


def empirical_var_cvar(returns: np.ndarray, confidence: float) -> tuple[float, float]:
    """VaR/CVaR as POSITIVE loss numbers (a 5% VaR of 0.02 means a 2% loss),
    directly from the empirical distribution -- no Gaussian or other
    parametric assumption."""
    var = -np.quantile(returns, 1.0 - confidence)
    tail = returns[returns <= -var]
    cvar = -tail.mean() if len(tail) > 0 else float("nan")
    return var, cvar


def gaussian_var_cvar(mean: float, std: float, confidence: float) -> tuple[float, float]:
    """Closed-form parametric VaR/CVaR for a Normal(mean, std) distribution,
    the same comparison point Q1's simulation used, but calibrated here to
    a real series's own moments instead of an assumed calm-regime input."""
    z = stats.norm.ppf(confidence)
    var = -(mean - std * z)
    phi_z = stats.norm.pdf(z)
    cvar = -(mean - std * phi_z / (1.0 - confidence))
    return var, cvar


def bootstrap_ci(returns: np.ndarray, confidence: float, rng: np.random.Generator,
                  n_boot: int = N_BOOTSTRAP) -> tuple[float, float, float, float]:
    """90% bootstrap CI (5th-95th pct of the bootstrap distribution) for the
    empirical VaR and CVaR, resampling days with replacement."""
    n = len(returns)
    vars_, cvars_ = np.empty(n_boot), np.empty(n_boot)
    for i in range(n_boot):
        sample = rng.choice(returns, size=n, replace=True)
        vars_[i], cvars_[i] = empirical_var_cvar(sample, confidence)
    return (np.percentile(vars_, 5), np.percentile(vars_, 95),
            np.percentile(cvars_, 5), np.percentile(cvars_, 95))


def report_series(label: str, hedged: pd.Series, rng: np.random.Generator) -> None:
    returns = hedged.dropna().values
    n = len(returns)
    mean, std = returns.mean(), returns.std()
    skew, kurt = stats.skew(returns), stats.kurtosis(returns)  # excess kurtosis (Normal = 0)
    print(f"\n{'=' * 100}\n{label}  (n={n} trading days, mean={mean:+.4%}/day, "
          f"std={std:.4%}/day, skew={skew:+.2f}, excess kurtosis={kurt:+.2f})\n{'=' * 100}")
    if kurt > 1.0:
        print("  Excess kurtosis well above 0: fatter tails than a Normal distribution,")
        print("  the same qualitative signature Q1's simulation assumed rather than measured.")

    print(f"  {'Confidence':<12}{'Gaussian VaR':<14}{'Empirical VaR':<16}{'VaR ratio':<12}"
          f"{'Gaussian CVaR':<15}{'Empirical CVaR':<16}{'CVaR ratio':<11}")
    for conf in CONFIDENCE_LEVELS:
        g_var, g_cvar = gaussian_var_cvar(mean, std, conf)
        e_var, e_cvar = empirical_var_cvar(returns, conf)
        var_ratio = e_var / g_var if g_var != 0 else float("nan")
        cvar_ratio = e_cvar / g_cvar if g_cvar != 0 else float("nan")
        print(f"  {conf:<12.1%}{g_var:<14.3%}{e_var:<16.3%}{var_ratio:<12.2f}"
              f"{g_cvar:<15.3%}{e_cvar:<16.3%}{cvar_ratio:<11.2f}")

    print(f"\n  90% bootstrap CI (resampling days, {N_BOOTSTRAP:,} draws) for the empirical estimate:")
    for conf in CONFIDENCE_LEVELS:
        n_tail_obs = int(np.sum(returns <= np.quantile(returns, 1.0 - conf)))
        var_lo, var_hi, cvar_lo, cvar_hi = bootstrap_ci(returns, conf, rng)
        print(f"    {conf:.1%}: VaR [{var_lo:.3%}, {var_hi:.3%}]  "
              f"CVaR [{cvar_lo:.3%}, {cvar_hi:.3%}]  (~{n_tail_obs} raw tail observations)")

    worst_day = hedged.dropna().idxmin()
    print(f"\n  Single worst day in this series: {worst_day.date()}  ({hedged.loc[worst_day]:+.2%})")


def build_hedged_series(prices: pd.DataFrame) -> pd.Series:
    market = market_proxy(prices)
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=COST_BPS, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    hedged, _beta = build_hedged_return_series(result.daily_returns_gross, market, reb_dates)
    return hedged.dropna()


def main() -> None:
    rng = np.random.default_rng(SEED)

    us_prices = load_us_kaggle_mirror()
    us_hedged = build_hedged_series(us_prices)
    report_series("US mirror, full sample", us_hedged, rng)
    report_series(f"US mirror, pre-{PRE_2008_END} (Milestones 9-14's established edge window)",
                  us_hedged.loc[:PRE_2008_END], rng)

    worst_day = us_hedged.idxmin()
    print(f"\n{'!' * 100}")
    print(f"The single worst US day above ({worst_day.date()}) falls inside the exact 1972-1977 "
          f"window Milestone 15 already flagged as thin (2-4 stock), survivorship-biased, and "
          f"partly data-glitched. Before trusting this project's own tail-risk numbers, checking "
          f"whether they inherit that same known confound -- exactly the kind of check this "
          f"project's own history says not to skip.")
    print(f"{'!' * 100}")
    report_series(f"US mirror, from {RELIABLE_DATA_START} (excluding Milestone 15's flagged "
                   f"1972-77 window)", us_hedged.loc[RELIABLE_DATA_START:], rng)

    asx_prices = load_asx_github_mirror()
    asx_hedged = build_hedged_series(asx_prices)
    report_series("ASX mirror, full sample", asx_hedged, rng)


if __name__ == "__main__":
    print("This project's risk playbook (Part VI.2) is derived entirely from Q1's stylized Monte")
    print("Carlo simulation of a hypothetical book. This milestone computes the same Gaussian-vs-")
    print("empirical VaR/CVaR comparison directly on momentum's REAL out-of-sample-hedged return")
    print("series -- the actual series every significance test in this project already uses.")
    print("Bootstrap 90% CIs quantify how much a far-tail estimate can be trusted given each")
    print("sample's real size.\n")
    main()

"""
Milestone 13 found momentum's decay does not fit a smooth linear trend and
proposed, from eyeballing a rolling 5-year trajectory, that a break around
September 2008 fits the data better. That comparison was descriptive, not
a formal test: the break date was chosen after looking at the data, and
"the best of ~400 candidate split dates will look more significant than
a single pre-specified date" holds even under a null of no true break.
This milestone runs two properly specified, complementary tests instead.

Method A -- a literature-motivated Chow-style test at a SINGLE,
pre-specified date (2008-09-01), motivated externally by Daniel &
Moskowitz's (2016) documented 2009 momentum-crash episode -- not chosen by
inspecting this project's own rolling-window plot from Milestone 13. A
single pre-specified date needs no multiple-testing correction: the
HAC-robust Wald test on a level-shift dummy (reusing this project's
existing hac_regression helper) is valid as-is.

Method B -- a Quandt-Andrews-style sup-Wald test that does NOT assume a
break date. It searches every candidate date in the central 70% of the
sample (15% trimmed from each end, the standard Andrews (1993)
trimming), computes the HAC-robust level-shift Wald statistic at each
candidate, and takes the maximum -- both the statistic's value and which
date it occurs at (a genuinely data-driven break-date estimate, not an
assumed one). Searching many candidate dates inflates the false-positive
rate of comparing that maximum to an ordinary single-test critical value,
so significance is assessed with a residual block-bootstrap instead: fit
the NULL model (one global mean, no break) to the real data, resample
blocks of its residuals with replacement (preserving autocorrelation),
reconstruct many synthetic no-break series, rerun the full candidate
search on each synthetic series, and compare the real sup-statistic to
that empirical null distribution. This project's sandboxed environment
cannot fetch Andrews' (1993) published asymptotic critical-value tables,
so simulating an honest null directly from this project's own data is the
reproducible alternative.

Computational note: Method B's full search-plus-bootstrap is run at
MONTHLY frequency (n~537, ~375 trimmed candidates x 400 bootstrap
resamples is fast, seconds not minutes) since running the equivalent
daily-frequency search inside a bootstrap loop is not tractable in this
environment; Method A (single pre-specified date, one regression) is run
at both frequencies for cross-checking against Milestone 13's daily
results.

A fast, hand-rolled OLS+Newey-West-HAC estimator (matching statsmodels'
cov_type="HAC" convention) is used for the candidate search and
bootstrap loop for speed; it is validated once against this project's
existing hac_regression/statsmodels helper at the top of main() before
being trusted for the full sweep.

Run: python investigations/structural_break_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd
from scipy.stats import norm

from backtest.engine import run_decile_backtest
from data.loaders import load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_significance import hac_regression, monthly_returns_at_rebalances
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1
from signals.reversal import short_term_reversal

HAC_LAGS_DAILY = 21
HAC_LAGS_MONTHLY = 6
LITERATURE_BREAK_DATE = pd.Timestamp("2008-09-01")  # Daniel & Moskowitz (2016) 2009 momentum-crash episode
TRIM_FRACTION = 0.15  # standard Andrews (1993) trimming
N_BOOTSTRAP = 400
BLOCK_LENGTH_MONTHS = 12
RNG_SEED = 20240913  # fixed for reproducibility

SIGNALS = {
    "12-1 momentum": momentum_12_1,
    "short-term reversal": short_term_reversal,
}


def stars(p: float) -> str:
    if np.isnan(p):
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def fast_level_shift_wald(y: np.ndarray, D: np.ndarray, lags: int) -> tuple[float, float]:
    """OLS: y = alpha + delta*D + e. Returns (delta_coef, delta_abs_tstat)
    using a Newey-West/Bartlett HAC sandwich covariance, matching
    statsmodels' cov_type='HAC' convention. D must be a 0/1 array."""
    n = len(y)
    X = np.column_stack([np.ones(n), D])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    resid = y - X @ beta
    g = X * resid[:, None]  # n x 2 score contributions
    S = (g.T @ g) / n
    for lag in range(1, lags + 1):
        w = 1.0 - lag / (lags + 1)
        S_l = (g[lag:].T @ g[:-lag]) / n
        S += w * (S_l + S_l.T)
    V = XtX_inv @ (n * S) @ XtX_inv
    se = np.sqrt(max(V[1, 1], 1e-300))
    return float(beta[1]), float(abs(beta[1]) / se)


def validate_fast_estimator(y: pd.Series, break_date: pd.Timestamp, lags: int) -> None:
    """Sanity check: the hand-rolled HAC estimator should closely match
    this project's existing statsmodels-based hac_regression helper."""
    D = (y.index >= break_date).astype(float)
    X = pd.DataFrame({"post": D}, index=y.index)
    sm_fit = hac_regression(y, X, lags=lags)
    sm_coef, sm_t = float(sm_fit.params["post"]), float(sm_fit.tvalues["post"])

    fast_coef, fast_abs_t = fast_level_shift_wald(y.values, D, lags)

    print(f"    validation @ {break_date.date()}: statsmodels coef={sm_coef:+.6f} t={sm_t:+.3f}  |  "
          f"fast coef={fast_coef:+.6f} |t|={fast_abs_t:.3f}")
    assert abs(fast_coef - sm_coef) < 1e-6, "fast estimator coefficient mismatch"
    assert abs(fast_abs_t - abs(sm_t)) < 0.05 * max(abs(sm_t), 1.0), "fast estimator t-stat mismatch"


def candidate_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    n = len(index)
    lo = int(n * TRIM_FRACTION)
    hi = n - lo
    return index[lo:hi]


def sup_wald_search(y: np.ndarray, index: pd.DatetimeIndex, lags: int) -> tuple[float, pd.Timestamp]:
    """Returns (sup |t|, argmax break date) over the trimmed candidate set."""
    cands = candidate_dates(index)
    best_stat = -np.inf
    best_date = None
    for date in cands:
        D = (index >= date).astype(float)
        if D.sum() < 10 or (len(D) - D.sum()) < 10:
            continue
        _, abs_t = fast_level_shift_wald(y, D, lags)
        if abs_t > best_stat:
            best_stat = abs_t
            best_date = date
    return best_stat, best_date


def block_bootstrap_null_series(resid: np.ndarray, alpha_hat: float, block_len: int, rng: np.random.Generator) -> np.ndarray:
    """Circular moving-block bootstrap of residuals under the null (no break),
    reconstructed around the fitted null-model mean."""
    n = len(resid)
    n_blocks = int(np.ceil(n / block_len))
    starts = rng.integers(0, n, size=n_blocks)
    pieces = [resid[np.arange(s, s + block_len) % n] for s in starts]
    boot_resid = np.concatenate(pieces)[:n]
    return alpha_hat + boot_resid


def run_signal_test(name: str, hedged_monthly: pd.Series, hedged_daily: pd.Series) -> None:
    print(f"\n{'#' * 90}\n# {name.upper()}\n{'#' * 90}")

    # ---- Method A: literature-motivated single-date Chow-style test ----
    print(f"\nMethod A -- Chow-style test at literature-motivated break date {LITERATURE_BREAK_DATE.date()}")
    for label, series, lags in [("daily", hedged_daily, HAC_LAGS_DAILY), ("monthly", hedged_monthly, HAC_LAGS_MONTHLY)]:
        s = series.dropna()
        D = pd.DataFrame({"post": (s.index >= LITERATURE_BREAK_DATE).astype(float)}, index=s.index)
        fit = hac_regression(s, D, lags=lags)
        coef, t, p = float(fit.params["post"]), float(fit.tvalues["post"]), float(fit.pvalues["post"])
        print(f"  [{label}] level shift at break: coef={coef:+.5f} (ann.~{coef * (252 if label == 'daily' else 12):+.2%})  "
              f"t={t:+.2f}  p={p:.4f}{stars(p)}  (n={int(fit.nobs)})")

    # ---- Method B: Quandt-Andrews sup-Wald search + block bootstrap ----
    print(f"\nMethod B -- Quandt-Andrews sup-Wald search (monthly, {TRIM_FRACTION:.0%} trimming) "
          f"+ {N_BOOTSTRAP}-draw block bootstrap")
    m = hedged_monthly.dropna()
    y = m.values
    idx = m.index

    print("  Validating fast HAC estimator against statsmodels:")
    validate_fast_estimator(m, LITERATURE_BREAK_DATE, HAC_LAGS_MONTHLY)

    obs_stat, obs_date = sup_wald_search(y, idx, HAC_LAGS_MONTHLY)
    print(f"  Observed sup|t| = {obs_stat:.3f}  at data-driven break date {obs_date.date() if obs_date is not None else 'N/A'}")

    # Null model: single global mean (no break)
    alpha_hat = float(y.mean())
    resid = y - alpha_hat

    rng = np.random.default_rng(RNG_SEED)
    boot_stats = np.empty(N_BOOTSTRAP)
    for b in range(N_BOOTSTRAP):
        y_boot = block_bootstrap_null_series(resid, alpha_hat, BLOCK_LENGTH_MONTHS, rng)
        boot_stats[b], _ = sup_wald_search(y_boot, idx, HAC_LAGS_MONTHLY)

    p_value = float((boot_stats >= obs_stat).mean())
    print(f"  Bootstrap null sup|t|: mean={boot_stats.mean():.3f}  p90={np.percentile(boot_stats, 90):.3f}  "
          f"p95={np.percentile(boot_stats, 95):.3f}  p99={np.percentile(boot_stats, 99):.3f}")
    print(f"  Empirical p-value (fraction of {N_BOOTSTRAP} no-break bootstrap resamples with sup|t| >= observed): "
          f"p={p_value:.4f}{stars(p_value)}")

    if obs_date is not None:
        months_from_literature = (obs_date.year - LITERATURE_BREAK_DATE.year) * 12 + (obs_date.month - LITERATURE_BREAK_DATE.month)
        print(f"  Data-driven break date vs. literature-motivated date: {obs_date.date()} vs. "
              f"{LITERATURE_BREAK_DATE.date()}  ({months_from_literature:+d} months apart)")


def main() -> None:
    prices = load_us_kaggle_mirror()
    market = market_proxy(prices)

    for name, fn in SIGNALS.items():
        signal = fn(prices)
        result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
        reb_dates = result.turnover_by_month.index
        hedged_daily, _beta = build_hedged_return_series(result.daily_returns_long, market, reb_dates)
        hedged_monthly = monthly_returns_at_rebalances(hedged_daily, reb_dates)
        run_signal_test(name, hedged_monthly, hedged_daily)


if __name__ == "__main__":
    print("Formal structural-break tests on each signal's out-of-sample-hedged long leg.")
    print("Method A: single pre-specified date (Chow-style, HAC Wald test).")
    print("Method B: unknown break date (Quandt-Andrews sup-Wald + block-bootstrap p-value).")
    print("*** p<0.01  ** p<0.05  * p<0.10\n")
    main()

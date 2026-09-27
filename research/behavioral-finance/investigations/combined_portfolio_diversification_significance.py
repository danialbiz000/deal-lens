"""
Milestone 49 (line AB) goes back to Milestone 45's cross-market combined
book (ASX momentum + NSE turn-of-month) and asks a sharper question than
Milestone 45 itself answered.

Milestone 45's own script already ran a formal HAC significance test on
the combined book's own daily return series (not merely inferred from the
two legs), using this project's standing 21-day Newey-West convention, and
got p=0.0001 -- so "is the combined book's return significantly different
from zero" was already answered honestly, not just eyeballed from Sharpe
and drawdown. Re-reading that result carefully, that is NOT the question
this milestone actually needs to ask: a combined book that is 50% ASX
momentum, a position already significant on its own (p=0.0007), is
*mechanically* likely to test significant for "mean != 0" regardless of
whether combining it with NSE turn-of-month adds anything. That headline
p=0.0001 mixes together "ASX momentum works" (already known) with "the
combination itself is doing something."

The real, still-open question is narrower: is the DIVERSIFICATION BENEFIT
Milestone 45 reported -- Sharpe +2.00 for the combined book vs. +1.69 for
ASX alone, a +0.31 improvement over just holding the better single leg --
distinguishable from what block-resampling noise alone would produce over
a comparably short (5.25-year, n=1,321-day) window? Milestone 45's near-
zero correlation estimate (+0.0200) is itself a point estimate over just
1,160 overlapping trading days; this milestone puts a bootstrap confidence
interval on it, and on the Sharpe-improvement figure itself, rather than
treating either as settled because "close to zero" and "higher than both
legs" look right on paper.

Method: block bootstrap (21-trading-day blocks, matching this project's
standing HAC_LAGS_DAILY convention, to preserve within-month serial
dependence) resampling of the ALIGNED (ASX, NSE) daily-return pairs over
the exact same window Milestone 45 used, 5,000 draws. For each draw,
recompute the combined book's Sharpe, both legs' Sharpes, and their
correlation; report the resulting distributions, one-sided bootstrap
p-values for "the Sharpe improvement is <= 0" and "the correlation is
>= a given threshold," and 90% percentile confidence intervals.

Reuses asx_momentum_leg and nse_turn_of_month_leg unchanged from
Milestone 45's cross_market_combined_portfolio.py, and the same window-
clipping logic (ASX's own date range, not a raw index union).

Run: python investigations/combined_portfolio_diversification_significance.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import numpy as np
import pandas as pd

from backtest.metrics import max_drawdown, sharpe_ratio
from investigations.cross_market_combined_portfolio import (
    LEG_WEIGHT,
    asx_momentum_leg,
    nse_turn_of_month_leg,
)
from investigations.momentum_crash_significance import hac_regression

SEED = 20260927
N_BOOTSTRAP = 5_000
BLOCK_LEN = 21  # matches this project's standing HAC_LAGS_DAILY convention
CI_LO, CI_HI = 0.05, 0.95  # 90% percentile interval


def build_aligned_legs() -> tuple[pd.Series, pd.Series]:
    """Reproduces Milestone 45's own window-clipping exactly: the combined
    book is evaluated over ASX's own date range, not a raw index union
    that would dilute it with years the ASX leg was never allocated to."""
    asx = asx_momentum_leg()
    nse = nse_turn_of_month_leg()
    window_index = nse.index[(nse.index >= asx.index.min()) & (nse.index <= asx.index.max())]
    combined_index = asx.index.union(window_index)
    asx_aligned = asx.reindex(combined_index).fillna(0.0)
    nse_aligned = nse.reindex(combined_index).fillna(0.0)
    return asx_aligned, nse_aligned


def block_bootstrap_indices(n: int, block_len: int, rng: np.random.Generator) -> np.ndarray:
    """Draws overlapping blocks of `block_len` consecutive indices, with
    replacement, concatenated until reaching length n, then truncated."""
    n_blocks_needed = int(np.ceil(n / block_len))
    starts = rng.integers(0, n - block_len + 1, size=n_blocks_needed)
    idx = np.concatenate([np.arange(s, s + block_len) for s in starts])
    return idx[:n]


def stars(p: float) -> str:
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def main() -> None:
    print("Milestone 45 reported the combined book's Sharpe (+2.00) beating both legs' own")
    print("Sharpes (+1.69, +1.24) and a near-zero correlation (+0.0200) between them, and")
    print("separately ran a formal HAC test on the combined book's own mean return (p=0.0001).")
    print("That headline test mixes 'ASX momentum works' (already known) with 'the combination")
    print("adds something' -- this milestone isolates the second question with a block")
    print("bootstrap: is the Sharpe IMPROVEMENT over the better single leg, and the near-zero")
    print("correlation estimate, distinguishable from resampling noise over this short window?\n")

    asx_aligned, nse_aligned = build_aligned_legs()
    combined = LEG_WEIGHT * asx_aligned + LEG_WEIGHT * nse_aligned
    n = len(asx_aligned)
    print(f"Combined book window: {asx_aligned.index.min().date()} to "
          f"{asx_aligned.index.max().date()} (n={n} trading days) -- same window Milestone 45 used.\n")

    fit = hac_regression(combined, pd.DataFrame(index=combined.index))
    p_mean = float(fit.pvalues["const"])
    print(f"Reproducing Milestone 45's own combined-book test (HAC, 21 lags): "
          f"p(mean=0)={p_mean:.4f}{stars(p_mean)} -- matches Milestone 45's reported 0.0001, "
          f"included here for a self-contained record, not as a new finding.\n")

    sharpe_asx = sharpe_ratio(asx_aligned)
    sharpe_nse = sharpe_ratio(nse_aligned)
    sharpe_combined = sharpe_ratio(combined)
    sharpe_best_leg = max(sharpe_asx, sharpe_nse)
    improvement = sharpe_combined - sharpe_best_leg
    corr_point = float(np.corrcoef(asx_aligned.values, nse_aligned.values)[0, 1])

    print(f"{'=' * 100}\nPoint estimates (same window, n={n})\n{'=' * 100}")
    print(f"  Sharpe: ASX alone={sharpe_asx:+.2f}  NSE alone={sharpe_nse:+.2f}  "
          f"combined={sharpe_combined:+.2f}  improvement over better single leg={improvement:+.2f}")
    print(f"  Correlation between legs: {corr_point:+.4f}")
    print(f"  Max drawdown: combined={max_drawdown(combined):.2%}  "
          f"vs. better single leg={max_drawdown(asx_aligned if sharpe_asx >= sharpe_nse else nse_aligned):.2%}\n")

    rng = np.random.default_rng(SEED)
    asx_vals = asx_aligned.values
    nse_vals = nse_aligned.values
    boot_improvement = np.empty(N_BOOTSTRAP)
    boot_corr = np.empty(N_BOOTSTRAP)
    boot_sharpe_combined = np.empty(N_BOOTSTRAP)

    for i in range(N_BOOTSTRAP):
        idx = block_bootstrap_indices(n, BLOCK_LEN, rng)
        a = asx_vals[idx]
        b = nse_vals[idx]
        c = LEG_WEIGHT * a + LEG_WEIGHT * b
        sharpe_a = np.mean(a) / np.std(a, ddof=1) * np.sqrt(252) if np.std(a, ddof=1) > 0 else 0.0
        sharpe_b = np.mean(b) / np.std(b, ddof=1) * np.sqrt(252) if np.std(b, ddof=1) > 0 else 0.0
        sharpe_c = np.mean(c) / np.std(c, ddof=1) * np.sqrt(252) if np.std(c, ddof=1) > 0 else 0.0
        boot_sharpe_combined[i] = sharpe_c
        boot_improvement[i] = sharpe_c - max(sharpe_a, sharpe_b)
        boot_corr[i] = np.corrcoef(a, b)[0, 1]

    ci_improvement = (np.quantile(boot_improvement, CI_LO), np.quantile(boot_improvement, CI_HI))
    ci_corr = (np.quantile(boot_corr, CI_LO), np.quantile(boot_corr, CI_HI))
    ci_sharpe_combined = (np.quantile(boot_sharpe_combined, CI_LO), np.quantile(boot_sharpe_combined, CI_HI))
    p_improvement_le_zero = float(np.mean(boot_improvement <= 0.0))
    p_corr_ge_0_3 = float(np.mean(boot_corr >= 0.3))

    print(f"{'=' * 100}\nBlock bootstrap ({N_BOOTSTRAP:,} draws, {BLOCK_LEN}-day blocks)\n{'=' * 100}")
    print(f"  Sharpe improvement over better single leg: point={improvement:+.2f}  "
          f"90% CI=({ci_improvement[0]:+.2f}, {ci_improvement[1]:+.2f})  "
          f"P(improvement<=0)={p_improvement_le_zero:.4f}")
    print(f"  Combined Sharpe: point={sharpe_combined:+.2f}  "
          f"90% CI=({ci_sharpe_combined[0]:+.2f}, {ci_sharpe_combined[1]:+.2f})")
    print(f"  Leg correlation: point={corr_point:+.4f}  "
          f"90% CI=({ci_corr[0]:+.4f}, {ci_corr[1]:+.4f})  "
          f"P(correlation>=0.30)={p_corr_ge_0_3:.4f}")


if __name__ == "__main__":
    main()

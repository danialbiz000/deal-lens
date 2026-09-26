"""
Milestone 41 (line S) runs a check this project has never formally run on
itself, despite having tested six cross-sectional signals across three
markets plus one time-series calendar effect: a multiple-testing
correction across the full family of "does this signal replicate on this
market" hypotheses. This project's own Milestone 5 taught the general
lesson (a 5%-threshold test run on enough independent cuts of data will
produce a "significant" false positive purely by chance at roughly the
rate implied by the threshold) -- but that lesson was applied narrowly, to
one signal's regime-construction robustness sweep, never to the project's
entire signal x market discovery process as a whole.

This assembles the one clean, comparable family of hypothesis tests this
project's own methodology supports: the out-of-sample-hedged, HAC-tested,
full-sample DAILY combined-book significance test -- the same construction
used for every "does X replicate on market Y" headline claim in this
project -- for all 6 cross-sectional signals (momentum, 52-week-high,
short-term reversal, low-volatility, MAX, long-term reversal) on all 3
markets (18 tests), plus the turn-of-month effect's own market-level test
on all 3 markets (3 more), for 21 tests in one pre-registered family.
Benjamini-Hochberg (controlling the false discovery rate) and Bonferroni
(controlling the family-wise error rate, the more conservative choice) are
both applied at alpha=0.05, and the results compared against which
findings this project has actually called "confirmed" -- to check whether
momentum's own two confirmed replications survive a correction most
individual-milestone tests in this project's history never applied.

Every p-value here is computed fresh in this script, not copied from
memory of earlier milestones' write-ups, to avoid compounding any small
transcription drift across 40 milestones of prior work into a
meta-analysis that is supposed to be the most careful check yet.

Reuses run_decile_backtest, build_hedged_return_series, hac_regression,
market_proxy, and turn_of_month_flags unchanged.

Run: python investigations/multiple_testing_correction.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd
from statsmodels.stats.multitest import multipletests

from backtest.engine import run_decile_backtest
from data.loaders import load_asx_github_mirror, load_nse_github_mirror, load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_significance import hac_regression
from investigations.short_leg_beta import market_proxy
from investigations.turn_of_month_effect import turn_of_month_flags
from signals.long_term_reversal import long_term_reversal_score
from signals.low_volatility import low_volatility_score
from signals.max_effect import max_effect_score
from signals.momentum import high_52w_proximity, momentum_12_1
from signals.reversal import short_term_reversal

N_DECILES = 5
HAC_LAGS_DAILY = 21
ALPHA = 0.05

MARKETS = {
    "NSE": load_nse_github_mirror,
    "US": load_us_kaggle_mirror,
    "ASX": load_asx_github_mirror,
}

SIGNALS = {
    "Momentum (12-1)": momentum_12_1,
    "52-week-high": high_52w_proximity,
    "Short-term reversal": short_term_reversal,
    "Low-volatility": low_volatility_score,
    "MAX effect": max_effect_score,
    "Long-term reversal": long_term_reversal_score,
}


def hedged_daily_pvalue(prices: pd.DataFrame, score_fn, market: pd.Series) -> tuple[float, float, int]:
    signal = score_fn(prices)
    result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    if len(reb_dates) == 0:
        return float("nan"), float("nan"), 0
    hedged, _beta = build_hedged_return_series(result.daily_returns_gross, market, reb_dates)
    hedged = hedged.dropna()
    if len(hedged) < 20:
        return float("nan"), float("nan"), len(hedged)
    fit = hac_regression(hedged, pd.DataFrame(index=hedged.index), lags=HAC_LAGS_DAILY)
    return float(fit.params["const"]), float(fit.pvalues["const"]), len(hedged)


def turn_of_month_pvalue(prices: pd.DataFrame, market: pd.Series) -> tuple[float, float, int]:
    market_ret = market.dropna()
    tom = turn_of_month_flags(market_ret.index)
    X = pd.DataFrame({"turn_of_month": tom.astype(float)}, index=market_ret.index)
    fit = hac_regression(market_ret, X, lags=HAC_LAGS_DAILY)
    return float(fit.params["turn_of_month"]), float(fit.pvalues["turn_of_month"]), len(market_ret)


def main() -> None:
    rows = []
    prices_cache = {}
    for market_name, loader in MARKETS.items():
        print(f"Loading {market_name}...")
        prices_cache[market_name] = loader()

    for market_name, prices in prices_cache.items():
        market = market_proxy(prices)
        for signal_name, score_fn in SIGNALS.items():
            alpha, p, n = hedged_daily_pvalue(prices, score_fn, market)
            rows.append({"test": f"{signal_name} on {market_name}", "alpha": alpha, "p": p, "n": n})
        tom_coef, tom_p, tom_n = turn_of_month_pvalue(prices, market)
        rows.append({"test": f"Turn-of-month on {market_name}", "alpha": tom_coef, "p": tom_p, "n": tom_n})

    df = pd.DataFrame(rows).dropna(subset=["p"]).reset_index(drop=True)
    n_tests = len(df)

    bh_reject, bh_adj, _, _ = multipletests(df["p"].values, alpha=ALPHA, method="fdr_bh")
    bonf_reject, bonf_adj, _, _ = multipletests(df["p"].values, alpha=ALPHA, method="bonferroni")
    df["bh_adj_p"] = bh_adj
    df["bh_reject"] = bh_reject
    df["bonf_adj_p"] = bonf_adj
    df["bonf_reject"] = bonf_reject
    df = df.sort_values("p").reset_index(drop=True)

    print(f"\n{'=' * 108}\n{n_tests} tests in the pre-registered family (6 signals x 3 markets, "
          f"daily combined book, + turn-of-month x 3 markets)\n{'=' * 108}")
    print(f"{'Test':<32}{'daily alpha':<14}{'raw p':<10}{'BH-adj p':<12}{'BH sig?':<10}{'Bonf-adj p':<14}{'Bonf sig?':<10}")
    for _, r in df.iterrows():
        print(f"{r['test']:<32}{r['alpha']:<+14.4%}{r['p']:<10.4f}{r['bh_adj_p']:<12.4f}"
              f"{'YES' if r['bh_reject'] else 'no':<10}{min(r['bonf_adj_p'], 1.0):<14.4f}"
              f"{'YES' if r['bonf_reject'] else 'no':<10}")

    n_raw_sig = (df["p"] < ALPHA).sum()
    n_bh_sig = df["bh_reject"].sum()
    n_bonf_sig = df["bonf_reject"].sum()
    expected_by_chance = n_tests * ALPHA
    print(f"\nOut of {n_tests} tests: {n_raw_sig} significant at raw p<{ALPHA} "
          f"(chance alone would produce ~{expected_by_chance:.1f} false positives at this rate); "
          f"{n_bh_sig} survive Benjamini-Hochberg FDR correction; "
          f"{n_bonf_sig} survive the more conservative Bonferroni correction.")


if __name__ == "__main__":
    print("This project has tested 6 cross-sectional signals x 3 markets, plus turn-of-month x 3")
    print("markets (21 tests), across 40 milestones -- but never applied a formal multiple-testing")
    print("correction across that entire family at once. Does momentum's confirmed replication")
    print("survive it? Every p-value below is computed fresh in this script.")
    print("Newey-West (HAC) standard errors throughout.\n")
    main()

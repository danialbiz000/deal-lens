"""
Milestone 48 (line Z) closes the one conspicuous gap left in this
project's own crash-mechanism testing: the Bear+HighVol regime-interaction
test (Milestones 16-18, 20, 46-47) has been applied to momentum on the US
mirror and NSE, and to low-volatility and MAX on the US mirror and ASX --
but never to momentum on ASX, this project's own cleanest, most
repeatedly-stress-tested, currently-live edge. Every other stress test
this project has built for ASX momentum (cost realism, Milestone 35;
sub-period stability, Milestone 34) has never included the one test that
actually explains why momentum crashes in theory. This was not a
deliberate exclusion, just an overlooked one -- ASX has 266 Bear+HighVol
trading days (17.7% of its 1,501-day sample), comfortably enough to
estimate the interaction without the NSE-style rank-deficiency problem
Milestone 19 found in the US post-2009 window.

This milestone runs the test (long and combined legs, full sample -- ASX
has no established pre/post structural break date the way the US mirror
does post-2008-09, so there is no natural split to test separately), then
folds the two new tests into Milestone 47's own 17-test crash-interaction
family. Every one of the 19 p-values is recomputed fresh in this run (by
directly re-invoking Milestone 47's own test functions, not copying
numbers from that milestone's write-up), and Benjamini-Hochberg and
Bonferroni are re-applied across the full, now-complete family.

Reuses momentum_tests and lottery_signal_tests from
crash_mechanism_multiple_testing.py (Milestone 47) unchanged, plus
build_regime_dummies, hac_regression, report_regression,
build_hedged_return_series, run_decile_backtest, and market_proxy.

Run: python investigations/asx_momentum_crash_mechanism.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

import pandas as pd
from statsmodels.stats.multitest import multipletests

from backtest.engine import run_decile_backtest
from data.loaders import load_asx_github_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.crash_mechanism_multiple_testing import lottery_signal_tests, momentum_tests
from investigations.momentum_crash_significance import build_regime_dummies, hac_regression, report_regression
from investigations.short_leg_beta import market_proxy
from signals.momentum import momentum_12_1

HAC_LAGS_DAILY = 21
N_DECILES = 5
ALPHA = 0.05


def stars(p: float) -> str:
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def asx_momentum_tests(rows: list[dict]) -> None:
    prices = load_asx_github_mirror()
    market = market_proxy(prices)
    regimes = build_regime_dummies(prices)
    signal = momentum_12_1(prices)
    result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index

    interaction_freq = (regimes["high_vol"] * regimes["bear"]).mean()
    print(f"ASX Bear+HighVol regime frequency, full sample: {interaction_freq:.1%}\n")

    for leg_name, leg_returns in [("long", result.daily_returns_long), ("combined", result.daily_returns_gross)]:
        hedged, _beta = build_hedged_return_series(leg_returns, market, reb_dates)
        era = hedged.dropna()
        era_regimes = regimes.reindex(era.index)
        interaction = era_regimes["high_vol"] * era_regimes["bear"]
        X = pd.DataFrame({
            "high_vol": era_regimes["high_vol"],
            "bear": era_regimes["bear"],
            "high_vol_x_bear": interaction,
        })
        fit = hac_regression(era, X, lags=HAC_LAGS_DAILY)
        print(f"-- Momentum ASX {leg_name} leg (n={len(era)}) --")
        report_regression("hedged_return ~ const + high_vol + bear + high_vol*bear  (HAC)", fit)
        coef = float(fit.params["high_vol_x_bear"])
        p = float(fit.pvalues["high_vol_x_bear"])
        print(f"  interaction coef={coef:+.5f}  p={p:.4f}{stars(p)}\n")
        rows.append({"test": f"Momentum ASX {leg_name} leg, full sample", "coef": coef, "p": p})


def main() -> None:
    print("Milestone 47 tested momentum (US, NSE), low-volatility, and MAX for the Bear+HighVol")
    print("crash-interaction mechanism, but never momentum on ASX -- this project's own cleanest,")
    print("currently-live edge. This milestone closes that gap and re-corrects the resulting")
    print("19-test family, every p-value computed fresh.\n")

    rows: list[dict] = []
    momentum_tests(rows)
    lottery_signal_tests(rows)
    asx_momentum_tests(rows)

    df = pd.DataFrame(rows).dropna(subset=["p"]).sort_values("p").reset_index(drop=True)
    n_tests = len(df)

    bh_reject, bh_adj, _, _ = multipletests(df["p"].values, alpha=ALPHA, method="fdr_bh")
    bonf_reject, bonf_adj, _, _ = multipletests(df["p"].values, alpha=ALPHA, method="bonferroni")
    df["bh_adj_p"] = bh_adj
    df["bh_reject"] = bh_reject
    df["bonf_adj_p"] = bonf_adj
    df["bonf_reject"] = bonf_reject

    print(f"{'=' * 100}\n{n_tests} Bear+HighVol crash-interaction tests, re-corrected with ASX momentum "
          f"included\n{'=' * 100}")
    print(f"{'Test':<40}{'raw p':<10}{'BH-adj p':<12}{'BH sig?':<10}{'Bonf-adj p':<14}{'Bonf sig?':<10}")
    for _, r in df.iterrows():
        print(f"{r['test']:<40}{r['p']:<10.4f}{r['bh_adj_p']:<12.4f}"
              f"{'YES' if r['bh_reject'] else 'no':<10}{min(r['bonf_adj_p'], 1.0):<14.4f}"
              f"{'YES' if r['bonf_reject'] else 'no':<10}")

    n_raw_sig = (df["p"] < ALPHA).sum()
    n_bh_sig = df["bh_reject"].sum()
    n_bonf_sig = df["bonf_reject"].sum()
    print(f"\nOut of {n_tests} tests: {n_raw_sig} significant at raw p<{ALPHA}; "
          f"{n_bh_sig} survive Benjamini-Hochberg; {n_bonf_sig} survive Bonferroni.")


if __name__ == "__main__":
    main()

"""
Milestone 47 (line Y) responds to an open observation this project's own
Milestone 41 left unaddressed: the multiple-testing correction there
covered exactly one family, the 21 "does signal X replicate on market Y"
tests -- but this project has run many other kinds of significance tests
since (the crash-cost interaction sweep, Milestone 42; the VaR/CVaR
profile, Milestone 43; and, most comparably, the Bear+HighVol
crash-mechanism regime-interaction test, run repeatedly across Milestones
16-18, 20, and 46 on different signals, markets, and eras).

Before building anything, this milestone makes an explicit methodological
choice most literal readings of "build a fuller inventory and correct
everything" would skip past: NOT every p-value this project has ever
printed belongs in one corrected family. Milestone 41's own family was
deliberately narrow -- "the one clean, comparable family this project's
own methodology supports" -- and for good reason: a decade-by-decade
breakdown (Milestones 26-28, 34) or a sub-period check (Milestone 38) is
a LOCALIZATION test, conditional on an effect Milestone X *already*
flagged as worth explaining -- not a fresh, independent "is this real"
discovery claim. Folding five decade-breakdown p-values from an
already-significant pooled result into the same corrected family as 21
independent replication attempts would inflate the family with tests
that are not exchangeable with the others, violating the assumption
multiple-testing correction depends on and manufacturing false precision,
not adding rigor.

What DOES belong in a second, comparable family: the Bear+HighVol
regime-interaction test itself, which this project has applied, with the
exact same construction (`build_regime_dummies` + HAC regression +
interaction term), as an independent "is there a real crash-conditional
effect here" question, to momentum (three eras, two markets, two legs)
and, as of Milestone 46, to low-volatility and MAX (two markets, three
legs). Every one of those is a comparable, freestanding hypothesis test,
not a conditional follow-up on an already-established result. This
milestone assembles all 17 of them, computed fresh, and applies the same
Benjamini-Hochberg and Bonferroni corrections Milestone 41 used.

Reuses build_regime_dummies, hac_regression, build_hedged_return_series,
run_decile_backtest, and market_proxy unchanged.

Run: python investigations/crash_mechanism_multiple_testing.py
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
from investigations.momentum_crash_significance import build_regime_dummies, hac_regression
from investigations.short_leg_beta import market_proxy
from signals.low_volatility import low_volatility_score
from signals.max_effect import max_effect_score
from signals.momentum import momentum_12_1

HAC_LAGS_DAILY = 21
N_DECILES = 5
ALPHA = 0.05
BREAK_DATE = pd.Timestamp("2008-09-01")


def interaction_pvalue(hedged: pd.Series, regimes: pd.DataFrame) -> tuple[float, float, int]:
    era = hedged.dropna()
    if len(era) < 20:
        return float("nan"), float("nan"), len(era)
    era_regimes = regimes.reindex(era.index)
    interaction = era_regimes["high_vol"] * era_regimes["bear"]
    X = pd.DataFrame({
        "high_vol": era_regimes["high_vol"],
        "bear": era_regimes["bear"],
        "high_vol_x_bear": interaction,
    })
    fit = hac_regression(era, X, lags=HAC_LAGS_DAILY)
    return float(fit.params["high_vol_x_bear"]), float(fit.pvalues["high_vol_x_bear"]), len(era)


def momentum_tests(rows: list[dict]) -> None:
    us_prices = load_us_kaggle_mirror()
    us_market = market_proxy(us_prices)
    us_regimes = build_regime_dummies(us_prices)
    us_signal = momentum_12_1(us_prices)
    us_result = run_decile_backtest(us_prices, us_signal, n_deciles=N_DECILES, cost_bps=10.0,
                                     min_names_per_side=2)
    us_reb = us_result.turnover_by_month.index

    for leg_name, leg_returns in [("long", us_result.daily_returns_long),
                                   ("combined", us_result.daily_returns_gross)]:
        hedged, _ = build_hedged_return_series(leg_returns, us_market, us_reb)
        for era_name, era_series in [
            ("full sample", hedged),
            ("pre-2008-09", hedged[hedged.index < BREAK_DATE]),
            ("post-2008-09", hedged[hedged.index >= BREAK_DATE]),
        ]:
            coef, p, n = interaction_pvalue(era_series, us_regimes)
            rows.append({"test": f"Momentum US {leg_name} leg, {era_name}", "coef": coef, "p": p, "n": n})

    nse_prices = load_nse_github_mirror()
    nse_market = market_proxy(nse_prices)
    nse_regimes = build_regime_dummies(nse_prices)
    nse_signal = momentum_12_1(nse_prices)
    nse_result = run_decile_backtest(nse_prices, nse_signal, n_deciles=N_DECILES, cost_bps=10.0,
                                      min_names_per_side=2)
    nse_reb = nse_result.turnover_by_month.index
    for leg_name, leg_returns in [("long", nse_result.daily_returns_long),
                                   ("combined", nse_result.daily_returns_gross)]:
        hedged, _ = build_hedged_return_series(leg_returns, nse_market, nse_reb)
        coef, p, n = interaction_pvalue(hedged, nse_regimes)
        rows.append({"test": f"Momentum NSE {leg_name} leg, full sample", "coef": coef, "p": p, "n": n})


def lottery_signal_tests(rows: list[dict]) -> None:
    configs = [
        ("Low-volatility", low_volatility_score, "US", load_us_kaggle_mirror),
        ("Low-volatility", low_volatility_score, "ASX", load_asx_github_mirror),
        ("MAX effect", max_effect_score, "US", load_us_kaggle_mirror),
    ]
    for signal_name, score_fn, market_name, loader in configs:
        prices = loader()
        market = market_proxy(prices)
        regimes = build_regime_dummies(prices)
        signal = score_fn(prices)
        result = run_decile_backtest(prices, signal, n_deciles=N_DECILES, cost_bps=10.0, min_names_per_side=2)
        reb_dates = result.turnover_by_month.index
        for leg_name, leg_returns in [
            ("long", result.daily_returns_long),
            ("short", result.daily_returns_short),
            ("combined", result.daily_returns_gross),
        ]:
            hedged, _ = build_hedged_return_series(leg_returns, market, reb_dates)
            coef, p, n = interaction_pvalue(hedged, regimes)
            rows.append({"test": f"{signal_name} {market_name} {leg_name} leg", "coef": coef, "p": p, "n": n})


def main() -> None:
    print("Milestone 41 corrected exactly one family: the 21 'does X replicate' tests. This")
    print("milestone builds a second, comparable family -- every Bear+HighVol crash-mechanism")
    print("interaction test this project has ever run (momentum across eras/markets/legs, plus")
    print("Milestone 46's low-volatility/MAX tests) -- rather than folding in decade-breakdown")
    print("or sub-period checks, which are conditional localizations of an already-flagged")
    print("effect, not independent discovery claims, and don't belong in the same family.\n")

    rows: list[dict] = []
    momentum_tests(rows)
    lottery_signal_tests(rows)

    df = pd.DataFrame(rows).dropna(subset=["p"]).reset_index(drop=True)
    n_tests = len(df)
    bh_reject, bh_adj, _, _ = multipletests(df["p"].values, alpha=ALPHA, method="fdr_bh")
    bonf_reject, bonf_adj, _, _ = multipletests(df["p"].values, alpha=ALPHA, method="bonferroni")
    df["bh_adj_p"] = bh_adj
    df["bh_reject"] = bh_reject
    df["bonf_adj_p"] = bonf_adj
    df["bonf_reject"] = bonf_reject
    df = df.sort_values("p").reset_index(drop=True)

    print(f"{'=' * 108}\n{n_tests} Bear+HighVol crash-interaction tests, one pre-registered family\n{'=' * 108}")
    print(f"{'Test':<38}{'coef':<12}{'raw p':<10}{'BH-adj p':<12}{'BH sig?':<10}{'Bonf-adj p':<14}{'Bonf sig?':<10}")
    for _, r in df.iterrows():
        print(f"{r['test']:<38}{r['coef']:<+12.5f}{r['p']:<10.4f}{r['bh_adj_p']:<12.4f}"
              f"{'YES' if r['bh_reject'] else 'no':<10}{min(r['bonf_adj_p'], 1.0):<14.4f}"
              f"{'YES' if r['bonf_reject'] else 'no':<10}")

    n_raw_sig = (df["p"] < ALPHA).sum()
    n_bh_sig = df["bh_reject"].sum()
    n_bonf_sig = df["bonf_reject"].sum()
    print(f"\nOut of {n_tests} tests: {n_raw_sig} significant at raw p<{ALPHA} "
          f"(chance alone would produce ~{n_tests * ALPHA:.1f} false positives at this rate); "
          f"{n_bh_sig} survive Benjamini-Hochberg; {n_bonf_sig} survive Bonferroni.")


if __name__ == "__main__":
    main()

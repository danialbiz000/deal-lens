"""
Milestone 31 turns this project's own audit discipline (line D) on its
flagship practical deliverable: `signals/composite.py`, the equal-weighted
three-signal "Behavioral Mispricing Score" that Part VI.1 of the PDF guide
presents as the project's investment framework. That composite has been
unchanged since the project's first milestone -- built before any of the
subsequent 30 milestones of evidence existed. By this project's own
accumulated findings:

  - momentum: the one demonstrated, repeatedly-stress-tested real edge
    (US pre-2008-09, independently replicated on ASX).
  - 52-week-high: no demonstrated skill (Milestones 6-7), confirmed on a
    third market to be momentum's own edge wearing a different
    construction where it does show alpha (Milestones 23-25).
  - short-term reversal: no demonstrated skill anywhere, its apparent edge
    traced to a 2-4-stock survivorship artifact (Milestone 16).

An equal-weighted blend of one real signal and two with no demonstrated
independent skill is, by the project's own evidence, not obviously the
right way to build a practical score -- worth testing directly rather than
leaving the composite unexamined while every individual signal has been
tested repeatedly. This milestone runs the out-of-sample hedge + HAC test
this project uses everywhere else on three variants: the current
equal-weighted composite, a momentum-only "composite" (weight 1 on
momentum, 0 on the other two), and, for context, each retracted component
alone -- on the two markets where momentum's edge is actually confirmed
(US, ASX).

Reuses run_decile_backtest, build_hedged_return_series, check_plain_alpha,
and market_proxy unchanged.

Run: python investigations/composite_score_evidence_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, for sibling packages

from backtest.engine import run_decile_backtest
from backtest.metrics import annualized_return
from data.loaders import load_asx_github_mirror, load_us_kaggle_mirror
from investigations.beta_hedged_backtest import build_hedged_return_series
from investigations.momentum_crash_mechanism_nse import check_plain_alpha
from investigations.short_leg_beta import market_proxy
from signals.composite import composite_score
from signals.momentum import momentum_12_1

MARKETS = {
    "US Kaggle mirror": load_us_kaggle_mirror,
    "ASX (Australia)": load_asx_github_mirror,
}


def momentum_only_score(prices):
    return composite_score(prices, weights={"momentum": 1.0, "high_52w": 0.0, "reversal": 0.0})


VARIANTS = {
    "current equal-weighted composite (momentum + 52w-high + reversal)": composite_score,
    "evidence-weighted: momentum only": momentum_only_score,
    "momentum alone (signals/momentum.py directly, not via composite)": lambda p: momentum_12_1(p),
}


def run_variant(name: str, variant_name: str, signal_fn, prices, market) -> None:
    signal = signal_fn(prices)
    result = run_decile_backtest(prices, signal, n_deciles=5, cost_bps=10.0, min_names_per_side=2)
    reb_dates = result.turnover_by_month.index
    if len(reb_dates) == 0:
        print(f"\n  {variant_name}: no usable rebalances")
        return
    hedged, beta_used = build_hedged_return_series(result.daily_returns_gross, market, reb_dates)
    hedged = hedged.dropna()
    raw_ann = annualized_return(result.daily_returns_gross.dropna())
    print(f"\n  {variant_name}:")
    print(f"    raw ann.ret (unhedged) = {raw_ann:+.2%}, mean beta={beta_used.mean():.3f}")
    check_plain_alpha(f"    hedged combined book", hedged, reb_dates)


def main() -> None:
    for market_name, loader in MARKETS.items():
        prices = loader()
        market = market_proxy(prices)
        print(f"\n{'=' * 90}\n{market_name}\n{'=' * 90}")
        for variant_name, signal_fn in VARIANTS.items():
            run_variant(market_name, variant_name, signal_fn, prices, market)


if __name__ == "__main__":
    print("Does the current equal-weighted 3-signal composite (built before any of this")
    print("project's 30 milestones of evidence existed) still make sense given that evidence --")
    print("or does an evidence-weighted (momentum-only) version perform better, out-of-sample-hedged?")
    print("Newey-West (HAC) standard errors. *** p<0.01  ** p<0.05  * p<0.10")
    main()

# Behavioral Finance Research Project

> **New to this project?** `docs/behavioral_finance_guide.pdf` is a plain-language
> companion guide (English) covering everything below with examples, psychology, and
> the full milestone-by-milestone decision log — no quant-finance background assumed.
> Regenerate it with `python docs/build_guide.py` after any milestone that changes the
> findings; the PDF states its own "as of" scope, this README is the always-current
> source if the two ever drift.

## Research question

Markets are conventionally modeled as (weak-form to semi-strong-form) informationally
efficient, populated by rational, expected-utility-maximizing agents. Two large, related
bodies of evidence complicate that assumption:

1. **Sophisticated, model-driven institutions have blown up precisely because their models
   assumed rational, well-behaved markets** — stable correlations, roughly normal return
   distributions, and ample liquidity — and those assumptions failed exactly when panic,
   herding, and forced deleveraging by *other* rational-seeming actors took over
   (Long-Term Capital Management, 1998; the "Quant Quake," August 2007; Amaranth Advisors,
   2006).
2. **Other funds have built durable strategies on the opposite premise** — that investors
   systematically misprice securities because of identifiable cognitive biases (anchoring,
   overreaction/underreaction, overconfidence, herding) — and have run those strategies
   profitably for decades (Fuller & Thaler Asset Management, LSV Asset Management, and
   factor-based managers such as AQR whose factors have partly behavioral explanations).

This project asks two concrete, falsifiable sub-questions:

- **Q1 (diagnosis).** Can we quantify *why* rational-market models fail under stress — i.e.,
  show mechanically how a risk model calibrated on "normal" historical correlations and
  Gaussian-ish return assumptions underestimates tail risk once fear-driven, correlated
  selling ("flight to quality") sets in?
- **Q2 (exploitation).** Do well-documented behavioral pricing anomalies (momentum,
  52-week-high anchoring, short-term reversal) produce a measurable, risk-adjusted return
  premium net of reasonable transaction costs, over a long, multi-regime sample — the same
  kind of edge that funds like Fuller & Thaler and LSV have built businesses around?

## Why this is a quant research project, not just a literature review

Both questions are testable with public data and standard tooling. This repo therefore
ships **runnable code**, not just narrative:

- `risk_simulation/fat_tails_vs_normal.py` — answers Q1. Fully self-contained (no external
  data dependency), runs immediately, and produces real numbers: how badly a Gaussian VaR
  model underestimates a 1-in-1000-day loss when the true data-generating process has fat
  tails and a correlation regime shift, calibrated loosely on what happened to LTCM's book
  in autumn 1998.
- `signals/`, `backtest/`, `data/loaders.py` — answer Q2. A momentum / 52-week-high /
  short-term-reversal signal library plus a decile long-short backtest engine (Sharpe,
  max drawdown, turnover, transaction-cost drag), run end to end against real daily price
  history (see "Empirical results" below).

## Important limitation of this environment — read before trusting any Q2 numbers

This code was written and committed from a sandboxed session whose outbound HTTPS is
restricted by an egress proxy to an allowlist. Verified directly (curl against each host):
Yahoo Finance, Stooq, SEC EDGAR, and FRED are all **blocked**; `api.github.com` and
`raw.githubusercontent.com` are **reachable**. That asymmetry shapes what's genuinely
validated here versus what still needs to be run elsewhere:

- **Q1 (risk simulation) is a real, executed result.** `risk_simulation/fat_tails_vs_normal.py`
  is a Monte Carlo study with no external data dependency, so its numbers are genuine, not
  illustrative. As executed (500,000 simulated days, seed=7; see that file for exact
  parameters):

  ```
  99.0% tail: Gaussian VaR 7.67% of book  vs  true VaR 8.15%  (1.06x)   |  CVaR 1.35x
  99.9% tail: Gaussian VaR 10.19% of book vs  true VaR 13.26% (1.30x)  |  CVaR 1.65x
  worst single day in the 500,000-day sample: 58.90% of book
  ```

  The underestimation is modest right at the 99% line (that quantile sits near the
  boundary between the calm and stress regimes in this parameterization) but compounds
  fast deeper into the tail — at 99.9% the "true" VaR is 30% higher than the Gaussian
  model says, and the true expected shortfall (CVaR) is 65% higher. That gap, multiplied
  by 25:1+ balance-sheet leverage, is the mechanical core of why LTCM's risk model didn't
  see 1998 coming: it wasn't wrong about "normal" days, it was wrong about how fast
  correlation and volatility move together once everyone runs for the same exit at once.

- **Q2 (signal backtest) is also now a real, executed result — but on a different universe
  than the code defaults to.** `data/loaders.py`'s primary path (`load_price_history`,
  Yahoo/Stooq, US large-caps) is still unexercised here — that provider is blocked. But
  `load_nse_github_mirror()` pulls a real daily-OHLCV dataset for 48 NSE (India)
  large/mid-cap companies, 2000–2021, from a GitHub-hosted CSV (reachable through the
  allowlist), and the full decile-backtest pipeline has been run against it end to end.
  See "Empirical results (NSE India, 2000–2021)" below for the numbers and
  "Data provenance" for exactly what this dataset is and isn't a substitute for.
  **The original US-universe path is still unvalidated** — run it yourself with normal
  internet access before trusting any number that comes out of it specifically.

This distinction matters a lot for a project whose entire thesis is "don't trust a model's
output just because it looks rigorous" — so the same discipline applies here: know which
number in this repo was actually computed versus which is still a claim to be checked.

## Empirical results (NSE India, 2000–2021)

Ran the full pipeline — `load_nse_github_mirror()` → each signal → `run_decile_backtest`
— against 48 companies, 5,306 trading days, monthly rebalance, 10 bps/unit-turnover cost.
With only 48 names, a 10-decile split puts ~5 names per side (noisy); a 5-quintile split
(~10 names/side) is also reported for the composite and each individual signal, since it's
the more defensible bin size for this universe:

| Signal | Split | Gross ann. return | Gross Sharpe | Net Sharpe | Max drawdown |
|---|---|---|---|---|---|
| Composite (all 3) | deciles | −3.59% | 0.01 | −0.03 | −74.3% |
| Composite (all 3) | quintiles | −1.33% | 0.05 | 0.00 | −63.2% |
| 12-1 momentum only | quintiles | −1.73% | 0.04 | 0.01 | −60.8% |
| 52-week-high only | quintiles | **−13.71%** | **−0.51** | −0.54 | **−97.1%** |
| Short-term reversal only | quintiles | **+4.46%** | **0.30** | 0.22 | −64.1% |

**Honest reading, not a cherry-picked one:**

- **No edge, on this universe, for momentum or the blended composite.** Sharpe ≈ 0 gross,
  slightly negative net of costs. Plausible explanation: these are 48 large, heavily
  analyst-covered blue chips — exactly the segment where underreaction-driven anomalies are
  typically weakest in the literature (they're documented as stronger in smaller,
  less-covered names). That's a real result, not a bug: it argues against over-trusting the
  composite score on a large-cap-only universe, which is directly relevant to how
  `FRAMEWORK.md` says the score should be used (a tilt, not a standalone strategy).
- **The 52-week-high signal was actively harmful here, and it isn't just crash-driven.**
  Checked directly: excluding both the 2008 GFC (Jan 2008–Jun 2009) and the 2020 COVID
  crash (Feb–Jun 2020) windows entirely, the strategy's Sharpe outside those windows is
  still −0.46 (cumulative return −90% ex-crash vs. −53% return realized *during* the crash
  windows alone) — so this is not simply "it got run over twice by tail events," it lost
  money persistently. See "Replication on a second market" and "Investigating the
  52-week-high result" below for how far this was chased down.
- **Short-term reversal is the one signal that actually worked, gross and net of costs —
  as understood at this point in the project.** Consistent with reversal being one of the
  more robust anomalies in the academic literature, plausibly because it's closer to a
  liquidity-provision premium than a pure behavioral bet. **Update (Milestone 8): this does
  not survive a beta check either.** See "Does the reversal edge survive a beta check too?"
  below — like the 52-week-high signal, this positive-looking Sharpe turns out to be mostly
  market-beta exposure and noise, not a demonstrated edge, once tested the same way the
  52-week-high signal's *losses* were.

**Reproduce this**: `python -m data.loaders` downloads and caches the dataset (parquet,
gitignored), then the "How to run" snippet below runs the same backtests.

## Replication on a second market (US, Kaggle mirror)

Same pipeline, same 30-name large-cap universe as the original `DEFAULT_UNIVERSE`
(`load_us_kaggle_mirror()`), a different GitHub-hosted mirror (see "Data provenance: the
US Kaggle mirror" below), 1970–2017 depending on each company's listing date:

| Signal | Split | Gross annual return | Gross Sharpe | Net Sharpe | Max drawdown |
|---|---|---|---|---|---|
| Composite (all 3) | deciles | +0.55% | 0.16 | 0.13 | −91.7% |
| Composite (all 3) | quintiles | +2.99% | 0.25 | 0.21 | −79.6% |
| 12-1 momentum only | quintiles | **+5.72%** | **0.34** | **0.32** | −88.4% |
| 52-week-high only | quintiles | **−13.98%** | **−0.29** | −0.32 | **−99.9%** |
| Short-term reversal only | quintiles | −0.68% | 0.13 | 0.07 | −83.0% |

**What replicates and what doesn't, comparing to NSE:**

- **The 52-week-high (anchoring) signal loses money in both markets.** This is the one
  result that held up unchanged: actively harmful, large drawdown, in a 48-name Indian
  large-cap sample *and* a 30-name US large-cap sample spanning a completely different
  macro history (multiple US recessions, the 1970s stagflation era for the oldest names,
  the dot-com crash, 2008 — not just one secular bull market). That cross-market, cross-era
  consistency is exactly what "Investigating the 52-week-high result" below tests directly.
- **Momentum does *not* replicate the same way — it flips sign.** Roughly flat/slightly
  negative on NSE, a real positive net-of-cost edge (Sharpe 0.32) on the US mirror. This is
  actually closer to the mainstream academic finding (momentum is one of the more robust,
  widely-replicated anomalies in US equities specifically), which raises the opposite
  concern from before: the NSE result for momentum may be the one that doesn't generalize,
  not the US one. **Update (Milestone 8): this US momentum result held up, and then some** —
  it's the only signal in this entire project whose edge survives a full beta-adjusted
  significance test (see "Does the reversal edge survive a beta check too?" below).
- **Short-term reversal does *not* replicate either — it's much weaker here** (Sharpe 0.07
  net vs. 0.22 net on NSE). So of the three individual signals, *none* of them showed a
  consistent, cross-market edge in the same direction except the negative one (52-week-high).
  That is itself a finding: a signal-selection process that only looked at one market (NSE)
  would have wrongly concluded reversal was the reliable edge and momentum was dead — the
  opposite of what a US-only study would have concluded. **Update (Milestone 8): reversal's
  NSE "edge" didn't survive a beta check either — it's now retracted, not just
  non-replicating.** **Universe/market choice changes
  which anomaly looks real; decomposition (Part V.3 in the PDF guide) is necessary but not
  sufficient — cross-market replication matters too.**

## Investigating the 52-week-high result: is it a value/growth confound?

Milestone 2 flagged two candidate explanations for why the anchoring signal loses money:
generic momentum-crash risk, or a value/growth confound specific to a secular bull market
(shorting "far from the 52-week high" names might just mean shorting cheap, beaten-down
names that then mean-revert upward, fighting the anchoring thesis with an unrelated value
effect). This was tested directly (`investigations/52w_high_value_confound.py`): build a
simple price-only value proxy (`signals/value_proxy.py`, current price ÷ trailing ~3-year
average price), measure its cross-sectional correlation with the raw 52-week-high score,
then **orthogonalize** the signal against it (date-by-date cross-sectional OLS, regress out
the value component, backtest the residual).

| Market | Corr(52w-high, value proxy) | Raw signal net Sharpe | Value-orthogonalized net Sharpe |
|---|---|---|---|
| NSE (India) | 0.63 | −0.54 | **−0.73** |
| US (Kaggle mirror) | 0.44 | −0.32 | **−0.49** |

**The value/growth confound hypothesis is rejected, in both markets.** The two signals
*are* meaningfully correlated (0.44–0.63), confirming a stock near its 52-week high also
tends to look "expensive" on this simple value proxy — but removing that shared component
made the signal's performance **worse**, not better, in both markets. If the confound
hypothesis had been right, orthogonalizing away the value component should have made the
"pure anchoring" signal look neutral-to-positive; instead it got more negative. Combined
with the cross-market replication above (the loss persists across two very different macro
histories, not just one secular bull run) and the earlier crash-window check (Milestone 2:
the loss isn't concentrated in 2008/2020 either), the remaining, still-untested candidate
explanation — generic momentum-crash risk (Daniel & Moskowitz, "Momentum Crashes," 2016), a
property of "long recent winners" strategies generally, not specific to any one market or
value effect — is now the best-supported explanation of the three, though it has not
itself been directly tested here (that would need, e.g., checking whether the signal's
losses cluster in high-realized-volatility regimes specifically). **Reproduce this**:
`python investigations/52w_high_value_confound.py` (no extra setup beyond the main
`requirements.txt`; takes a few minutes because the orthogonalization loops over every
trading date in both datasets).

## Testing momentum-crash risk directly (Milestone 4)

> **Update (Milestone 5): the formal statistical test below does *not* confirm the
> regime-conditioning mechanism this section describes.** This section is kept as
> written at the time — the pattern-matching genuinely looked this compelling — but
> "Formally testing momentum-crash risk" further down walks it back with real numbers.
> Read that section before treating anything below as confirmed.

Milestone 3 left one candidate explanation for the 52-week-high signal's losses
untested: generic momentum-crash risk (Daniel & Moskowitz, 2016) — a documented property
of "long recent winners, short recent losers" strategies, where the *short* leg (recent
losers, typically higher-beta) can rebound sharply during a market recovery, hurting the
strategy specifically when realized volatility is high and the market has recently been
down. This was tested directly (`investigations/momentum_crash_risk.py`): two regime
indicators were built from the same price data (no external index available) — a
realized-volatility tercile (21-day rolling, annualized) and a trailing-12-month
bull/bear market state, both lagged one day to avoid look-ahead — and the backtest engine
was extended (`backtest/engine.py`, `BacktestResult.daily_returns_long` /
`daily_returns_short`) to report the long leg and short leg's P&L contributions
separately, not just their combined total, so the mechanism (not just the timing) could be
checked.

**Result: strongly consistent with momentum-crash risk, on four independent pieces of
evidence, in both markets.**

| Evidence | NSE (India) | US (Kaggle mirror) |
|---|---|---|
| Sharpe monotonically worsens with realized vol (Low→Mid→High) | −0.22 → −0.41 → −0.78 | −0.11 → −0.27 → −0.43 |
| Sharpe, bull vs. bear trailing-12m state | −0.27 vs. **−1.06** | −0.15 vs. **−1.10** |
| Worst bucket: bear + high-vol ("crash-rebound" setup) | **−1.07 Sharpe, −38% ann.** | **−1.26 Sharpe, −61% ann.** |
| Whole-sample return skewness, combined long-short | −0.66 (left-skewed) | −1.32 (left-skewed) |

**The leg decomposition confirms the mechanism, not just the timing:** in both markets,
the **long leg (buying stocks near their 52-week high) is a genuinely positive,
standalone strategy** — Sharpe 0.45–1.03 across every regime in NSE, 0.65–1.20 in the US
outside bear markets — consistent with the anchoring/underreaction thesis actually working
on the long side. The **short leg (shorting stocks far from their high) is the entire
problem**: uniformly negative (Sharpe −0.6 to −1.1) in every single regime bucket in both
markets, and it's *this* leg's loss that swells in the bear+high-vol bucket (NSE: −19% →
−49% annualized from calmest to worst regime; US: −13% → −62%). The short leg's own return
distribution is right-skewed in NSE (skew +0.13 to +0.40) — the fingerprint of a short
position that loses steadily most of the time and occasionally gets hit by a sharp squeeze
against it, exactly the mechanism the hypothesis describes.

**How hard to lean on this, as understood at the time**: this is pattern-matching against
a well-documented mechanism using real data, not a formal significance test (no t-stats on
the regime differences were computed) and the volatility-tercile cutoffs were set using the
full sample's distribution, which a live version would need to compute on a
rolling/expanding basis instead to avoid look-ahead in the regime *definition* itself. With
that caveat, four independent, mutually consistent signatures across two unrelated markets
looked, at this point in the project, like about as strong a case as this kind of
historical analysis could make short of formal statistics — which is exactly what the next
section adds, and exactly what changes the conclusion. **Reproduce this**:
`python investigations/momentum_crash_risk.py`.

## Formally testing momentum-crash risk (Milestone 5)

The user explicitly asked for the pattern-matching above to be turned into "a statistical
test with proven reliability" before opening a PR. Two upgrades were made
(`investigations/momentum_crash_significance.py`):

1. **Look-ahead-free regime thresholds.** The volatility tercile cutoff is now computed on
   an *expanding* window (each day's "high vol" label uses only volatility data through the
   previous day), not the full sample — fixing the one caveat flagged above.
2. **Formal significance testing**: daily strategy/long-leg/short-leg returns are
   regressed on regime dummies (`high_vol`, `bear`, `high_vol × bear`) and, separately, on
   the volatility-tercile rank, using **Newey-West (HAC) standard errors** (21-trading-day
   lag, the standard correction for serial correlation from monthly-rebalanced holding
   periods — the same style of correction the Daniel & Moskowitz paper itself uses). A
   second version aggregates to **monthly returns at each rebalance** (one observation per
   holding period, HAC lag 6) — the frequency the paper's own tests are run at, and a check
   on whether daily-return noise was swamping a real monthly-level effect either way.

**Result: the specific regime-conditioning mechanism does *not* survive formal testing.
What survives is only the more basic decomposition finding.**

| Return series | Daily: `high_vol×bear` interaction | Monthly: `bear` | Monthly: `vol_rank` |
|---|---|---|---|
| NSE — short leg (where the theory predicts the damage) | p=0.57 | p=0.67 | p=0.09 (**wrong sign**) |
| NSE — long leg | p=0.94 | **p=0.0007**  | **p=0.0046** |
| US — short leg (where the theory predicts the damage) | p=0.65 | p=0.34 | p=0.61 |
| US — long leg | p=0.15 | **p<0.0001** | **p=0.0139** |

(Full coefficient tables, both frequencies, both legs, both the dummy and monotonicity
specifications: `python investigations/momentum_crash_significance.py`.)

**What this means, stated plainly**: the short leg — the one the momentum-crash mechanism
specifically predicts should blow up in high-volatility, bear-market regimes — shows **no
statistically significant regime-conditioning in either market, at either frequency, in
any specification**. The regime effects that *are* statistically significant (bear-state
and volatility-rank coefficients, both highly significant, p<0.01) show up in the **long
leg instead** — which is a much more mundane explanation (a long-biased position carries
positive market-beta exposure and underperforms in bear markets generally) than the
specific "short squeeze on rebounding losers" mechanism the momentum-crash hypothesis
describes. NSE's short leg even has the *wrong-signed* coefficient at the 10% level
(losses shrinking, not growing, as volatility rises) — direct evidence against, not for,
the hypothesis in that specific cut.

**What remains statistically ironclad, across every single specification, both markets,
both frequencies**: the long leg's average daily/monthly return is significantly positive
(p<0.05 daily, p<0.0001 monthly, both markets) and the short leg's is significantly
negative (same). The **decomposition finding — long works, short doesn't — is real and
robust**. The **specific proposed mechanism for *why* the short leg fails is not
confirmed** by this test; it remains a plausible, literature-grounded hypothesis that
looked compelling under simple descriptive splits but did not hold up under multiple-
testing-aware, autocorrelation-corrected regression. With ~24 regime-effect coefficients
tested across both frequencies and markets, seeing 2-4 marginally significant results at
the 5-10% level is within what pure chance would produce — not meaningfully more than a
false-positive rate under a true null.

**Practical implication, as understood at this point**: the long-only recommendation
stands — it rests on the robust decomposition, not on the crash-risk story. But the
project should **not** claim to know *why* the short leg fails. That remains an open
question. This is the project's own "don't trust the reassuring pattern" thesis applied to
its most recent finding about itself, at the point where it mattered most: the pattern
that looked like the best-supported explanation in the whole investigation turned out not
to survive the one test that actually tests it. **Reproduce this**:
`python investigations/momentum_crash_significance.py` (needs `statsmodels`, added to
`requirements.txt`). — **Update (Milestone 6): the next, more basic check found the actual
answer, and it changes the "long-only" recommendation too. Keep reading.**

## Is it just beta? (Milestone 6)

Milestone 5 left the decomposition itself — long leg positive, short leg negative — as the
one statistically solid finding, with no confirmed explanation for *why*. There was one
more basic check that should have come before the exotic behavioral hypotheses, not after
them: **do the two legs simply have different, uncontrolled exposure to the market itself?**
An equal-weighted decile long-short book makes no attempt to match the long and short
baskets' market sensitivity — if "losers" (far from the 52-week high) happen to be
higher-beta stocks than "winners" (near the high), the strategy carries unintended net
market exposure, and in a market with a strongly positive average return over the sample
(both NSE and the US mirror returned ~19–21% annualized over their respective windows),
that alone would produce exactly the pattern observed, with no anchoring or crash story
required.

This was tested directly (`investigations/short_leg_beta.py`): a standard CAPM-style
regression — leg return = alpha + beta × market return — using the same equal-weighted
market proxy as Milestone 5, with the same Newey-West (HAC) correction, at daily and
monthly frequency.

| | NSE daily | NSE monthly | US daily | US monthly |
|---|---|---|---|---|
| Long leg beta (p-value) | +0.84 (p<0.0001) | +0.80 (p<0.0001) | +0.82 (p<0.0001) | +0.75 (p<0.0001) |
| Short leg beta (p-value) | −1.16 (p<0.0001) | −1.19 (p<0.0001) | −1.39 (p<0.0001) | −1.40 (p<0.0001) |
| Combined net beta (p-value) | **−0.32 (p<0.0001)** | **−0.40 (p=0.0007)** | **−0.57 (p<0.0001)** | **−0.70 (p<0.0001)** |
| Long leg alpha (p-value) | p=0.60 | p=0.61 | p=0.76 | p=0.35 |
| Short leg alpha (p-value) | p=0.15 | p=0.65 | p=0.72 | p=0.95 |
| Combined alpha (p-value) | p=0.25 | p=0.42 | p=0.69 | p=0.41 |

**This is the answer.** Every single beta coefficient — 12 of them, both legs plus the
combined book, both markets, both frequencies — is highly significant (p<0.001, all but
one below p=0.0001). Every single alpha — the same 12 cells — is statistically
indistinguishable from zero (p ranges from 0.15 to 0.95). The "losers" basket (short leg)
consistently has a *larger-magnitude* beta than the "winners" basket (long leg) — high
recent losers are higher-beta stocks than recent winners, consistent with the momentum
literature's own description of loser-leg stocks, but the consequence here is purely
mechanical, not behavioral: **the combined long-short book is not market-neutral. It carries
an unintended, statistically significant net short-beta position (−0.32 to −0.70 depending
on market/frequency) — and being structurally short a market that returned ~20% a year is a
completely sufficient explanation for the losses documented in every milestone above,
with no anchoring bias, no crash risk, and no value confound required.**

**This changes the practical recommendation from Milestone 4/5, not just adds a footnote to
it.** "Trade the signal long-only" was based on the long leg's raw average return being
significantly positive (Milestone 5). That's still true — but this test shows that positive
return is consistent with the long leg simply being an 0.75–0.84-beta long position in a
rising market, with **no significant standalone alpha** once that exposure is controlled
for. There is currently **no evidence, anywhere in this project, of genuine stock-selection
skill in the 52-week-high signal, in either direction**, once market beta is properly
accounted for. The corrected, honest recommendation: the signal's long leg is a reasonable
lower-beta way to stay long the market, not a demonstrated source of alpha; anyone wanting
to test for real, beta-independent skill in this signal would need to explicitly
beta-neutralize both legs and re-run this same regression on the beta-hedged residual —
**done next, in Milestone 7 below.**

**The real methodological lesson, stated plainly**: this project spent three milestones
(2, 3, 5) chasing increasingly sophisticated behavioral and statistical explanations —
crash windows, a value/growth confound, formal regime-conditioning significance tests —
before checking the single most basic hygiene check for any long-short equity backtest:
whether the two legs are beta-matched. They weren't, and that omission alone explains
everything the more exotic hypotheses were built to explain. **Rule, now stated in
`FRAMEWORK.md`: check for a beta mismatch between the legs before reaching for a
behavioral explanation, not after.** **Reproduce this**:
`python investigations/short_leg_beta.py`.

## Does real alpha survive an actual beta hedge? (Milestone 7)

Milestone 6 used one full-sample regression coefficient to estimate beta and asked whether
the leftover average return (the intercept) was significantly different from zero. That's
a legitimate test, but it isn't the same as actually trading a beta-hedged version of the
strategy: a single, full-sample beta assumes constant market exposure over 20+ years, which
real betas don't have. This milestone builds and tests the real thing
(`investigations/beta_hedged_backtest.py`): at every monthly rebalance, beta is re-estimated
from only the **trailing 252 trading days** (roughly one year) of the combined book's own
history — strictly out-of-sample, never using data from the period being hedged — and that
beta is used to hedge the *next* month's daily returns by subtracting `beta × market return`
from the strategy's own daily return. This mirrors how a real fund would operationally
hedge: periodic re-estimation, applied forward, no look-ahead.

| | NSE (India) | US (Kaggle mirror) |
|---|---|---|
| Days covered (needs 252d trailing history to start) | 5,142 | 11,417 |
| Rolling hedge beta: mean (std across time) | −0.26 (0.31) | −0.44 (0.50) |
| Correlation of hedged returns with the market | −0.07 | −0.02 |
| Unhedged annualized return / vol / Sharpe (same window) | −14.3% / 23.9% / −0.53 | −14.7% / 33.5% / −0.30 |
| Beta-hedged annualized return / vol / Sharpe (same window) | −7.1% / 22.7% / −0.21 | −7.5% / 31.3% / −0.09 |
| Hedged daily return significantly ≠ 0? | p=0.35 | p=0.45 |
| Hedged monthly return significantly ≠ 0? | p=0.42 | p=0.17 |

**Independent confirmation of Milestone 6, by a stronger method.** The rolling hedge
substantially cuts the strategy's correlation with the market (from the strongly negative
correlation implied by Milestone 6's static betas, down to −0.02 to −0.07) and **roughly
halves the annualized loss** in both markets — consistent with a large share of the
original loss being mechanical beta exposure, not something specific to the "losers"
basket. But even after this real, out-of-sample hedge, **the residual return is not
statistically distinguishable from zero in either market, at either frequency** (all
p-values between 0.17 and 0.45) — there is still no significant alpha, positive or
negative, once market exposure is genuinely (not just statistically) removed.

**Two honest caveats, not swept under the rug.** First, the hedge is imperfect — the
residual correlation isn't exactly zero, and the rolling beta itself is quite unstable over
time (its standard deviation is comparable to or larger than its mean in both markets),
meaning a real hedging program would need frequent rebalancing and would incur hedging
transaction costs this script doesn't model. Second, while building this script a real bug
was caught before any numbers were reported: an early version estimated beta as
`np.cov(...) / np.var(...)`, but `np.cov`'s default degrees-of-freedom (`ddof=1`) doesn't
match `np.var`'s default (`ddof=0`), silently inflating every beta estimate by a factor of
roughly `n/(n-1)` (~0.4% here — immaterial to the conclusion, but a real, textbook
finite-sample bug all the same). Fixed by using `np.polyfit`'s OLS slope instead, and
locked in with a synthetic-fixture test (`tests/test_beta_hedged_backtest.py`) asserting
exact beta recovery on a zero-noise series.

**Reproduce this**: `python investigations/beta_hedged_backtest.py`.

## Does the reversal edge survive a beta check too? (Milestone 8)

Every beta check so far was run on the 52-week-high signal only. But short-term reversal
was this project's *one* positive empirical finding (Milestone 2: "the only signal that
actually worked, gross and net of costs," Sharpe 0.22 net on NSE) — and it was never
re-examined for the exact same uncontrolled-beta artifact that turned out to fully explain
the 52-week-high signal's losses. This milestone applies the identical CAPM-style test
(`investigations/momentum_reversal_beta.py`) to **both** remaining signals — 12-1 momentum
and short-term reversal — long leg, short leg, and combined book, both markets, both
frequencies: 24 alpha tests in total.

**Short-term reversal's "edge" does not survive.** Not one of its 12 alpha tests (2 markets
× 3 legs × 2 frequencies) is significant at conventional levels (all p > 0.10, most p > 0.2).
The positive Sharpe reported in Milestone 2 was — like the 52-week-high signal's loss — a
mix of market-beta exposure and noise, not a demonstrated stock-selection edge. **This
project's one previously "positive" empirical result is retracted along with the negative
one.**

**12-1 momentum tells a genuinely different, more interesting story.** On NSE, momentum
shows essentially no significant alpha either (one marginal hit at the 10% level, long leg
monthly). But on the **US mirror, momentum's long leg and combined book show real,
statistically robust, largely beta-independent alpha**:

| | US long leg | US combined book |
|---|---|---|
| Daily alpha (annualized) | +8.1%/yr, **p<0.0001** | +12.1%/yr, **p=0.004** |
| Monthly alpha (annualized) | +9.2%/yr, **p<0.0001** | +15.3%/yr, **p<0.0001** |
| Beta | ≈+1.0 to +1.1 (long leg) | ≈−0.05 to −0.24, mostly *not* significant |

The combined long-short book's beta is close to zero and, at daily frequency, not
statistically different from zero (p=0.38) — this book is close to genuinely market-neutral
**and** has a large, highly significant positive average return. Unlike the marginal,
scattered hits dismissed as noise in Milestone 5's multiple-testing discussion, this is a
**coherent cluster**: the same signal, the same market, the same direction, significant at
the 1% level or better across both frequencies and both the long leg and the combined book
— a qualitatively different, much less noise-like pattern than an isolated p≈0.03 hit.

**How hard to lean on this.** This is the strongest, most credible finding in the entire
project — but it is one market (the US Kaggle mirror, snapshot ending 2017-11-10), it does
not replicate on NSE, and it has not been checked for the specific decay risk flagged in
this README's own "Explicit limitations" since the project's first commit: momentum was
published by Jegadeesh & Titman in 1993, and momentum's premium is well documented in the
literature to have weakened somewhat post-publication. Whether this specific alpha holds up
in a pre-1994 vs. post-1994 sub-sample split has **not yet been tested** — checked next.

**Reproduce this**: `python investigations/momentum_reversal_beta.py`.

## Has US momentum's alpha decayed since publication? (Milestone 9)

Jegadeesh & Titman published the 12-1 momentum anomaly in the *Journal of Finance* in
March 1993. A large literature (notably McLean & Pontiff, "Does Academic Research Destroy
Stock Return Predictability?", *Journal of Finance*, 2016) documents that anomaly returns
tend to shrink — by roughly 26% after working-paper circulation and ~58% on average after
formal publication — once traders can crowd into a known effect. Milestone 8 found large,
highly significant momentum alpha in the US mirror but never checked whether it was
concentrated in the pre-publication era. This milestone
(`investigations/momentum_publication_decay.py`) splits the same long leg and combined-book
regressions at **1994-01-01** (~1 year after publication) and re-runs them on each half
separately — 251 pre-1994 rebalances vs. 286 post-1994 rebalances, out of 537 total.

| | Long leg, pre-1994 | Long leg, post-1994 | Combined, pre-1994 | Combined, post-1994 |
|---|---|---|---|---|
| Daily alpha (annualized) | +9.8%/yr, **p=0.003** | +6.5%/yr, **p=0.032** | +16.1%/yr, **p=0.011** | +8.6%/yr, p=0.116 (n.s.) |
| Monthly alpha (annualized) | +11.4%/yr, **p=0.0004** | +7.1%/yr, **p=0.041** | +18.6%/yr, **p=0.0008** | +13.1%/yr, **p=0.035** |

**Real, partial decay — exactly the textbook pattern, not full disappearance.** Every cut
shows the alpha shrinking after 1994: the long leg's daily alpha falls by roughly a third
(9.8%→6.5%/yr) and its monthly alpha by roughly two-fifths (11.4%→7.1%/yr); the combined
book's decays by 30-47% depending on frequency. That magnitude of decline lines up closely
with McLean & Pontiff's average post-publication effect across US anomalies generally —
this isn't an unusually large or suspicious decay, it's the expected one. **The alpha
survives in three of four cuts** (long leg, both frequencies; combined book, monthly) but
**loses statistical significance in one** (combined book, daily, p=0.116) — and the
combined book's beta also drifts from indistinguishable-from-zero pre-1994 (p=0.86 daily,
p=0.27 monthly — genuinely market-neutral) to weakly negative post-1994 (p=0.052 daily),
a secondary sign that the strategy's risk profile itself has shifted since the anomaly
became public knowledge.

**Updated conclusion**: this project's one durable finding is now more precisely stated as
*momentum's long leg (and, less robustly, the market-neutral combined book) continued to
carry statistically significant, economically smaller alpha through 2017*, not an
un-decayed anomaly. That is a real, still-standing finding — three of four regression cuts
remain significant at conventional levels in the post-1994 half alone, more than 20 years
after publication — but a meaningfully weaker one than Milestone 8's full-sample numbers
suggested on their own, and the specific "is it dead or does it just work less well"
question this README has flagged since its first commit now has a real, textbook-consistent
answer instead of an open one.

**Reproduce this**: `python investigations/momentum_publication_decay.py`.

## Does the post-1994 alpha survive an actual out-of-sample hedge? (Milestone 10)

Milestone 9's decay split is a real improvement over a full-sample average, but it has the
same limitation Milestone 6's beta regression had before Milestone 7 closed the loop: it
fits one beta **in-sample**, using the whole post-1994 sub-sample's own data, then asks
whether the average residual differs from zero. A real fund cannot do that — it has to
estimate beta from only trailing history and hedge forward. This milestone
(`investigations/momentum_hedged_decay_backtest.py`) reuses Milestone 7's rolling,
out-of-sample beta hedge (re-estimated every monthly rebalance from only the preceding
252 trading days, applied forward, never looking ahead) on the momentum long leg and
combined book, then applies the identical 1994-01-01 split to the resulting **hedged**
daily return series.

| | Long leg, pre-1994 | Long leg, post-1994 | Combined, pre-1994 | Combined, post-1994 |
|---|---|---|---|---|
| Hedged ann. return | +9.62%/yr | +3.29%/yr | +7.93%/yr | **-0.31%/yr** |
| Daily alpha (HAC) | **p=0.0010** | p=0.1485 (n.s.) | **p=0.0244** | p=0.5900 (n.s.) |
| Monthly alpha (HAC) | **p=0.0017** | p=0.1886 (n.s.) | p=0.0506 (n.s., borderline) | p=0.5049 (n.s.) |

**This is a further, sharper correction, not a confirmation of Milestone 9's "survives in
three of four cuts" framing.** Once beta is estimated the way a real fund would have to
estimate it — from trailing data only, re-hedged every month, never fit on the same period
being tested — the post-1994 alpha is **not statistically distinguishable from zero in
either leg**, at either frequency. The combined book's hedged post-1994 average return is
outright negative (-0.31%/yr). Pre-1994, the same methodology strongly confirms alpha in
both legs (p≤0.025 in three of four cuts), so the hedge itself isn't simply too noisy to
detect a real effect when one is present — it detects it clearly pre-1994 and finds nothing
post-1994. The gap between Milestone 9's "three of four cuts survive" and this milestone's
"none survive" is entirely explained by the in-sample vs. out-of-sample distinction: an
in-sample regression can fit the specific quirks of the post-1994 data it's being tested
against, while a rolling hedge estimated only from prior data cannot.

**Updated conclusion, superseding Milestone 9's**: US 12-1 momentum's alpha was real and
strong before 1994 and has **not** been demonstrated to survive, in a form an actual fund
could have traded, in the more-than-two-decades since. The project's single most credible
candidate for a genuine, durable edge does not clear the bar once tested with the same
standard of rigor (an actual rolling out-of-sample hedge, not a static or per-era
regression coefficient) that Milestone 7 already established as this project's own
required standard. This does not mean the original Milestone 8 finding was wrong for its
sample — the full-sample and pre-1994 alpha are both real and robust — it means the
finding cannot currently be sized as a forward-looking edge without further work (e.g., a
faster-adapting hedge, or evidence the post-1994 weakness is itself a regime effect rather
than permanent decay).

**Reproduce this**: `python investigations/momentum_hedged_decay_backtest.py`.

## Is the post-1994 null result a crash artifact, a hedge artifact, or genuine decay? (Milestone 11)

Milestone 10 explicitly flagged two open questions rather than treating the null result as
final: whether the post-1994 weakness is concentrated in a specific regime — most plausibly
the well-documented 2009 "momentum crash" (Daniel & Moskowitz, 2016, *Review of Financial
Studies*, where past losers momentum strategies were underweighting rebounded violently
during the 2008-crisis recovery) — and whether the null result depends on the specific
252-trading-day rolling hedge window Milestones 7/10 happened to use. This milestone
(`investigations/momentum_decay_regime_analysis.py`) runs three checks on the post-1994
hedged return series to answer both.

**Check 1 — sub-period breakdown.** Splitting post-1994 into five multi-year eras (1994-99,
2000-02, 2003-07, 2008-09, 2010-17) and computing the hedged annualized return and HAC alpha
in each shows a declining trend, not a single bad episode with a recovery: the long leg's
hedged excess return runs +6.5%, +10.5%, +3.4%, -3.7%, then **+0.1%** in 2010-2017 — the
most recent nine years show essentially zero excess return, well after the 2009 crash was
over. The combined book shows the same pattern, ending at **-5.1%** in 2010-2017. No single
era shows individually significant alpha (each has too few observations for the power to
detect an effect this size on its own), but the trend across eras argues for ongoing decay,
not a shock-and-recovery.

**Check 2 — explicit crash-window exclusion (March-August 2009).** The crash window itself
was severe — the combined book lost 40.2% cumulatively in those 128 trading days alone.
Excluding it from the post-1994 sample: the **long leg's** daily alpha p-value improves from
0.149 to **0.095** (crossing the 10% threshold — the crash meaningfully hurt this leg's
result), but the **combined book's** p-value only improves from 0.590 to 0.334, nowhere near
significance. **The crash is a real contributing factor for the long leg, but does not
explain the combined book's null result, and the continued weakness through 2010-2017 (well
after the crash) shows the effect is not fully explained by a single 2009 episode either
way.**

**Check 3 — hedge rolling-window robustness (126d / 252d / 378d).** Re-running Milestone
10's entire hedge with three different lookback windows: pre-1994 alpha is strongly
significant at every window tested (p≤0.017, long leg p≤0.001) and post-1994 alpha is
non-significant at every window tested (p ranges 0.14-0.66 across both legs and all three
windows). **The null result is not an artifact of the specific 252-day window** — it holds
whether beta is estimated from six months or a year and a half of trailing data.

**Updated conclusion**: this deeper investigation does not reverse Milestone 10's finding —
if anything it strengthens it. The 2009 momentum crash was real and severe and meaningfully
affected the long leg's result, but it is not sufficient on its own to explain either leg's
post-1994 null result, and the hedge's design choice is not driving it either. The era-by-era
trend (positive and shrinking through the 2000s, negative through the crisis, and still flat
or negative for the nine years since) is the signature of genuine, ongoing decay rather than
one bad shock the strategy simply hasn't yet recovered from.

**Reproduce this**: `python investigations/momentum_decay_regime_analysis.py`.

## Is "real pre-1994, decayed since" specific to momentum, or market-wide? (Milestone 12)

Milestones 9-11 built a specific toolkit — a rolling, out-of-sample beta hedge split at
1994-01-01 — and applied it only to momentum, because momentum was the one signal with
significant full-sample alpha worth investigating. But the 52-week-high and short-term
reversal signals were both declared dead using a *full-sample* beta-adjusted regression
(Milestones 6-8), which would hide the exact same pattern found for momentum: real,
significant alpha in an early era, averaged down to statistical noise by a later decayed
era. This had never been checked, because there was no reason to look for a decay pattern in
signals that already looked dead on average. This milestone
(`investigations/all_signals_decay_analysis.py`) applies the identical pre/post-1994
out-of-sample hedge to **all three** US signals — not to re-answer an already-settled
question (NSE momentum's full-sample null was already established in Milestone 8, so
re-running the hedge there would add nothing), but to ask a genuinely new one: is the decay
pattern unique to momentum, or a broader feature of the US market?

| Signal | Leg | Pre-1994 ann. ret / p | Post-1994 ann. ret / p |
|---|---|---|---|
| 12-1 momentum | long leg | +9.62%/yr, **p=0.001** | +3.29%/yr, p=0.149 |
| 12-1 momentum | combined | +7.93%/yr, **p=0.024** | -0.31%/yr, p=0.590 |
| 52-week-high | long leg | -0.21%/yr, p=0.704 | -2.06%/yr, p=0.468 |
| 52-week-high | combined | -8.46%/yr, p=0.776 | -6.68%/yr, p=0.401 |
| Short-term reversal | long leg | +5.31%/yr, **p=0.046** | +0.25%/yr, p=0.629 |
| Short-term reversal | combined | -0.41%/yr, p=0.293 | -0.57%/yr, p=0.576 |

**Two genuinely different stories, not one.** The 52-week-high signal shows **no significant
alpha in either era, in any leg** — confirming Milestones 6-7's conclusion that this signal
never had genuine stock-selection skill in either direction; its full-sample "loss" was
uncontrolled beta from the start, not a decayed edge. **Short-term reversal's long leg tells
a different story: it shows the identical decay pattern as momentum** — a real, statistically
significant pre-1994 alpha (+5.31%/yr, p=0.046) that decays completely to noise post-1994
(+0.25%/yr, p=0.629). This was invisible in Milestone 8's full-sample regression, which
averaged the genuine early effect with the decayed later one and correctly found no
full-sample significance — but "no full-sample significance" is not the same claim as "never
had a genuine edge," and this milestone shows reversal's long leg did.

**Updated conclusion, correcting Milestone 8's framing for reversal specifically**: Milestone
8's headline claim — "this project's one previously-reported positive finding [reversal] did
not survive the same scrutiny applied to the negative one" — is accurate for the full-sample
regression it ran, but incomplete: reversal's long leg was never *pure noise*, it was a real,
decayed effect exactly analogous to momentum's, just never tested with the era-split
methodology that only existed starting at Milestone 9. **The "real pre-1994, decayed since"
pattern is not a momentum-specific quirk — it appears in two of this project's three signals'
long legs (momentum and reversal) and is absent from the third (52-week-high, which never had
genuine alpha at all)**, consistent with a market-wide explanation — the same 1990s-2000s
scaling-up of quantitative, cross-sectional equity strategies that this project's own case
studies (LTCM, the 2007 Quant Quake) already document as having transformed US equity
markets' microstructure over exactly this period — rather than an idiosyncratic property of
momentum alone.

**Reproduce this**: `python investigations/all_signals_decay_analysis.py`.

## Quantifying the decay: a continuous rate, not a binary 1994 cut (Milestone 13)

Every decay test so far (Milestones 9-12) used a single, somewhat arbitrary binary split —
1994-01-01, chosen as "~1 year after Jegadeesh & Titman's 1993 publication." That answers
"was there a difference before vs. after this one date," not "how fast did the edge erode,
or when did it actually run out." This milestone
(`investigations/decay_rate_estimation.py`) quantifies the decay directly: for each
signal's out-of-sample-hedged long leg, over the *full* sample (no pre/post split), it
regresses `hedged_return_t = alpha + slope × (years since hedge coverage began) + e_t`
with HAC standard errors — `slope` is a direct, continuously-estimated annual decay rate
with its own p-value, and (alpha, slope) together imply a zero-crossing date: this
project's best point estimate of when the edge actually ran out.

| Signal | alpha (start, ann.) | slope (change/yr) | Implied zero-crossing |
|---|---|---|---|
| 12-1 momentum, long leg | +12.65%/yr, p=0.008 | -0.23%/yr, **p=0.152 (n.s.)** | ill-conditioned (not reliable) |
| Short-term reversal, long leg | +13.46%/yr, p=0.014 | -0.41%/yr, **p=0.026** | 2004-11-22 |

**Momentum's decay is not a smooth line — it does not even pass as one.** The full-sample
linear-trend slope for momentum's long leg is *not* statistically significant (p=0.15
daily, p=0.25 monthly): a single straight line drawn across the whole 1972-2017 hedged
return series is a poor fit, not because the effect didn't decay, but because it didn't
decay *smoothly*. A 5-year rolling-window trajectory shows why: annualized hedged returns
stay consistently strong (roughly +4% to +22%/yr, noisy but never close to zero) all the
way from the 1970s through the window ending January 2008 — including every year of the
supposed "post-1994 decay" period the earlier milestones flagged — and only then drop
sharply, turning negative for every rolling window from 2009 onward. **Splitting explicitly
at September 2008 instead of January 1994 gives a far cleaner separation**: pre-Sept-2008
long-leg alpha is +8.02%/yr, p=0.0005 (n=8,983 days) vs. post-Sept-2008 alpha of -0.56%/yr,
p=0.998 (n=2,309 days, utterly indistinguishable from zero) — a starker divide than the
1994 split produced (p=0.001 pre-94 vs. p=0.149 post-94). **This refines, rather than
contradicts, Milestones 9-11's momentum finding**: the direction (weak/absent in the more
recent era) was right, but describing it as gradual, publication-driven decay since 1994
is not well supported by the data's actual shape. A sudden regime shift around the 2008-09
financial crisis (plausibly the same 2009 momentum crash examined directly in Milestone 11,
or the post-crisis scaling-up of quantitative strategies) is a better-supported story for
*when and how* momentum's edge disappeared than slow 1990s crowding.

**Reversal's decay is closer to the smooth story the publication-decay literature
predicts.** Its full-sample linear trend *is* statistically significant (slope -0.41%/yr
daily, p=0.026; -0.39%/yr monthly, p=0.027), with an implied zero-crossing around
November 2004. The rolling trajectory confirms a genuine decline, though a real one, not a
perfectly straight line: annualized returns fall from a very strong +27%/yr in the late
1970s to negative territory by the mid-1980s, stay negative through the 1990s, then show
an unexplained recovery bump (+6% to +14%/yr) from 2000-2004 before declining again through
the 2010s. The overall downward trend is real and significant, but "smooth, monotonic
decay" oversimplifies a pattern that includes a multi-year partial recovery in the middle.

**Updated conclusion**: quantifying the decay rate, rather than assuming a fixed cutoff,
shows the two signals' declines have genuinely different shapes. Reversal's long leg
decays roughly the way the publication-decay literature describes — a real, continuous,
statistically significant downward trend, crossing zero around 2004. Momentum's long leg
does not: it held essentially flat and strong for 35+ years and then broke sharply around
the 2008-09 financial crisis, a pattern a continuous linear-decay model fits poorly and a
structural-break framing fits well. Treat momentum's weakness as "broke around 2008-09,"
not "has been gradually decaying since 1994" — the earlier milestones' binary split
happened to land on the right side of the qualitative story without correctly identifying
its shape or timing.

**Reproduce this**: `python investigations/decay_rate_estimation.py`.

## A formal structural-break test, not a descriptive comparison (Milestone 14)

Milestone 13's "split at September 2008 instead of 1994" comparison was descriptive: the
break date was chosen *after* looking at momentum's rolling-window trajectory, and testing
"the best of many candidate split dates" is expected to look impressive even under a null
of no true break — a comparison, not a test. This milestone
(`investigations/structural_break_test.py`) runs two properly specified tests instead.

**Method A — a literature-motivated Chow-style test at a single, pre-specified date**
(2008-09-01, motivated externally by Daniel & Moskowitz's (2016) documented 2009
momentum-crash episode, not by inspecting this project's own plot). A single pre-specified
date needs no multiple-testing correction.

**Method B — a Quandt-Andrews-style sup-Wald test that does *not* assume a break date.**
It searches every candidate date in the central 70% of the sample (15% trimmed from each
end, standard Andrews (1993) practice), computes the HAC-robust level-shift statistic at
each one, and takes the maximum — both its value and which date it occurs at. Because
searching many candidates inflates the false-positive rate of a naive comparison, this
project's sandboxed environment (which cannot fetch Andrews' published critical-value
tables) instead builds its own empirical null: fit a no-break model to the real data,
block-bootstrap its residuals (400 draws, 12-month blocks, preserving autocorrelation),
rerun the full candidate search on each synthetic no-break series, and compare the real
maximum statistic to that simulated null distribution.

| | Momentum | Reversal |
|---|---|---|
| Method A: level shift at 2008-09, daily | coef=-9.31%/yr ann., **p=0.026** | coef=-4.02%/yr ann., p=0.337 |
| Method A: level shift at 2008-09, monthly | coef=-9.10%/yr ann., p=0.052 | coef=-3.90%/yr ann., p=0.316 |
| Method B: data-driven best break date | 2010-12-31 | **1980-08-29** |
| Method B: sup\|t\| (bootstrap p-value) | 2.771 (p=0.138, n.s.) | 3.369 (**p=0.048**) |

**Momentum: the specific 2008 hypothesis holds; an unconstrained search does not decisively
confirm it as *the* dominant break.** Method A confirms a real, statistically significant
level shift specifically at the literature-motivated date (p=0.026 daily). But Method B's
unconstrained search finds its single best-fitting break at **December 2010, not September
2008** — 27 months later — and that best-fit statistic is *not* significant once corrected
for having searched ~375 candidate dates (bootstrap p=0.138). **This nuances Milestone 13's
framing**: there is good evidence of weakening tied specifically to the 2008-09 crisis
window, but the data does not decisively pin down one single, dominant structural break —
a specific, externally-motivated hypothesis survives; an unconstrained "find the best break
anywhere" search does not clearly beat noise.

**Reversal: no evidence for an 2008-tied break — but a genuine, significant break turns up
much earlier, around 1980.** Method A finds nothing at 2008 (as expected: Milestone 13
already showed reversal's decline predates the financial crisis by decades). Method B's
unconstrained search finds a significant break (bootstrap p=0.048) at **August 1980** — the
early, sharp decline from the extraordinarily high +27%/yr level-shift of the late 1970s
that Milestone 13's rolling trajectory showed, not a smoothly accumulating multi-decade
slope. **This further refines Milestone 13's "smooth, statistically significant linear
decay" framing for reversal**: part of that significant linear trend is better described as
one sharp early-1980s adjustment than continuous decay across the whole sample.

**Updated conclusion**: neither signal's decline is best described as either a perfectly
smooth trend or a single obvious break once tested formally and correctly for
multiple-testing bias. Momentum shows a real, hypothesis-confirmed weakening at the 2008-09
crisis, but not an unambiguous single structural break when searched for without that prior.
Reversal shows a genuine, statistically significant break, but decades earlier than any
milestone had proposed, complicating rather than confirming the smooth-decay story. Both
results are more conservative and more precisely qualified than any earlier milestone's
framing — consistent with this project's repeated experience that the more rigorous test
usually narrows, rather than confirms, the simpler story that preceded it.

**Reproduce this**: `python investigations/structural_break_test.py`.

## Investigating the mechanism behind the 1980 reversal break — a major correction (Milestone 15)

Milestone 14 found a genuine, statistically significant structural break for reversal
around August 1980, but offered no explanation for the date. At the user's explicit
request, this milestone (`investigations/reversal_1980_break_diagnostics.py`)
investigates the mechanism directly rather than reporting the date and moving on — and
the result substantially revises this project's understanding of reversal's status.

**The universe is severely thin in the 1970s-early 1980s — 2-4 stocks, not a portfolio.**
From 1972 through 1983, the reversal signal's decile "long leg" contains only **2-4
stocks**, drawn from a total universe of just 9-14 names. The underlying universe itself
is a small, hand-picked subset of *today's* largest surviving companies (AAPL, JPM, JNJ,
PG, XOM, KO, PEP, WMT, HD, DIS, CVX, PFE, INTC, VZ, T, MRK, ABT, MCD) backfilled to their
earliest available data — a textbook survivorship-biased sample: every name in this era's
universe is, by construction, a company that *did* go on to become a mega-cap winner by
2017. Any stock that dipped temporarily in the 1970s-80s was, in hindsight, virtually
guaranteed to "bounce back," mechanically inflating an apparent reversal effect that has
nothing to do with genuine investor overreaction.

**A genuine data-quality defect, not previously flagged, compounds the problem.** Scanning
this era for single-day moves exceeding 50% (the usual fingerprint of an unadjusted stock
split) turns up two real anomalies: **WMT** drops 52% on 1974-12-06 and then jumps back
+109% twelve days later on 1974-12-18 (price round-trips from $0.0171 to $0.0082 and back
— consistent with a split-adjustment error that later self-corrects in the raw feed), and
**INTC** jumps +101% on 1972-01-27 and a further +51% on 1972-06-22. These are new,
previously undocumented data-quality issues in the US Kaggle mirror, beyond the general
"not an official source" caveat already in this README's "Data provenance" section.

**The decisive test: does reversal's alpha survive excluding the thinnest years?** No.
Re-running the identical out-of-sample-hedged significance test from a range of start
dates:

| Start date | Reversal ann. ret / p | Momentum (control) ann. ret / p |
|---|---|---|
| 1972-01-01 (full sample) | +2.64%/yr, p=0.068 (already only marginal) | +6.21%/yr, **p=0.0008** |
| 1978-01-01 | -0.59%/yr, p=0.833 | +6.38%/yr, **p=0.0014** |
| 1980-08-29 (the break date itself) | -1.24%/yr, p=0.922 | +6.20%/yr, **p=0.0027** |
| 1985-01-01 | -1.20%/yr, p=0.935 | +5.90%/yr, **p=0.0056** |
| 1990-01-01 | -0.73%/yr, p=0.896 | +5.47%/yr, **p=0.0192** |
| 1995-01-01 | +0.48%/yr, p=0.581 | +3.75%/yr, p=0.121 |

**Reversal's entire positive-alpha claim depends on the unreliable 1972-1977 window and
disappears completely once it is excluded** — from any start date at or after 1978,
including the Method B break date itself, p ranges 0.54-0.96 and the point estimate is
usually slightly negative. **Momentum, run as a control through the exact same thin,
survivorship-biased, partly data-glitched early universe, is unaffected**: it remains
highly significant (p≤0.02) at every start date through 1990, fading only toward the
already-established, externally-motivated 2008-09 territory from 1995 onward. The same
data limitation affects both signals identically; only reversal's finding depended on it.

**Updated conclusion — this reverses, not just refines, earlier milestones' framing for
reversal.** The August 1980 "break" is not evidence of a real 1980 market event: it is the
Quandt-Andrews search correctly detecting that reversal's entire apparent edge lives
inside an unreliable, thin, survivorship-biased, and partly data-glitched early sample
window, with nothing genuine on either side of any split point once that window is
excluded. **The "reversal has genuine pre-2005 alpha" claim carried since Milestone 9
through Milestone 14 should be treated as retracted, not merely decayed or narrowed:
reversal shows no reliably demonstrated edge anywhere in this dataset once the unreliable
years are excluded.** Momentum is unaffected by this correction and, if anything, comes
out more strongly validated: the same diagnostic that broke reversal's finding left
momentum's intact.

**Reproduce this**: `python investigations/reversal_1980_break_diagnostics.py`.

## Does the classic momentum-crash mechanism explain the 2008-09 break? (Milestone 16)

Milestones 13-14 confirmed momentum's long leg broke sharply around September 2008 but
left the *mechanism* unexplained — Milestone 11 checked a fixed calendar window
(March-August 2009) and found it only partially mattered. This milestone
(`investigations/momentum_crash_mechanism_2008.py`) tests the actual, named mechanism
instead of a calendar window: the classic Daniel & Moskowitz (2016) momentum-crash
trigger (past losers snapping back hard in a high-volatility market rebound), using the
same look-ahead-free Bear × High-Volatility regime-interaction regression this project
built and validated in Milestones 5-6 — where it was tested on the 52-week-high signal,
full-sample, and found **not** significant. Applying the identical regression to
momentum's out-of-sample-hedged long leg, split at the same literature-motivated
2008-09-01 date used throughout Milestones 14-15:

| | Pre-2008-09 | Post-2008-09 |
|---|---|---|
| Bear × High-Vol regime frequency | 6.1% of days | 9.1% of days |
| Bear × High-Vol interaction coefficient | -0.00062/day, p=0.424 (n.s.) | **-0.00218/day, p=0.0081** |
| Baseline (non-crash-regime) daily alpha | +0.00038, **p=0.003** (~+9.6%/yr) | +0.00017, p=0.203 (n.s., ~+4.3%/yr) |
| Implied return on a Bear+High-Vol day | ~-11%/yr (n.s.) | **~-37%/yr** |

**The crash mechanism was dormant before 2008 and activated after.** Pre-2008-09, the
Bear × High-Vol interaction is small and not remotely significant (p=0.42) — consistent
with Milestones 5-6's original finding that momentum-crash risk wasn't a real driver of
this project's data. Post-2008-09, the identical interaction term becomes large, negative,
and statistically significant (p=0.008): on the roughly 9% of post-2008 trading days that
are both high-volatility and in a trailing bear-market state, momentum's long leg loses at
an annualized rate around 37%, while its baseline (non-crash) daily alpha has fallen to
statistically indistinguishable from zero. The combined long-short book shows the same
sign and similar magnitude but weaker significance (p=0.21) — consistent with the extra
noise from a still-volatile short leg diluting the signal.

**Updated conclusion**: this gives momentum's 2008-09 structural break a genuine causal
mechanism, not just a confirmed date. The classic momentum-crash dynamic that this
project rejected in Milestones 5-6 (for the 52-week-high signal, full-sample) and that
Milestone 11 found only partially relevant to a fixed 2009 calendar window, turns out to
be real for momentum specifically — but **conditional on era**: dormant through the
pre-crisis decades, then active since. This is consistent with, and adds mechanistic
detail to, the broader post-2008 quant-crowding story already touched on in this
project's own Quant Quake case study — a market where momentum-following capital had
scaled up enough by 2008 for the classic crash dynamic to actually bite.

**Reproduce this**: `python investigations/momentum_crash_mechanism_2008.py`.

## Does the momentum-crash mechanism replicate on NSE? (Milestone 17)

Milestone 16's finding was established on one market. This milestone
(`investigations/momentum_crash_mechanism_nse.py`) tests it on NSE (India) — a market
that lived through the same 2008 global crisis. Before trusting anything here, the
Milestone 15 lesson applies: NSE momentum's decile long leg holds 6-10 names throughout
2000-2021 (vs. the US mirror's notorious 2-4 names in the 1970s-80s), a reasonable
portfolio size, not the thin-universe artifact that sank reversal.

**A genuine methodological gap, closed first.** Milestone 8 tested NSE momentum's alpha
with a single *static* full-sample beta regression and found no significant result. That
is a materially cruder test than the rolling, out-of-sample hedge this project built in
Milestone 7 and has used for every US momentum test since — but it had never been applied
to NSE momentum before. Doing so now:

| | Long leg, daily | Long leg, monthly |
|---|---|---|
| Full sample (2000-2021) | +3.56%/yr, p=0.170 (n.s.) | +4.55%/yr, p=0.168 (n.s.) |
| Pre-2008-09 | -2.82%/yr, p=0.744 (n.s.) | -1.70%/yr, p=0.754 (n.s.) |
| Post-2008-09 | +7.66%/yr, **p=0.044** | +7.94%/yr, p=0.073 (marginal) |

**Full-sample, the more rigorous hedge reaffirms Milestone 8's conclusion** — no
significant NSE momentum alpha, daily or monthly, now on firmer methodological footing.
But a **post-2008-specific signal emerges** that the cruder full-sample test could not
have seen: daily-frequency alpha is significant (p=0.044), monthly is marginal (p=0.073).
This is genuinely new, but should be read as "promising, not confirmed" — this project's
own standard label for exactly this strength of evidence (see Milestone 9) — and comes
with a real caveat: NSE's universe itself grew from ~30 to 48 names over this window, so
part of the post-2008 improvement in the strength of the signal may reflect a less thin,
better-populated cross-section rather than a genuine change in the underlying economics.

**The crash-specific mechanism itself does not replicate.** Applying Milestone 16's exact
Bear × High-Vol regression to NSE: the interaction term is never significant (p=0.96
full-sample, p=0.34 pre-2008, p=0.66 post-2008) — unlike the US, where it activated
sharply post-2008. What NSE *does* show is a plain, unconditional **Bear** effect: the
long leg loses significantly in any trailing bear market (coef=-0.00095/day, p=0.002
full-sample; p=0.001 post-2008), regardless of whether volatility is simultaneously high.
That is a related but mechanistically different pattern from the US's specific
crash-*rebound* dynamic — NSE momentum looks bear-market-sensitive in general, not
crash-rebound-sensitive in particular.

**Updated conclusion**: this is not a repeat of the already-settled "does NSE momentum
work" question — it is two new, honestly-qualified findings. The specific momentum-crash
mechanism confirmed for the US in Milestone 16 is not universal; it does not show up in
NSE the same way, even though NSE lived through the same 2008 crisis. Separately, a more
rigorous re-test surfaced a genuinely new, if still tentative, post-2008 NSE momentum
signal that a cruder test had missed — evidence that this project's own methodology
upgrades are still capable of finding things the earlier, less careful passes did not,
even on a market already checked multiple times.

**Reproduce this**: `python investigations/momentum_crash_mechanism_nse.py`.

## Was the 2008-09 crash mechanism a permanent regime change, or a one-off crisis? (Milestone 18)

Milestone 16 tested the Bear × High-Volatility interaction on the *whole* post-2008-09
block (Sept 2008 through the end of the US mirror's coverage in Nov 2017, n=2,309 days)
and found it significant (p=0.008), reading that as evidence the crash mechanism
"activated" for good after 2008. But that block pools two very different periods: the
acute 2008-09 crisis itself, and eight subsequent years. This milestone
(`investigations/momentum_crash_mechanism_persistence.py`) splits the post-2008-09 block
at 2009-12-31 and re-runs the identical regression on each half separately, to test
whether the crash-regime effect persisted past the crisis or was concentrated in it.

The split immediately surfaces a structural fact this project had not checked before:
**the US mirror's trailing-12-month market return never went negative again after
September 2009**, all the way through the end of its coverage in November 2017 — the 2011
European-debt-crisis selloff and the Aug 2015-Feb 2016 drawdown were sharp but both
recovered within the 252-day lookback before ever registering as a sustained bear state
under this project's own (Milestone 5) definition. Bear+High-Vol regime frequency by
sub-period:

| | Pre-2008-09 | Crisis (2008-09 to 2009-12) | Post-crisis (2010-01 onward) |
|---|---|---|---|
| Trading days | 8,983 | 337 | 1,972 |
| Bear × High-Vol regime frequency | 6.1% | 62.3% | **0.0%** |
| High-Vol × Bear interaction coef (long leg) | -0.00062/day, p=0.42 (n.s.) | +0.00115/day, p=0.26 (n.s.) | *cannot be estimated — no Bear days in this window* |
| High-Vol alone (crisis window) | — | -0.00361/day, **p<0.0001** | — |
| Bear alone (crisis window) | — | -0.00188/day, **p=0.036** | — |

**Two refinements to Milestone 16's framing, not a retraction of its core fact.**
Momentum's long leg still lost heavily during 2008-09 — that empirical fact is
unchanged and confirmed again here. But two things Milestone 16's pooled test could not
show on its own:

1. **There is no evidence of a persisting post-2008 bear-market regime to test.** Because
   the trailing-return bear flag never fired again after September 2009, the "post-2008-09"
   window Milestone 16 tested is, for the interaction term's purposes, entirely carried by
   the 16-month crisis sub-window — the other ~2,000 days post-crisis contribute zero
   Bear+High-Vol observations. Framing this as a standing "post-2008 regime change" was an
   overstatement; the honest description is "active during the 2008-09 crisis, untested
   since, because no comparable bear market has recurred in this sample."
2. **Isolated to the crisis window alone, the specific multiplicative interaction is not
   what's doing the work.** When the regression is run on the crisis's 337 days by
   themselves, the interaction term (`high_vol_x_bear`) is *not* significant (p=0.26 long
   leg, p=0.31 combined) — instead, high volatility alone (p<0.0001) and the bear-market
   flag alone (p=0.036 long leg, p=0.005 combined) each independently explain the losses.
   Milestone 16's pooled significance for the *interaction specifically* came from
   contrasting the crisis window against ~2,000 calm, non-bear post-crisis days as an
   implicit control group — a valid test of "did something change after 2008," but weaker
   evidence for "the interaction, specifically, is the mechanism" than the p=0.008 headline
   number suggested in isolation.

Neither sub-window shows any hedged-alpha significance in the plain daily/monthly check
either (crisis: p=0.84 daily, n=15 months insufficient for HAC; post-crisis: p=0.86 daily,
p=0.57 monthly) — consistent with Milestone 16's original post-2008 baseline-alpha result
(p=0.20, n.s.).

**Updated conclusion**: the 2008-09 break is real and tied to volatility and bear-market
state, but this project has no evidence it is a *standing* feature of the post-2008 world,
because the specific bear-market condition this project uses to define "crash regime" has
not recurred since 2009 in this sample. A risk model built on Milestone 16's finding alone
would be over-claiming "momentum has been crash-exposed since 2008"; the accurate claim is
narrower: "momentum was crash-exposed during the one bear market this sample's post-2008
window actually contains." Whether the mechanism would reactivate in a future bear market
is a hypothesis this data cannot confirm or rule out — there simply hasn't been one to test
against since.

**Reproduce this**: `python investigations/momentum_crash_mechanism_persistence.py`.

## Does the crash-mechanism finding survive different regime-construction choices? (Milestone 19)

Every crash-regime result since Milestone 5 rests on two parameter choices baked into
`build_regime_dummies()`: a 21-trading-day realized-volatility window and a 252-trading-day
(~1-year) trailing-return lookback for the "Bear" flag. Neither had been stress-tested. This
matters more than usual for Milestone 18's finding specifically, because "no bear market
recurred after 2009" is a claim that can only be as robust as the lookback window that
defines "bear market" — a shorter window would register the sharp 2011 and 2015-16
drawdowns that a 1-year lookback smooths away. This milestone
(`investigations/momentum_crash_regime_robustness.py`) reimplements the regime construction
with configurable windows (the original function used by every prior milestone is
untouched) and sweeps a 4×4 grid: volatility windows of 10, 21, 42, and 63 trading days,
crossed with bear-market lookbacks of 126, 189, 252, and 378 trading days — 16 combinations,
each checked two ways: does a Bear regime ever fire after 2010-01-01, and does Milestone
16's "interaction dormant pre-2008-09, significant post-2008-09" pattern still hold.

| | Bear lookback 126d | 189d | 252d (default) | 378d |
|---|---|---|---|---|
| Bear regime fires post-2010? | **Yes** (200 days, 2010-16) | **Yes** (47 days, 2010-16) | No | No |
| M16 pattern replicates (vol=10/21/42/63) | 0/1/0/1 of 4 | 0/1/1/0 | 0/1/1/0 (default: yes) | 0/1/1/1 |

**Milestone 18's "no bear regime since 2009" is not robust to the lookback window — this
is a real qualification, not just a robustness footnote.** At the two shorter, equally
standard lookbacks (126 trading days ≈ 6 months, 189 ≈ 9 months), the trailing-return bear
flag *does* fire after 2010 — 200 days clustered in 2010-11 and 2015-16, and 47 days in the
same years respectively — which is exactly the 2011 European-debt-crisis selloff and the
Aug 2015-Feb 2016 drawdown that Milestone 18 already named as sharp-but-short episodes the
252-day window happened to smooth away. Only at lookbacks of 252 days or longer does the
"no recurrence" claim hold. Milestone 18's finding should be read as conditional on this
project's own 1-year convention, not as a lookback-independent fact about the market.

**The Milestone 16 interaction pattern itself replicates in 8 of 16 combinations — real,
but concentrated in a specific part of the parameter space.** It never holds at the
shortest volatility window (10 days, 0/4 bear-lookbacks) — at that window the pre-2008 era
itself becomes significant in one case, breaking the "dormant before" half of the claim.
It rarely holds at the shortest bear-lookback (126 days, 1/4 vol-windows). But it holds
reliably — 3 of 4 bear-lookbacks — at this project's own default 21-day volatility window
and the adjacent 42-day window, and the default parameter combination (21-day vol, 252-day
bear) that Milestones 16-18 actually used sits squarely inside that reliable region, not at
an edge case cherry-picked to produce significance.

**Updated conclusion**: two different answers for two different claims sharing the same
regime-construction code. Milestone 16's qualitative story — the crash mechanism was quiet
before 2008-09 and active during/after it — is reasonably robust to nearby parameter
choices, failing only at unusually short windows this project never actually used. Milestone
18's stronger, more specific claim — that *no* bear market recurred anywhere in the
post-2009 sample — is fragile: it depends on choosing a bear-lookback of a year or longer,
and a 6- or 9-month lookback, an equally defensible convention, tells a different story.
The honest combined statement is: momentum's crash-regime exposure is confirmed for the
2008-09 crisis under every parameter choice tested, and whether it also showed up in 2011 or
2015-16 is a genuinely open question this project has not yet run — the persistence test
that Milestone 18 ran only under the default window has not been re-run under the windows
where a second bear regime actually exists to test it against.

**Reproduce this**: `python investigations/momentum_crash_regime_robustness.py`.

## Did the crash mechanism reactivate in 2011 or 2015-16? (Milestone 20)

Milestone 19 left one question explicitly open: at bear-market lookbacks of 126 and 189
trading days (~6 and ~9 months), a bear regime *does* recur post-2010 — clustered in
2010-11 (the European debt-crisis selloff) and 2015-16 (the Aug 2015-Feb 2016 drawdown) —
giving 148 and 31 Bear+High-Vol days respectively to actually test the crash mechanism's
persistence against, something Milestone 18's default 252-day lookback could not do at all.
This milestone (`investigations/momentum_crash_mechanism_recurrence.py`) closes that thread:
re-running the Bear × High-Vol interaction regression on the 2010-onward window, under both
alternate lookbacks, with everything else (the 21-day volatility window, the hedge
methodology) unchanged from every prior milestone.

| | Bear lookback 126d | Bear lookback 189d |
|---|---|---|
| Bear+High-Vol days, 2010 onward | 148 (7.5% of era) | 31 (1.6% of era) |
| Interaction coefficient | -0.00172/day, p=0.203 (n.s.) | -0.00143/day, p=0.443 (n.s.) |
| Bear-alone coefficient | +0.00126/day, p=0.226 (n.s.) | **+0.00212/day, p=0.023** |

**The mechanism did not reactivate, under either alternate lookback — and where a coefficient
was significant, it pointed the wrong way for crash risk.** At neither window is the
Bear × High-Vol interaction anywhere near significant post-2010 (p=0.20, p=0.44), despite
now having real bear-regime days to test it against. At the 189-day lookback, the
bear-market main effect *is* significant (p=0.023) — but positive, not negative: momentum's
long leg did somewhat *better*, not worse, during 2010-onward trailing-bear periods, the
opposite sign from both the crisis-era coefficient and what the crash-risk mechanism
predicts. This is not the pattern of a dormant mechanism waking back up; it is closer to no
pattern at all.

**Updated conclusion**: this strengthens, rather than merely leaves open, Milestone 18's
original framing. The crash mechanism is not just *untested* outside the 2008-09 crisis
under this project's default parameters — now that two alternate, equally standard
parameter choices supply real bear-regime days post-2010, the mechanism is *tested and not
found* there. The honest, now-complete statement across Milestones 16, 18, 19, and 20: the
Bear × High-Vol interaction explains momentum's 2008-09 losses specifically, has not
reappeared in either of the two next bear-adjacent episodes this sample contains under any
lookback tested, and a standing "momentum is crash-exposed" risk rule would have been
wrong to apply in both 2011 and 2015-16. Whether it would reactivate in a genuinely severe
future crisis — as opposed to the milder episodes of 2011 and 2015-16 — remains open; this
sample simply has not contained one since 2009.

**Reproduce this**: `python investigations/momentum_crash_mechanism_recurrence.py`.

## Does the tentative NSE signal survive its own named caveat? (Milestone 21)

Milestone 17's tentative post-2008 NSE momentum signal (long leg, daily p=0.044, monthly
p=0.073) shipped with an explicit, unresolved caveat: NSE's universe grew from ~30 names in
2000 to a full 48 by late 2010, so part of the apparent post-2008 improvement could reflect
a less thin, better-populated cross-section rather than a genuine change in the underlying
economics. That caveat was named but never tested — until now.
Checking the NSE mirror's daily coverage directly finds the universe was still expanding
through 2009 (45 of 48 names on average) but has been **perfectly fixed at exactly 48
names, every single day, from 2010-11-04 through the end of the sample (2021-04-30)** — 10.5
of the ~12.7 years in Milestone 17's "post-2008" window. That split gives a clean test:
does the signal survive when restricted to only the years where a growth confound is
definitionally impossible, because the universe never changed size at all?

| | Post-2008 full (Milestone 17) | Growing (2008-09 to 2010-11) | Stable (2010-11 onward, fixed 48 names) |
|---|---|---|---|
| Days | 3,114 | 535 | 2,579 |
| Daily ann. return / p-value | +7.66%/yr, **p=0.044** | +23.72%/yr, p=0.112 (n.s.) | +4.60%/yr, p=0.180 (n.s.) |
| Monthly ann. return / p-value | +7.94%/yr, p=0.073 (marginal) | +21.55%/yr, p=0.132 (n.s.) | +4.96%/yr, p=0.250 (n.s.) |

**Not the confound named, but a different and arguably more serious problem for the same
finding.** The growth-confound story predicted the *growing* years would show inflated,
thin-universe significance that the *stable* years would lack — but the opposite pattern
shows up in the point estimates: the growing sub-period's annualized return is actually
*larger* (+23.72%/yr vs. +4.60%/yr), not smaller, so this is not evidence the universe
growth specifically inflated the signal. What it does show is something this project has
now learned to recognize from Milestones 18-20: **the full-window significance is a
pooling artifact.** Neither natural sub-period — not the growing years, not the fully
stable, fixed-48-name years — reaches significance on its own, at either frequency. The
signal exists only when the two are pooled together.

**Updated conclusion**: Milestone 17's own "promising, not confirmed" label undersold how
fragile this finding is. It is not just unconfirmed; it does not survive being split by
the one structural feature (universe stability) this project already knew was a live
concern, in either direction the split could have gone. Applying the same lesson Milestones
18-20 learned about the crash mechanism — a pooled window's significance can come from
combining two periods rather than a persisting effect in either — to this project's own
tentative finding rather than only to someone else's: the NSE post-2008 momentum signal
should be read as *not currently demonstrated*, not merely as an open, promising thread.

**Reproduce this**: `python investigations/momentum_nse_universe_growth_check.py`.

## A third, independent market: does momentum replicate on ASX? (Milestone 22)

NSE and the US Kaggle mirror are this project's only two markets so far, and both trace
back to community re-exports of specific existing datasets (NSE: one uploader's CSV; US: a
well-known Kaggle "Huge Stock Market Dataset" mirror). Neither is an independent check on
whether momentum is a market-wide phenomenon or an artifact of how those two particular
datasets happen to be built. This milestone looks for a genuine third source.

**Finding one was harder than expected — worth documenting as part of the result, not just
a footnote.** An extensive search for a European per-company OHLCV mirror (the first
choice) found none reachable from this sandbox: `stooq.com`, `huggingface.co`,
`github.com`'s own HTML pages, and `api.github.com`'s general repo-browsing API are all
blocked by the network proxy here — only `raw.githubusercontent.com` is allowlisted, and
only for exact, known file paths. Several candidate European-stock repositories turned out
to be pipeline *code* that fetches from Yahoo Finance or Kaggle at run time (also blocked),
not committed price data. The source that finally worked is
[`grantcarthew/data-asx-historical-share-tables`](https://github.com/grantcarthew/data-asx-historical-share-tables)
— a GitHub mirror of the Australian Securities Exchange's own daily S&P/ASX300 constituent
report emails, 2009-10-20 to 2015-12-31. Not European, but a genuinely independent
developed market: different exchange, different uploader, official ASX report emails
rather than a Kaggle re-export — see "Data provenance: the ASX GitHub mirror" below for
the parsing and validation details.

**Applying this project's current best methodology directly, rather than its history.**
Rather than re-running the original crude full-sample regression Milestones 6-8 started
with, this test goes straight to the out-of-sample rolling hedge and HAC significance
check this project has used for every market since Milestone 10/17:

| | Long leg | Combined long-short |
|---|---|---|
| Raw ann. return (unhedged) | +8.29%/yr | +27.15%/yr |
| Hedged daily ann. return / p | +11.14%/yr, **p=0.0085** | +35.45%/yr, **p=0.0006** |
| Hedged monthly ann. return / p | +9.97%/yr, **p=0.0141** | +30.97%/yr, **p=0.0001** |
| Mean hedge beta | +0.83 | −0.42 |

**Momentum replicates cleanly on ASX — the strongest, most unambiguous result of the three
markets tested.** Both legs are significant at both frequencies, on a proper out-of-sample
hedge from day one (this market never went through the "static full-sample regression
first, hedge added later" history NSE and the US mirror did). The combined book's large
magnitude has a plausible, checked explanation rather than being a red flag on its own: the
short leg's mean beta (−1.26) is far more negative than the long leg's (+0.83) is positive,
consistent with Australia's well-known 2011-2015 mining and resources downturn — momentum's
short leg would have been loaded with high-beta miners that kept underperforming through
exactly that window, and the rolling beta estimates themselves are reasonably stable (std
0.39, no extreme outliers) rather than a symptom of an unstable hedge.

**A genuine limitation, stated plainly: this is the shortest history of the three
markets.** Six years (1,501 trading days) is enough for a full-sample significance test but
not for the era-splitting, structural-break, or persistence checks this project ran
extensively on the US mirror's 47-year history — there is no "pre-publication vs.
post-publication" split possible here, and no way yet to check whether ASX momentum's edge
is stable across sub-periods the way Milestones 9-14 checked for the US. That is future
work, not a result claimed here.

**Reproduce this**: `python investigations/momentum_asx_replication.py`.

## Completing the ASX picture: do 52-week-high and reversal replicate too? (Milestone 23)

Milestone 22 tested only momentum on ASX. NSE and the US mirror were both tested on all
three signals from the first pass (Milestone 3) — ASX had an incomplete picture by
comparison. This milestone runs 52-week-high and short-term reversal on ASX with the
identical out-of-sample hedge + HAC methodology, closing that gap.

| | Long leg (daily / monthly) | Combined long-short (daily / monthly) |
|---|---|---|
| 52-week-high | +7.00%/yr, p=0.099 (marg.) / +8.41%/yr, **p=0.0091** | +24.52%/yr, **p=0.0126** / +23.80%/yr, **p=0.0023** |
| Short-term reversal | −4.04%/yr, p=0.491 (n.s.) / −3.40%/yr, p=0.529 (n.s.) | −3.14%/yr, p=0.818 (n.s.) / −2.49%/yr, p=0.719 (n.s.) |

**Reversal replicates the established pattern: no edge, anywhere.** Consistent with
Milestone 15's full retraction on NSE and the US mirror, reversal shows nothing on ASX
either — not close to significant at either frequency, either leg. A third market, the
identical null. This is a confirming result, not a new one, and needs no further
qualification.

**52-week-high does not — and this is a genuine update to a conclusion this project called
"resolved" three signals ago.** Milestones 6-7 found 52-week-high's apparent edge on NSE
and the US mirror was *entirely* a construction flaw: an uncontrolled long/short beta
mismatch, with **zero** significant alpha in 12 of 12 hedged regressions across both
markets and both frequencies. On ASX, the hedged combined book is significant at both
frequencies (p=0.0126 daily, p=0.0023 monthly), and even the long leg alone clears
significance monthly (p=0.0091). This is not the same failure mode Milestones 6-7 found —
the alpha survives the hedge here, rather than vanishing once beta is controlled for.

**But this likely isn't a second, independent anomaly — it's the same mechanism as
momentum's ASX result, viewed through a highly correlated signal.** 52-week-high and 12-1
momentum are both trend-following constructions (recent winners vs. losers), and on ASX
their leg returns are correlated at **0.76 (long leg) and 0.82 (combined book)** — they are
substantially picking the same names. The short leg's mean beta (−1.36) is close to
momentum's own short-leg beta (−1.26) from Milestone 22, consistent with both signals'
short sides being loaded with the same high-beta mining and resources stocks that
underperformed through 2011-2015. The honest reading: ASX's 2011-2015 divergence was
severe and persistent enough that *any* reasonable trend-following construction would have
captured it, not that 52-week-high anchoring specifically is a real, independent
behavioral edge on this market. Milestones 6-7's core finding — that 52-week-high carries
no *independent* stock-selection skill beyond what a beta or momentum exposure would
already explain — is not disproven here; it has simply never been tested with momentum as
an explicit control on this market, which is the natural next check, not one this
milestone runs.

**Updated conclusion**: momentum remains this project's one demonstrably robust,
independently-replicated finding across all three markets. 52-week-high's ASX result
should be read as an open, mechanism-ambiguous finding — real and hedge-robust, but not
yet shown to be *more* than momentum wearing a different construction — not folded in
alongside momentum as a second confirmed ASX edge.

**Reproduce this**: `python investigations/all_signals_asx_replication.py`.

## Does ASX 52-week-high carry any skill beyond momentum? (Milestone 24)

Milestone 23 left one specific check unrun: whether 52-week-high's significant ASX alpha
survives once momentum is held constant as an explicit control, rather than just compared
against it after the fact via a correlation coefficient. This milestone runs it directly:
regress 52-week-high's out-of-sample-hedged return series on momentum's own hedged return
series (both built identically to Milestones 22-23) and check whether 52-week-high's
intercept — its alpha net of momentum exposure — is still significant.

| | Long leg (daily / monthly) | Combined long-short (daily / monthly) |
|---|---|---|
| Intercept (alpha net of momentum) | p=0.318 / p=0.349 | p=0.747 / p=0.936 |
| Momentum exposure coefficient | +0.265, **p=0.017** / +0.303, **p=0.015** | +0.876, **p<0.0001** / +0.842, **p<0.0001** |
| R² | 0.089 / 0.082 | 0.658 / 0.596 |

**Decisive: 52-week-high's ASX alpha does not survive controlling for momentum, in any of
the four cuts.** Once momentum's own hedged return series is included as a regressor, the
intercept collapses to statistically indistinguishable from zero at both frequencies, both
legs — a sharp contrast with Milestone 23's uncontrolled check, where 52-week-high's alpha
was significant at every one of those same four cuts. The momentum exposure coefficient,
meanwhile, is highly significant everywhere, and for the combined long-short book it
explains the large majority of 52-week-high's variance (R²=0.60-0.66, momentum coefficient
≈0.84-0.88) — 52-week-high's combined book moves almost one-for-one with momentum's own.

**Updated conclusion**: this confirms, rather than merely suggests, Milestone 23's "same
mechanism" reading. ASX 52-week-high carries no demonstrated independent stock-selection
skill once momentum exposure is accounted for — its apparent edge is momentum's own ASX
alpha, viewed through a highly correlated construction, not a second, distinct behavioral
anomaly. This closes the open thread Milestone 23 left explicitly unresolved, and restores
52-week-high to the same "no independent skill demonstrated" verdict Milestones 6-7 reached
on NSE and the US mirror — reached here by a different, more direct test (a momentum
control, not a beta hedge), but landing at the same place.

**Reproduce this**: `python investigations/momentum_control_asx_52w_high.py`.

## A new signal: does the low-volatility anomaly replicate anywhere? (Milestone 25)

Every signal in this project so far — momentum, 52-week-high, short-term reversal — is a
trend/reversal construction built purely from price history. The low-volatility anomaly
(Ang, Hodrick, Xing & Zhang 2006; Frazzini & Pedersen 2014's "betting against beta") is a
different bet: rank names by trailing realized volatility, go long the calmest decile,
short the most volatile one. Standard CAPM says expected return should rise with
volatility/beta; the anomaly is that historically it hasn't. This milestone builds the
signal (`signals/low_volatility.py`) and tests it on all three markets immediately with
this project's current best methodology, rather than repeating the project's own
methodological history one market at a time.

| | NSE, long leg (daily/monthly) | US, long leg (daily/monthly) | ASX, long leg (daily/monthly) |
|---|---|---|---|
| Hedged ann. return / p | -1.70%, p=.673 / -0.46%, p=.857 | -2.45%, p=.172 / -2.19%, p=.125 | +7.73%, p=.090 / **+8.74%, p=.0099** |

| | NSE, combined (daily/monthly) | US, combined (daily/monthly) | ASX, combined (daily/monthly) |
|---|---|---|---|
| Hedged ann. return / p | -2.56%, p=.943 / +0.86%, p=.849 | **-20.70%, p=.0002 / -18.09%, p=.0004** | +15.54%, p=.123 / +16.04%, p=.114 |

**No clean story across markets — and the most striking result is a significant
*inversion*, not a confirmation.** NSE shows nothing at all, either leg, either frequency.
ASX shows a modest, real signal in the long (low-vol) leg alone — significant monthly
(p=0.0099), marginal daily (p=0.090) — but the combined book isn't significant. The US
mirror shows the strongest result of all, and it runs the wrong way: the hedged combined
book loses **20.70%/yr** (daily) and **18.09%/yr** (monthly), both highly significant
(p<0.001) — high-volatility names significantly *outperformed* low-volatility ones, net of
beta, over 1970-2017. This is the opposite of what the anomaly predicts.

**Checked for the obvious confound first, given this project's own history with this exact
dataset.** Milestone 15 found the US mirror's pre-1985 window is severely thin and
survivorship-biased for reversal; before trusting a striking US result on the same
dataset, the same check applies here. Re-running the combined-book regression from ten
different start dates (1970 through 2000): the negative, anomaly-inverting result holds,
significant or near-significant (p=0.02-0.09), at every start date from 1978 through 1995
— it is not a 1970s-thin-universe artifact. It weakens only from a 2000 start (p=0.20,
n.s.), consistent with genuine decay rather than a data-quality problem concentrated in one
early window.

**Updated conclusion**: the low-volatility anomaly, as this project has constructed it,
does not replicate as a positive finding on any of the three markets, and inverts with real
statistical force on the one market (US) with enough history to test it properly. This
should not be filed alongside momentum as a second working signal, nor alongside reversal
and 52-week-high as a cleanly retracted one — it is its own, distinct negative result: a
well-documented academic anomaly that this project's own data does not support, and on its
best-tested market, actively contradicts.

**Reproduce this**: `python investigations/low_volatility_all_markets.py`.

## Data provenance: the NSE GitHub mirror

`load_nse_github_mirror()` pulls
`raw.githubusercontent.com/dheeraj5988/stock_market_dataset/main/combined_stock_data.csv`
— a personal, community-uploaded repository, **not an official exchange or licensed
data-vendor feed**. Treat results from it as a genuine methodology demonstration on real
market prices, not as investment-grade research, until cross-checked against an official
source (NSE/BSE archives, a paid vendor, or Yahoo/Stooq once reachable). Specifically:

- **Ticker-rename cleanup is evidence-based, not assumed.** The raw file has 63 distinct
  symbol codes; inspecting each one's min/max trade date showed 14 chains of symbols with
  zero date overlap and near-perfect day-to-day contiguity — the signature of an NSE
  ticker-symbol change (e.g. `TELCO`→`TATAMOTORS`, `TISCO`→`TATASTEEL`,
  `SESAGOA`→`SSLT`→`VEDL`), each cross-checked against known Indian market corporate
  history. `HDFC` and `HDFCBANK` were deliberately kept separate — they were two distinct
  listed companies for this entire sample (they only merged in mid-2023, after the data
  ends). The merge map lives in `data/loaders.py`, `_NSE_RENAME_CHAINS`.
- **Still not survivorship-bias-free even after merging.** The 48 resulting companies are
  ones prominent enough to be included in whatever process built this mirror in the first
  place (looks like large/mid-cap NSE names) — it is not a point-in-time index
  reconstruction, so it over-represents "companies that stayed large and relevant," the
  same limitation flagged generically below, now concrete for this specific dataset.
- **No longer India-only**: see "Replication on a second market" above — a US large-cap
  mirror was located and run through the same pipeline, and it changed which findings
  looked robust (momentum and reversal did **not** replicate consistently; the
  52-week-high signal's losses did).

## Data provenance: the US Kaggle mirror

`load_us_kaggle_mirror()` pulls per-ticker CSVs from
`raw.githubusercontent.com/scienclick/stocks/master/data/Stocks/<ticker>.us.txt` — a
GitHub mirror of the well-known Kaggle "Huge Stock Market Dataset" (Boris Marjanovic),
itself compiled from historical price data, **not an official exchange or licensed
data-vendor feed**, same caveat as the NSE mirror above. Specifics:

- **Coverage ends 2017-11-10** — this is a historical replication check, not a live
  feed. Each company's series starts at its own listing/IPO date (e.g. Visa's starts
  2008-03-18) and runs through that end date.
- **`META` is served under its pre-2021 ticker, `FB`** (Facebook, Inc., before the
  corporate rename to Meta Platforms) — the dataset predates the rename. Documented in
  `data/loaders.py`, `US_MIRROR_UNIVERSE`, not silently substituted.
- **Same survivorship caveat as the NSE mirror**: this is `DEFAULT_UNIVERSE`, a
  present-day-chosen large-cap list, not a point-in-time constituents file for any given
  historical date.
- **The universe is severely thin before the mid-1980s, and this materially matters, not
  just cosmetically (Milestone 15).** Only 9-14 of the 30 default tickers have any price
  data before 1983; a 5-decile backtest's long leg is consequently just 2-4 stocks from
  1972 through 1983. This thin-universe problem, combined with survivorship bias (every
  name in this era's universe is, by construction, a company that went on to become a
  mega-cap winner by 2017), was found to entirely explain short-term reversal's apparent
  pre-1994 alpha — see "Investigating the mechanism behind the 1980 reversal break" above.
- **Two specific unadjusted-split-like data anomalies were found in this era (Milestone
  15), not previously documented**: `WMT` drops 52% on 1974-12-06 then jumps back +109% on
  1974-12-18 (a round-trip, consistent with a split-adjustment error that later
  self-corrects in the raw feed), and `INTC` jumps +101% on 1972-01-27 and +51% on
  1972-06-22. Any result drawing on these tickers' data before ~1975 (INTC) or across
  December 1974 (WMT) should be treated with added caution.

## Data provenance: the ASX GitHub mirror

`load_asx_github_mirror()` pulls ~1,600 individual daily report CSVs (one per trading day,
fetched in parallel) from
`raw.githubusercontent.com/grantcarthew/data-asx-historical-share-tables/master/csv/Daily/S%26P-ASX300/`
— a GitHub mirror of the Australian Securities Exchange's own daily S&P/ASX300 constituent
report emails, **not a Kaggle re-export like the NSE and US mirrors above**. Specifics:

- **Coverage: 2009-10-20 to 2015-12-31**, ~1,501 trading days — this project's shortest
  history by far (vs. NSE's 21 years and the US mirror's 47). Treat any full-sample number
  from this market as a single-era result, not yet checked for stability across sub-periods.
- **Two report-text formats, parsed both**: reports before mid-2010ish give the trading
  date as `DD/MM/YYYY`; later reports spell it out (`"Trading data for Thursday, May 12,
  2011"`). Critically, **the filename's date is the day the report was *processed*
  (typically the next morning), not the trading date** — and the offset between the two
  is not constant (it widens across weekends and public holidays, e.g. a report filed
  2014-06-10 covers trading from 2014-06-06). The loader parses the actual trading date out
  of each file's own header text rather than trusting the filename.
- **Raw parsing yields ~638 distinct codes; only 209 are genuine, persistent constituents.**
  The rest are mostly ASX deferred-settlement trading variants (temporary codes with
  suffixes like `DA`/`DC`/`R` used during capital raisings, not separate companies) that
  appear for only a handful of days each. Applying the same data-density discipline
  Milestone 15 forced onto this project — drop any code with fewer than 1,000 days of
  history, the identical threshold `load_nse_github_mirror` already uses — removes
  essentially all of them and leaves a stable ~200-name universe (min 160, median 199 of
  209 present on any given day; see Milestone 22 above for why this comfortably clears the
  thin-universe bar).
- **Spot-checked against known history, not just internally consistent.** BHP, CBA, and
  ANZ close at $18.09, $85.57, and $27.96 respectively on 2015-12-30 in this mirror —
  matching the real, publicly known price levels for Australia's largest bank and largest
  miner at the end of 2015 (BHP mid-recovery from the iron-ore price collapse, CBA near its
  all-time high before the later bank royal commission). Not a substitute for an audited
  feed, but a real sanity check beyond internal consistency.
- **No ticker-rename curation was attempted**, unlike the NSE mirror's explicit
  `_NSE_RENAME_CHAINS`. If any of the 209 retained ASX codes underwent a symbol change
  within this window, that company's series would appear artificially truncated rather than
  merged — a known, undocumented-in-detail limitation, not one this project has checked
  stock-by-stock.

## Methodology

### Case studies (qualitative, `case_studies/`)

Five episodes plus the "exploit side," chosen to be well-documented and to pull in
different directions (institutional failure at different scales, and one case running the
opposite direction — retail herding overwhelming institutions):

| Case | Failure mode | Behavioral mechanism |
|---|---|---|
| LTCM (1998) | "Rational" convergence-arbitrage model assumed historical correlations/vol would hold; 25:1+ leverage turned a plausible loss into a solvency event | Flight-to-quality herding by *counterparties*, not LTCM itself, broke the model's correlation assumptions |
| Quant Quake (Aug 2007) | Multiple market-neutral quant funds, each individually "rational," had converged on correlated factor bets; one fund's forced unwind cascaded into a correlated, self-reinforcing selloff across the group | Herding among sophisticated arbitrageurs (crowding), not retail panic |
| Amaranth Advisors (2006) | A single trader's concentrated, highly leveraged natural-gas spread position | Overconfidence / illusion of control |
| 2008 financial crisis | Industry-wide Gaussian-copula default-correlation model, calibrated on a housing-boom window with no national price decline, mispriced senior CDO tranches once defaults stopped being independent | Herding into a shared industry model (adoption risk beat model risk), then a correlated counterparty-trust collapse once losses started |
| GameStop squeeze (Jan 2021) | Institutional short positioning (Melvin Capital et al.) assumed away the risk of a large, fast, coordinated retail short squeeze | Social-media herding, attention-driven retail trading, gamified trading-app design — the *opposite* direction from the other cases |
| Fuller & Thaler, LSV, AQR (ongoing) | N/A — these are the "exploit side" | Built explicit strategies around anchoring, under/overreaction, and overextrapolation biases in *other* investors |

### Quantitative signals (`signals/`)

Three anomalies chosen because each has a specific, named behavioral mechanism in the
literature (not just "it worked historically"):

1. **12-1 month momentum** (Jegadeesh & Titman, 1993) — underreaction to information that
   diffuses slowly through the market.
2. **52-week-high proximity** (George & Hwang, 2004) — anchoring: investors use the 52-week
   high as a reference point and are slow to bid a stock through it even on good news.
3. **Short-term (1-month) reversal** (Jegadeesh, 1990; Lehmann, 1990) — overreaction /
   liquidity-provision: very recent losers/winners partially mean-revert as overreaction
   unwinds.

A **composite behavioral mispricing score** (`signals/composite.py`) combines all three,
cross-sectionally z-scored, as the input to the investment framework in `../FRAMEWORK.md`.

### Backtest design (`backtest/engine.py`)

Standard decile-sort long-short methodology: at each monthly rebalance, rank the universe
by signal, go long the top decile / short the bottom decile, equal-weighted, hold one
month, roll forward. Reports gross and cost-adjusted Sharpe ratio, max drawdown, monthly
turnover, and a simple linear transaction-cost model (bps per unit of turnover).

### Risk simulation (`risk_simulation/fat_tails_vs_normal.py`)

Monte Carlo comparison of a portfolio's 1-day 99% VaR estimated two ways:
(a) fit a multivariate Gaussian to "calm regime" returns and extrapolate, vs.
(b) simulate from a fat-tailed (Student-t) return process with a **regime-switching
correlation matrix** that jumps to near-1 pairwise correlation during stress — the
mechanism widely cited for why LTCM's diversification assumptions failed in Aug-Sep 1998.
Reports how many multiples the Gaussian model underestimates the true tail loss by.

## Data sources

- **NSE GitHub mirror** (`load_nse_github_mirror`) — 48 India-listed companies,
  2000–2021, reachable from any environment whose network policy allowlists GitHub.
  See "Data provenance: the NSE GitHub mirror" above for its caveats.
- **US Kaggle GitHub mirror** (`load_us_kaggle_mirror`) — 30 US large-caps, listing date
  through 2017-11-10, also reachable via the GitHub allowlist. See "Data provenance: the
  US Kaggle mirror" above.
- **ASX GitHub mirror** (`load_asx_github_mirror`) — ~209 Australia-listed companies,
  2009-10-20 to 2015-12-31, a third and genuinely independent GitHub-reachable source (see
  "Data provenance: the ASX GitHub mirror" above). All three mirrors are the sources
  actually exercised in this repo.
- **Yahoo Finance / Stooq** (`load_price_history` / `load_single`) — the original
  US-large-cap, live-data default path. Needs general internet access this sandbox didn't
  have; still unexercised here. Universe is a hard-coded liquid large-cap list, not a
  point-in-time index membership file — see "Explicit limitations."

## How to run

```bash
cd research/behavioral-finance
pip install -r requirements.txt

# Q1 — runs now, no internet needed, no dependency on the rest of the repo
python risk_simulation/fat_tails_vs_normal.py

# Q2 — path 1, validated in this repo (NSE mirror via GitHub)
python -c "
from data.loaders import load_nse_github_mirror
from signals.composite import composite_score
from backtest.engine import run_decile_backtest

prices = load_nse_github_mirror()  # downloads + caches to data/cache/
scores = composite_score(prices)
result = run_decile_backtest(prices, scores, n_deciles=5)  # quintiles: 48 names is thin for deciles
print(result.summary())
"

# Q2 — path 2, validated in this repo (US Kaggle mirror via GitHub)
python -c "
from data.loaders import load_us_kaggle_mirror
from signals.composite import composite_score
from backtest.engine import run_decile_backtest

prices = load_us_kaggle_mirror()
scores = composite_score(prices)
result = run_decile_backtest(prices, scores, n_deciles=5)
print(result.summary())
"

# Q2 — the original live-data US-universe path; needs a reachable Yahoo/Stooq, unvalidated here
python -c "
from data.loaders import load_price_history
from signals.composite import composite_score
from backtest.engine import run_decile_backtest

prices = load_price_history(period='10y')
scores = composite_score(prices)
result = run_decile_backtest(prices, scores)
print(result.summary())
"

# Investigation — is the 52-week-high result a value/growth confound? (rejected; see above)
python investigations/52w_high_value_confound.py

# Investigation — is the 52-week-high result momentum-crash risk? (descriptive pass;
# looked compelling, see the formal test below before trusting it)
python investigations/momentum_crash_risk.py

# Investigation — same question, formally: HAC regressions, daily + monthly frequency
# (result: NOT statistically confirmed — see "Formally testing momentum-crash risk" above)
python investigations/momentum_crash_significance.py

# Investigation — is it just uncontrolled market-beta exposure? (yes — see "Is it just
# beta?" above; this is the actual explanation)
python investigations/short_leg_beta.py

# Investigation — does real alpha survive an actual, out-of-sample rolling beta hedge?
# (no — see "Does real alpha survive an actual beta hedge?" above)
python investigations/beta_hedged_backtest.py

# Investigation — does the same beta check apply to momentum and reversal? (reversal's
# edge is retracted; US momentum's is the strongest finding in this project — see
# "Does the reversal edge survive a beta check too?" above)
python investigations/momentum_reversal_beta.py

# Investigation — has US momentum's alpha decayed since 1993 publication? (yes, partially —
# see "Has US momentum's alpha decayed since publication?" above)
python investigations/momentum_publication_decay.py

# Investigation — does that post-1994 alpha survive an actual out-of-sample hedge, not just
# an in-sample regression? (no — see "Does the post-1994 alpha survive an actual
# out-of-sample hedge?" above)
python investigations/momentum_hedged_decay_backtest.py

# Investigation — is that post-1994 null result a 2009 crash artifact, a hedge-window
# artifact, or genuine decay? (genuine, ongoing decay — see "Is the post-1994 null result
# a crash artifact, a hedge artifact, or genuine decay?" above)
python investigations/momentum_decay_regime_analysis.py

# Investigation — is "real pre-1994, decayed since" specific to momentum, or market-wide?
# (market-wide — reversal's long leg shows the same pattern; see "Is 'real pre-1994, decayed
# since' specific to momentum, or market-wide?" above)
python investigations/all_signals_decay_analysis.py

# Investigation — quantify the decay rate directly instead of a binary 1994 cut (momentum:
# not a smooth trend, breaks sharply around 2008-09; reversal: genuinely smooth decline,
# zero-crossing ~2004; see "Quantifying the decay" above)
python investigations/decay_rate_estimation.py

# Investigation — formal structural-break test: Chow test at a literature-motivated date +
# Quandt-Andrews sup-Wald search with a block-bootstrap p-value (momentum's 2008 hypothesis
# holds but an unconstrained search doesn't decisively confirm one dominant break; reversal's
# real break is ~1980, not 2008; see "A formal structural-break test" above)
python investigations/structural_break_test.py

# Investigation — what caused the 1980 reversal break: a real market event, or thin/biased
# data? (thin/biased data — reversal's entire alpha claim is retracted; momentum, tested as
# a control, is unaffected; see "Investigating the mechanism behind the 1980 reversal
# break" above)
python investigations/reversal_1980_break_diagnostics.py

# Investigation — does the classic momentum-crash mechanism (Bear x High-Vol) explain
# momentum's 2008-09 break? (yes for the long leg — dormant pre-2008 (p=0.42), significant
# post-2008 (p=0.008); see "Does the classic momentum-crash mechanism explain the 2008-09
# break?" above)
python investigations/momentum_crash_mechanism_2008.py

# Investigation — does the momentum-crash mechanism replicate on NSE, and does the
# project's own more rigorous hedge methodology find NSE momentum alpha a cruder test
# missed? (mechanism does not replicate; a tentative post-2008 signal does emerge; see
# "Does the momentum-crash mechanism replicate on NSE?" above)
python investigations/momentum_crash_mechanism_nse.py

# Investigation — was the 2008-09 crash-mechanism finding (Milestone 16) a permanent
# post-2008 regime, or specific to the crisis itself? (no bear-market regime recurred
# after Sept 2009 in this sample, so the interaction cannot even be tested post-crisis; see
# "Was the 2008-09 crash mechanism a permanent regime change, or a one-off crisis?" above)
python investigations/momentum_crash_mechanism_persistence.py

# Investigation — does the crash-mechanism finding survive different volatility-window and
# bear-lookback choices? (Milestone 16's pattern replicates in 8/16 combinations, robust
# near this project's own defaults; Milestone 18's "no bear regime since 2009" does NOT
# survive shorter, equally standard lookbacks; see "Does the crash-mechanism finding
# survive different regime-construction choices?" above)
python investigations/momentum_crash_regime_robustness.py

# Investigation — did the crash mechanism reactivate in 2011 or 2015-16, now that a bear
# regime actually exists there under shorter lookbacks? (no — interaction not significant at
# either alternate window, and the bear-alone effect flips to positive/significant at the
# 189-day lookback, the wrong sign for crash risk; see "Did the crash mechanism reactivate
# in 2011 or 2015-16?" above)
python investigations/momentum_crash_mechanism_recurrence.py

# Investigation — does the tentative NSE post-2008 momentum signal (Milestone 17) survive
# splitting by universe stability, testing its own named growth-confound caveat? (not the
# confound named, but a worse problem: neither the growing-universe years nor the fully
# stable, fixed-48-name years is significant alone -- the signal only exists pooled; see
# "Does the tentative NSE signal survive its own named caveat?" above)
python investigations/momentum_nse_universe_growth_check.py

# Investigation — does momentum replicate on a third, independent market (ASX Australia),
# tested with this project's current best methodology from the start? (yes -- both legs
# significant at daily and monthly frequency, the cleanest result of the three markets
# tested, though on this project's shortest sample history; see "A third, independent
# market: does momentum replicate on ASX?" above)
python investigations/momentum_asx_replication.py

# Investigation — do 52-week-high and short-term reversal replicate on ASX too, completing
# the three-signal picture Milestone 22 only ran for momentum? (reversal: no, consistent
# with the established null everywhere; 52-week-high: significant hedged alpha, but highly
# correlated (0.76-0.82) with momentum's own ASX result -- likely the same mechanism, not a
# second independent edge; see "Completing the ASX picture" above)
python investigations/all_signals_asx_replication.py

# Investigation — does ASX 52-week-high's alpha survive momentum as an explicit control,
# closing the thread Milestone 23 left open? (no -- intercept collapses to insignificant at
# all four cuts (p=0.32-0.94) once momentum is included as a regressor, while momentum's own
# coefficient is highly significant everywhere; confirms 52-week-high has no independent ASX
# skill beyond momentum; see "Does ASX 52-week-high carry any skill beyond momentum?" above)
python investigations/momentum_control_asx_52w_high.py

# Investigation — a new signal (low-volatility anomaly, not previously tested in this
# project) on all three markets at once, with this project's current best methodology from
# the start? (no clean replication anywhere; NSE null, ASX weak long-leg-only positive, US
# significantly INVERTS -- high-vol beat low-vol, net of beta, p<0.001, robust to a
# 1970s-thin-universe check; see "A new signal: does the low-volatility anomaly replicate
# anywhere?" above)
python investigations/low_volatility_all_markets.py

# Tests (synthetic fixtures — no internet needed)
pytest tests/ -v
```

## Concrete, applicable outputs

This research is designed to feed three deliverables (full detail in `../FRAMEWORK.md`):

1. **An investment framework** — a composite behavioral mispricing score usable as a
   screening/tilt signal alongside fundamental analysis, now with real empirical caveats
   attached (see "Empirical results" through "Investigating the mechanism behind the 1980
   reversal break" above): don't trust it blind on a large-cap-only universe, check which
   sub-signal is actually carrying any edge before combining them, and beta-neutralize
   long-short legs before crediting any performance difference to a behavioral effect
   rather than to uncontrolled market exposure. No cell in this project currently survives
   every check applied at this repo's own highest standard of rigor: US 12-1 momentum's
   long leg passed decomposition, cross-market replication, a beta-adjusted significance
   test, an in-sample publication-decay split (Milestone 9), an actual rolling
   out-of-sample hedge (Milestone 10), a deep investigation into whether that hedge's null
   result was a crash or methodology artifact (Milestone 11, confirming it was neither), a
   continuous decay-rate estimate showing its weakness is a sharp 2008-09 break rather than
   smooth decay (Milestone 13), and a formal, multiple-testing-corrected structural-break
   test (Milestone 14, confirming the specific 2008-09 hypothesis while declining to
   confirm any single date as *the* dominant break), a causal-mechanism test (Milestone
   16, finding the Daniel-Moskowitz momentum-crash dynamic explains the break), a
   cross-market replication of that mechanism (Milestone 17, finding it does *not*
   replicate on NSE — a US-specific effect), a persistence test (Milestone 18, finding
   the "post-2008" crash-regime significance is generated entirely by the 2008-09 crisis
   itself, since no bear-market regime has recurred in this sample since — so it should be
   read as "confirmed for one crisis," not "a standing post-2008 feature"), and a
   parameter-robustness sweep (Milestone 19, finding the crash-mechanism *pattern* replicates
   in 8 of 16 nearby volatility/bear-lookback choices, but Milestone 18's specific "no bear
   regime recurred" claim does not survive shorter, equally standard lookbacks — a real
   qualification, not just a footnote), and a direct reactivation test (Milestone 20,
   re-running the persistence test under the lookbacks where a real post-2010 bear regime
   exists and finding the mechanism did *not* reactivate in either 2011 or 2015-16 —
   closing Milestone 19's open thread and strengthening, not just leaving open, Milestone
   18's "confirmed for one crisis" framing). A separate line of work applied that same
   pooled-window lesson to this project's own remaining open, "promising not confirmed"
   thread — the tentative NSE post-2008 momentum signal (Milestone 21): splitting by
   universe stability (the specific caveat Milestone 17 itself named) found neither the
   growing-universe years nor the fully stable years significant alone, downgrading the
   signal from "promising, not confirmed" to "not currently demonstrated." Finally, a third
   independent market was found and tested (Milestone 22, after an extensive search ruled
   out every reachable European source): momentum replicates cleanly on ASX (Australia),
   both legs significant at daily and monthly frequency on a proper out-of-sample hedge
   from the start — the cleanest of the three markets, though on this project's shortest
   sample history (2009-2015) and not yet checked for era-stability the way the US mirror
   was. The other two signals were then tested on ASX too (Milestone 23, completing the
   three-signal picture NSE/US had from the start): reversal replicates the established
   null (no edge, consistent with its full retraction elsewhere); 52-week-high shows
   significant hedged alpha, but at 0.76-0.82 return correlation with momentum's own ASX
   result, this looks like the same mechanism viewed through a highly correlated signal,
   not a second independent ASX edge — left as an open, mechanism-ambiguous finding, not
   folded in as a confirmed second anomaly. That open thread was then closed directly
   (Milestone 24): regressing 52-week-high's hedged returns on momentum's own hedged
   returns, 52-week-high's intercept is statistically indistinguishable from zero at all
   four cuts (p=0.32-0.94) while momentum's own coefficient is highly significant
   everywhere — ASX 52-week-high carries no demonstrated skill independent of momentum,
   confirming rather than merely suggesting Milestone 23's reading. A genuinely new signal
   was then introduced (Milestone 25): the low-volatility anomaly, tested on all three
   markets at once with this project's best methodology from the start. It does not
   replicate as a positive finding anywhere — null on NSE, a modest long-leg-only signal on
   ASX, and a statistically significant *inversion* on the US mirror (hedged combined book
   loses 20.70%/yr, p=0.0002, high-volatility names significantly outperforming low-volatility
   ones net of beta), robust to the same pre-1985 thin-universe check that mattered for
   reversal. Momentum's
   pre-2008-09 alpha is this repo's one surviving, repeatedly-stress-tested finding.
   **Short-term reversal's
   apparent pre-2005 alpha (Milestones 9, 12-14) has since been retracted (Milestone 15):
   it depended entirely on a severely thin (2-4 stock), survivorship-biased, and partly
   data-glitched 1972-1977 sample window, and vanishes completely (p=0.54-0.96) once that
   window is excluded — including from the exact date Milestone 14's own structural-break
   search identified.** Momentum, tested as a control against the identical unreliable
   early data, was unaffected — its significance does not depend on those years at all.
   Nothing in this project has demonstrated a forward-sizeable edge in the most recent
   decade or so, for any signal, in either direction.
2. **Risk-management lessons** — a stress-testing playbook (derived from the Q1 simulation)
   for any leveraged or "market-neutral" strategy: never calibrate tail risk on a calm-regime
   correlation matrix alone.
3. **A business/product idea** — a standalone pitch, not tied to any specific existing
   platform.

## Explicit limitations (state these in any paper or pitch built on this)

- **Survivorship bias**: both loaders use a fixed, present-day-chosen ticker/company list,
  not point-in-time index membership — true of the Yahoo/Stooq default universe and of the
  NSE GitHub mirror alike (see "Data provenance" above for the latter specifically). A
  rigorous version needs a survivorship-bias-free universe (e.g., CRSP, or a maintained
  point-in-time constituents file).
- **Transaction costs are a simple linear model**, not a real market-impact model; real
  turnover costs for a strategy this size would need a proper implementation-shortfall
  estimate.
- **No out-of-sample / walk-forward validation** is wired up by default — anyone extending
  this should split into a strict in-sample fit period and out-of-sample test period before
  claiming an edge, and check performance decay after each anomaly's publication date
  (a very well-documented risk for momentum and reversal specifically).
- **The Q1 simulation's regime-switching correlation and fat-tail parameters are
  illustrative, calibrated loosely to the LTCM episode's qualitative shape** (correlations
  that were low/moderate in normal times moving toward 1 in the crisis), not fit to LTCM's
  actual undisclosed book. Treat the multiple as "this is the order of magnitude of the
  effect," not a precise historical reconstruction.
- **The 52-week-high signal's cause: resolved, and it's the boring answer.** Two
  behavioral/statistical explanations were ruled out by direct test — not purely the
  2008/2020 crash windows (Milestone 2), not a value/growth confound (Milestone 3), not
  formally-tested momentum-crash risk (Milestone 5, which walked back Milestone 4's
  descriptive-looking confirmation). The actual explanation (Milestone 6, "Is it just
  beta?") is a construction flaw, not a market phenomenon: the long and short legs have
  significantly different, uncontrolled market-beta exposure (long ≈ +0.8, short ≈ −1.2 to
  −1.4), leaving the combined book net short-beta (−0.32 to −0.70, p<0.001 every cut) in
  markets that returned ~20%/year over the sample. Once beta is controlled for, **alpha is
  insignificant in every leg, every market, every frequency (12 of 12 regressions)** — there
  is no demonstrated stock-selection skill in this signal, in either direction, in this
  repo as it stands. **Milestone 7 confirmed this independently**, with an actual rolling,
  out-of-sample beta hedge rather than a single full-sample regression coefficient: the
  hedge cuts the loss roughly in half but the residual return is still not statistically
  distinguishable from zero, in either market, at either frequency. Anything built on this
  repo should beta-neutralize the legs before claiming a behavioral edge from this signal —
  and even then, per Milestone 7, expect an imperfect hedge (rolling beta is itself quite
  unstable over time in both markets) and real hedging transaction costs not modeled here.
- **Momentum and reversal did not replicate consistently across the two markets tested**
  (see "Replication on a second market") — treat any single-market anomaly finding in this
  repo as provisional until it's been checked on at least one more, independent universe.
- **Short-term reversal's "positive" empirical result is retracted, fully, at every level
  this project checked (Milestones 8, then 12, then 15 — a claim that briefly looked
  rehabilitated before being retracted again, more thoroughly).** Milestone 8's full-sample
  CAPM beta check found none of reversal's 12 alpha tests significant. Milestone 12 then
  found this incomplete: reversal's long leg carried a real-looking, significant pre-1994
  alpha (+5.31%/yr, p=0.046) hidden inside that full-sample average. But Milestone 15
  traced that apparent pre-1994 alpha to its source and found it depends entirely on a
  severely thin (2-4 stock), survivorship-biased, partly data-glitched 1972-1977 sample
  window — it vanishes completely (p=0.54-0.96, often slightly negative) from any start
  date at or after 1978, including the exact date Milestone 14's own structural-break
  search identified as reversal's "true" break (1980-08-29, p=0.922). Momentum, tested
  through the identical unreliable early data as a control, was unaffected (p≤0.02 at
  every comparable start date). **Reversal shows no reliably demonstrated edge anywhere in
  this dataset, in any leg, at any point in the sample, once properly checked.**
- **US 12-1 momentum's alpha decays after publication, as expected (Milestone 9) — and
  does not survive an actual out-of-sample hedge post-1994 (Milestone 10, superseding
  Milestone 9's framing).** Milestone 9's in-sample per-era regression found the long
  leg's alpha shrinking ~33-38% post-1994 but remaining significant, and the combined
  book losing significance only at daily frequency. Milestone 10 re-ran the same split on
  a rolling, out-of-sample beta-hedged return series (re-estimated every rebalance from
  only trailing data, exactly as Milestone 7 built for the 52-week-high signal) and found
  a sharper result: **pre-1994 alpha is strongly confirmed in both legs (p≤0.025), but
  post-1994 alpha is not statistically significant in either leg, at either frequency**
  (p=0.15-0.59), and the hedged combined book's post-1994 average return is outright
  negative (-0.31%/yr). The gap between the two milestones is the in-sample vs.
  out-of-sample distinction, not a data error: an in-sample regression can fit quirks
  specific to the sample it's tested against; a hedge estimated only from prior data
  cannot, and here it finds nothing post-1994. Treat this project's momentum finding as
  real and strong pre-1994, and **not currently demonstrated to be forward-sizeable**
  in the post-publication era — the more precise, and more sobering, replacement for
  Milestone 9's "decays but doesn't disappear" framing.
- **The post-1994 null result is genuine, ongoing decay — not a 2009 crash artifact, and
  not a hedge-window artifact (Milestone 11).** Three checks: (1) a five-era breakdown of
  post-1994 shows the long leg's hedged excess return declining from +6.5%/yr (1994-99) to
  essentially zero (+0.1%/yr, 2010-2017) — a trend, not a single bad episode with a
  recovery; (2) excluding the March-August 2009 momentum-crash window (Daniel & Moskowitz,
  2016) moves the long leg's alpha p-value from 0.149 to a borderline 0.095, but barely
  moves the combined book's (0.590 to 0.334, nowhere near significance) — the crash was
  real and severe (the combined book lost 40% cumulatively in those 128 days alone) but
  does not explain either leg's overall null result; (3) re-running the hedge with 126-,
  252-, and 378-day rolling windows gives the same pattern every time (pre-1994 always
  significant at p≤0.017, post-1994 never significant, p=0.14-0.66) — the null result does
  not depend on the specific window chosen. **This investigation does not reverse
  Milestone 10's conclusion; it rules out the two most obvious objections to it and leaves
  ongoing, genuine decay as the best-supported explanation.**
- **"Real pre-1994, decayed since" is not momentum-specific — it also appears in
  short-term reversal's long leg, and is absent from 52-week-high entirely (Milestone
  12).** Applying the same pre/post-1994 out-of-sample hedge to all three US signals found
  two distinct stories: 52-week-high shows no significant alpha in either era, in any leg
  (it never had genuine stock-selection skill, consistent with Milestones 6-7); reversal's
  long leg shows the identical decay signature as momentum's — real, significant pre-1994
  alpha (p=0.046) fully decayed to noise post-1994 (p=0.629) — which Milestone 8's
  full-sample regression correctly found non-significant overall but could not distinguish
  from "never real." Treat Milestone 8's reversal retraction as accurate at the full-sample
  level but incomplete: the long leg was a genuine, decayed effect, not pure noise. **[Since
  retracted: Milestone 15 traced this "genuine pre-1994 alpha" to a thin, survivorship-biased
  1972-1977 sample window and found it does not survive removing those years — see
  "Investigating the mechanism behind the 1980 reversal break" above.]**
- **The 1994 cutoff, while directionally right for momentum, misdescribes its shape and
  timing (Milestone 13).** Quantifying the decay as a continuous linear trend rather than a
  binary split finds momentum's slope is *not* statistically significant (p=0.15) — the
  effect did not decay smoothly. A rolling 5-year trajectory shows momentum's hedged alpha
  stayed consistently strong (+4% to +22%/yr) from the 1970s all the way through the window
  ending January 2008, then broke sharply negative from 2009 on. Splitting at September
  2008 instead of 1994 gives a far cleaner divide (pre: +8.02%/yr, p=0.0005; post: -0.56%/yr,
  p=0.998) than the 1994 split ever did. Momentum's weakness is better described as a sudden
  regime shift around the 2008-09 crisis (plausibly tied to the 2009 momentum crash examined
  in Milestone 11) than gradual, 1994-onward publication decay. Reversal's decay, by
  contrast, *is* well-described by a smooth linear trend (slope -0.41%/yr, p=0.026, implied
  zero-crossing ~November 2004) — the two signals' declines have genuinely different shapes,
  and neither should be assumed to generalize to the other. **[Since retracted for reversal:
  Milestone 15 found this "smooth trend" is itself an artifact — reversal has no significant
  alpha at all once the thin, unreliable 1972-1977 window is excluded, so there is no real
  decline left to describe as smooth or otherwise. Momentum's finding in this bullet is
  unaffected.]**
- **A formal structural-break test qualifies both of Milestone 13's stories further
  (Milestone 14).** Momentum's "broke around 2008-09" claim was descriptive — the date was
  chosen by inspecting the data. A properly specified Chow test at the literature-motivated
  date (2008-09-01) does confirm a real level shift (p=0.026 daily) — but a Quandt-Andrews
  sup-Wald search that does *not* assume any break date finds its single best-fitting break
  27 months later (December 2010), and that unconstrained maximum is *not* statistically
  significant once corrected for having searched ~375 candidate dates via a 400-draw block
  bootstrap (p=0.138). The specific, externally-motivated hypothesis survives; an
  unconstrained "find the best break anywhere" search does not decisively confirm one
  dominant structural break. Reversal shows the opposite pattern: no evidence of a break
  near 2008 (p=0.34), but the unconstrained search finds a genuine, statistically
  significant break (bootstrap p=0.048) around **August 1980** — the sharp early decline
  from reversal's extraordinarily high late-1970s level, not a smoothly accumulating
  multi-decade slope. Treat both signals' "when did it break" story as more conservative
  and more precisely qualified than Milestone 13's descriptive framing. **[Since retracted
  for reversal: Milestone 15 investigated this August 1980 break directly and found it
  reflects a thin (2-4 stock), survivorship-biased, partly data-glitched early universe, not
  a real 1980 market event — reversal's alpha vanishes entirely from any start date at or
  after 1978, including 1980-08-29 itself (p=0.922). Momentum's break finding in this
  bullet is unaffected — the same diagnostic left it intact.]**
- **Momentum's 2008-09 break now has a concrete causal mechanism, not just a confirmed
  date (Milestone 16).** Applying this project's own look-ahead-free Bear × High-Volatility
  momentum-crash regression (Milestones 5-6, where it was rejected for the 52-week-high
  signal, full-sample) to momentum's hedged long leg, split at 2008-09-01: the interaction
  term is small and insignificant pre-2008 (p=0.42) but large, negative, and significant
  post-2008 (coef=-0.00218/day, p=0.008) — on the ~9% of post-2008 trading days that are
  both high-volatility and trailing-bear, the long leg loses at an annualized rate around
  37%. The classic momentum-crash mechanism this project rejected for the original signal
  turns out to be real for momentum specifically, but conditional on era: dormant through
  the pre-crisis decades, active since — consistent with a market where momentum-following
  capital had scaled up enough by 2008 for the mechanism to actually bite. **[Refined,
  not retracted, by Milestone 18: splitting "post-2008" into the 2008-09 crisis itself vs.
  2010-onward found the trailing-return bear flag never fired again after September 2009 in
  this sample — so the "active since" framing overstates what was tested. The mechanism is
  confirmed for the one bear market this sample's post-2008 window actually contains, not
  demonstrated to be a standing post-2008 feature. See "Was the 2008-09 crash mechanism a
  permanent regime change, or a one-off crisis?" below.]**
- **The momentum-crash mechanism does not replicate on NSE — but a more rigorous re-test
  finds a tentative NSE momentum signal a cruder test had missed (Milestone 17).**
  Milestone 8's "no significant NSE momentum alpha" used a static full-sample regression;
  applying the project's own rolling out-of-sample hedge (used for every US momentum test
  since Milestone 7) to NSE momentum for the first time reaffirms no significant alpha
  full-sample (daily p=0.170, monthly p=0.168), but surfaces a new, "promising, not
  confirmed" post-2008 signal (daily p=0.044, monthly p=0.073, marginal) — with the real
  caveat that NSE's universe itself grew from ~30 to 48 names over this window, so part of
  the improvement may reflect a less thin cross-section rather than a genuine regime
  change. **[Downgraded by Milestone 21: testing this exact caveat found neither the
  growing-universe sub-period nor the fully universe-stable sub-period significant on its
  own — the full-window significance is a pooling artifact, not evidence of a genuine,
  sub-period-independent signal. See "Does the tentative NSE signal survive its own named
  caveat?" below.]** Separately, Milestone 16's exact Bear × High-Vol interaction is never significant
  on NSE (p=0.96 full-sample) — the specific crash-*rebound* mechanism found for US
  momentum does not generalize. NSE does show a plain, unconditional Bear effect instead
  (loses significantly in any trailing bear market, p=0.002 full-sample) — a related but
  mechanistically different, more generic bear-market sensitivity.
- **Milestone 16's "post-2008 crash regime" is really "the one crisis in the post-2008
  window," not a standing feature — and in isolation, the interaction term itself is not
  what's significant (Milestone 18).** Splitting the post-2008-09 block at 2009-12-31: the
  US mirror's trailing-12-month market return never went negative again after September
  2009, all the way through the end of its coverage (Nov 2017) — the 2011 and 2015-16
  selloffs both recovered before the 252-day lookback registered them as sustained bear
  states. That means Milestone 16's "post-2008" test is entirely carried, for the
  interaction term, by the 337-day 2008-09 crisis window; the other ~2,000 post-crisis days
  contribute zero Bear+High-Vol observations, so the interaction cannot even be estimated
  there (rank-deficient regression). Worse for the "interaction" framing specifically: run
  on the crisis window alone, the multiplicative term itself is *not* significant
  (p=0.26 long leg, p=0.31 combined) — high volatility alone (p<0.0001) and the bear flag
  alone (p=0.036-0.005) do the work instead. Read Milestone 16's finding as: real for the
  2008-09 crisis specifically, evidence for volatility and bear-state each mattering
  independently more than for their interaction being the mechanism, and untested — not
  disconfirmed — as a standing post-2008 regime, since no comparable bear market has
  recurred in this sample to test against. **[Qualified by Milestone 19: this "no comparable
  bear market" claim itself depends on the 252-day (~1-year) trailing-return lookback this
  project has used since Milestone 5. At shorter, equally standard lookbacks (126 or 189
  trading days, ~6-9 months), a bear regime *does* fire post-2010 — 200 and 47 days
  respectively, clustered in 2010-11 and 2015-16 — so "no bear market recurred" is a
  lookback-dependent claim, not a lookback-independent fact. See "Does the crash-mechanism
  finding survive different regime-construction choices?" below.]**
- **The crash-mechanism *pattern* (dormant pre-2008-09, active post) replicates across most,
  but not all, nearby regime-construction choices — and the specific claim that no bear
  market recurred after 2009 does not (Milestone 19).** Sweeping a 4×4 grid of volatility
  windows (10/21/42/63 days) and bear-market lookbacks (126/189/252/378 days): the
  Milestone 16 pattern holds in 8 of 16 combinations, reliably (3 of 4 lookbacks) at this
  project's own default 21-day volatility window and the adjacent 42-day window, but never
  at the shortest 10-day window and rarely at the shortest 126-day bear-lookback. The
  default parameter combination Milestones 16-18 actually used sits inside the reliable
  region, not at a cherry-picked edge case. But the bear-regime-frequency finding
  underlying Milestone 18 is fragile: a bear regime fires post-2010 at both shorter
  lookbacks tested (126 and 189 days) and never at the two longer ones (252, this project's
  default, and 378) — so whether the crash mechanism has a "second data point" to test
  persistence against depends on which standard convention is chosen, and that persistence
  test has not yet been re-run under the lookbacks where a second bear regime exists.
  **[Closed by Milestone 20: re-run under both alternate lookbacks, the mechanism did not
  reactivate — see below.]**
- **The crash mechanism did not reactivate in 2011 or 2015-16, even once real bear-regime
  days exist to test it against (Milestone 20).** Re-running the Bear × High-Vol
  interaction on the 2010-onward window under the two lookbacks (126 and 189 days) where a
  bear regime actually recurs: the interaction is not significant at either window
  (p=0.203 at 126 days, p=0.443 at 189 days), despite 148 and 31 Bear+High-Vol days
  respectively to test it against. At the 189-day lookback the bear-market main effect *is*
  significant (p=0.023) but positive — momentum's long leg did somewhat better, not worse,
  during those trailing-bear periods, the opposite sign from both the 2008-09 crisis
  coefficient and what the crash-risk mechanism predicts. This strengthens, rather than
  merely leaves open, Milestone 18's "confirmed for one crisis" framing: the mechanism is
  now tested and not found outside 2008-09, not just untested. Whether it would reactivate
  in a genuinely severe future crisis, as opposed to the milder 2011 and 2015-16 episodes,
  remains open — this sample has not contained one since 2009.
- **The tentative NSE post-2008 momentum signal (Milestone 17) does not survive splitting
  by universe stability — its own named caveat, finally tested (Milestone 21).** NSE's
  universe grew from ~30 names in 2000 to a fixed 48 by 2010-11-04, then stayed at exactly
  48 names every day through the end of the sample. Splitting Milestone 17's post-2008
  window at that date: the growing sub-period (2008-09 to 2010-11, n=535 days) shows a
  *larger* point estimate (+23.72%/yr) than the full window but is not significant
  (p=0.112) on its own; the fully stable, fixed-48-name sub-period (2010-11 onward, n=2,579
  days) shows a smaller point estimate (+4.60%/yr) and is also not significant (p=0.180).
  Neither direction of the growth-confound concern is confirmed — the growing years are not
  where the significance is concentrated — but a different, arguably more serious problem
  is: the full-window significance (p=0.044) exists only when the two sub-periods are
  pooled, echoing the exact pooled-window lesson Milestones 18-20 learned about the crash
  mechanism, applied here to this project's own remaining open finding. **The NSE post-2008
  signal should now be read as not currently demonstrated, not merely as an unconfirmed but
  promising thread.**
- **Momentum replicates on a third, independent market (ASX Australia), the cleanest result
  of the three tested — but on this project's shortest history, and finding the market at
  all took real effort (Milestone 22).** A thorough search for a European per-company OHLCV
  mirror found none reachable from this sandbox; `stooq.com`, `huggingface.co`,
  `github.com`'s own HTML pages, and general `api.github.com` repo browsing are all
  blocked, and several candidate repositories turned out to be fetch-at-runtime pipeline
  code (also blocked), not committed data. `grantcarthew/data-asx-historical-share-tables`
  — a mirror of ASX's own daily S&P/ASX300 report emails, 2009-10-20 to 2015-12-31 — was
  the source that worked. Applying this project's out-of-sample hedge and HAC significance
  test directly (not the cruder full-sample regression Milestones 6-8 started with):
  long-leg alpha +11.14%/yr daily (p=0.0085) and +9.97%/yr monthly (p=0.0141); the combined
  book shows an even larger, still-significant effect (p<0.001 both frequencies), plausibly
  tied to Australia's 2011-2015 mining-sector downturn loading the short leg with
  high-beta losers (mean short-leg beta −1.26 vs. the long leg's +0.83) rather than being a
  hedge-instability artifact (rolling beta std 0.39, no extreme outliers). **This is a real
  limitation, not just a caveat**: six years is enough for a full-sample significance test
  but not for the era-splits, structural-break tests, or persistence checks Milestones 9-14
  ran on the US mirror's 47-year history — ASX momentum has not yet been checked for
  stability across sub-periods the way every other surviving finding in this project has.
- **52-week-high shows significant hedged alpha on ASX — reopening, not confirming, a
  question Milestones 6-7 called resolved — but it is highly correlated with momentum's own
  ASX result, not clearly a second independent edge (Milestone 23).** Milestones 6-7 found
  52-week-high's NSE/US "edge" was entirely a beta-construction flaw: zero significant
  alpha in 12 of 12 hedged regressions across both markets. On ASX, the hedged combined
  book is significant at both frequencies (p=0.0126 daily, p=0.0023 monthly) — the alpha
  survives the hedge this time, a different failure mode than before. But 52-week-high's
  and momentum's ASX leg returns correlate at 0.76 (long leg) and 0.82 (combined book), and
  the short leg's mean beta (−1.36) closely matches momentum's own (−1.26) — both signals
  are substantially picking the same names, consistent with both simply capturing
  Australia's 2011-2015 mining-sector divergence rather than 52-week-high anchoring being an
  independent behavioral edge on this market. Reversal, tested alongside it, shows nothing
  (p=0.49-0.82 across all four cuts) — a clean confirmation of its established null, needing
  no further qualification. **Treat 52-week-high's ASX result as open and
  mechanism-ambiguous, not as a second confirmed ASX anomaly alongside momentum** — the
  natural next check (momentum as an explicit control in the same regression) has not yet
  been run. **[Closed by Milestone 24: run directly, momentum as an explicit control fully
  explains 52-week-high's ASX alpha — see below.]**
- **ASX 52-week-high carries no skill independent of momentum, confirmed directly rather
  than inferred from a correlation coefficient (Milestone 24).** Regressing 52-week-high's
  out-of-sample-hedged returns on momentum's own hedged returns: 52-week-high's intercept
  (alpha net of momentum exposure) is not significant at any of the four cuts (long leg
  p=0.318 daily, p=0.349 monthly; combined book p=0.747 daily, p=0.936 monthly), while
  momentum's own coefficient is highly significant everywhere (p≤0.017, and p<0.0001 for
  the combined book, which momentum alone explains R²=0.60-0.66 of). This decisively
  confirms Milestone 23's "same mechanism" reading rather than merely leaving it plausible:
  ASX 52-week-high's apparent edge is momentum's own alpha viewed through a highly
  correlated construction, restoring the same "no independent skill demonstrated" verdict
  Milestones 6-7 reached on NSE and the US mirror — reached here by a direct control
  regression rather than a beta hedge, but landing at the identical conclusion.
- **The low-volatility anomaly does not replicate positively on any of the three markets,
  and significantly inverts on the US mirror — a genuinely new, distinct negative result,
  not a repeat of reversal's or 52-week-high's story (Milestone 25).** Testing a newly
  built signal (`signals/low_volatility.py`, long the calmest decile, short the most
  volatile) with this project's out-of-sample hedge and HAC test on all three markets at
  once: NSE shows nothing (p=0.67-0.94 across all four cuts); ASX shows a real but modest
  long-leg-only signal (p=0.0099 monthly, p=0.090 daily; combined book not significant);
  the US mirror shows the strongest result of all, running the wrong way — the hedged
  combined book loses 20.70%/yr daily and 18.09%/yr monthly, both p<0.001, meaning
  high-volatility names significantly *outperformed* low-volatility ones net of beta over
  1970-2017. Checked against the obvious confound given this project's own history with
  this exact dataset (Milestone 15's pre-1985 thin-universe problem): re-running from ten
  different start dates, the inversion holds, significant or near-significant, from 1978
  through 1995, weakening only from a 2000 start — not a thin-universe artifact. **This
  should not be filed alongside momentum as a second working signal, nor alongside reversal
  and 52-week-high as a cleanly retracted one — it is its own distinct negative result: a
  well-documented academic anomaly this project's data does not support, and on its
  best-tested market, actively contradicts.**

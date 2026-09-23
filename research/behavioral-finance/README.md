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
- **Short-term reversal is the one signal that actually worked, gross and net of costs.**
  Consistent with reversal being one of the more robust anomalies in the academic
  literature, plausibly because it's closer to a liquidity-provision premium than a pure
  behavioral bet, so it survives in large, liquid names better than underreaction-based
  momentum does — though see the US replication below, where this result does **not** hold up.

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
  not the US one.
- **Short-term reversal does *not* replicate either — it's much weaker here** (Sharpe 0.07
  net vs. 0.22 net on NSE). So of the three individual signals, *none* of them showed a
  consistent, cross-market edge in the same direction except the negative one (52-week-high).
  That is itself a finding: a signal-selection process that only looked at one market (NSE)
  would have wrongly concluded reversal was the reliable edge and momentum was dead — the
  opposite of what a US-only study would have concluded. **Universe/market choice changes
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
  US Kaggle mirror" above. Both mirrors are the sources actually exercised in this repo.
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

# Tests (synthetic fixtures — no internet needed)
pytest tests/ -v
```

## Concrete, applicable outputs

This research is designed to feed three deliverables (full detail in `../FRAMEWORK.md`):

1. **An investment framework** — a composite behavioral mispricing score usable as a
   screening/tilt signal alongside fundamental analysis, now with real empirical caveats
   attached (see "Empirical results" and "Is it just beta?" above): don't trust it blind on
   a large-cap-only universe, check which sub-signal is actually carrying any edge before
   combining them, and beta-neutralize long-short legs before crediting any performance
   difference to a behavioral effect rather than to uncontrolled market exposure.
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

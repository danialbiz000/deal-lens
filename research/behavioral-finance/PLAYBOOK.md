# Position-Sizing & Risk-Budget Playbook

**What this is.** Every one of this project's 53 research milestones answers a
statistical question: is a signal real, does it survive correction, how
uncertain is a given number. None of them answer the question a capital
allocator actually has to answer: *how much, how, and with what stop rules*.
This document is that translation — the first deliverable in this project
built for someone deploying real capital, not for continuing the research.

**What this is not.** Not a new statistical finding. Every number below is
already published in `README.md` / `FRAMEWORK.md` / the project guide PDF;
this document adds no new test and runs no new script. It also is not
investment advice — it is an honest translation of what 53 milestones of
stress-testing this project's own one surviving recommendation actually
support, written by the same process that spent the last several milestones
finding out how much of that recommendation doesn't survive scrutiny.

**Audience.** Someone who has read (or will read) the research and is
deciding whether, and how, to actually allocate capital to the combined book
— ASX momentum (long-short, monthly decile rebalance) + NSE turn-of-month
(long-only-or-cash, ~12 calendar windows/year), 50/50 notional, the project's
one standing recommendation since Milestone 45.

---

## 1. What is and isn't proven — read this before anything else

| Claim | Status |
|---|---|
| ASX momentum has a real, out-of-sample-hedged long-leg edge | **Established.** Survives cost realism (to 200bps, 20x baseline), sub-period stability, multiple-testing correction, and the crash-regime-interaction test (Milestones 24-25, 34-35, 41, 48). |
| NSE turn-of-month has a real calendar edge | **Established, with a decay caveat.** Full-sample and the specific 2010-11/2015-11 window both significant; the *long-run* pattern (Milestone 38) is decay toward insignificance in the most recent 15-16 years system-wide — the live window used here sits before that decay fully sets in (Milestone 52), but the trend direction is down. |
| The two legs are genuinely uncorrelated | **Established.** Correlation +0.0197, 90% CI (-0.03, +0.07) — tight around zero (Milestone 49). |
| The combined book's Sharpe improvement over the better single leg (+0.32) | **NOT proven.** 90% CI (-0.14, +0.47); one-sided P(improvement ≤ 0) = 0.108 (Milestone 49). Treat as plausible, not real, until more overlapping history accumulates. |
| ASX momentum's edge would survive if deployed today | **Untestable with this project's own data.** ASX mirror ends 2015-12-30; the live window already consumes the full usable sample (Milestone 52). No walk-forward confirmation exists past that date. |
| NSE turn-of-month's edge was real in advance, not hindsight | **Established.** Significant using only pre-window data, p<0.0001 (Milestone 52). |
| The crash-regime mechanism behind momentum's own worst historical loss | **Does not survive correction.** Raw p=0.0081, BH-adjusted p=0.1384-0.1547 (Milestone 47) — independently supported by the literature (Daniel & Moskowitz 2016) but not, on its own, by this project's data at a corrected significance level. |
| Turn-of-month carries no crash-regime risk | **Established** (clean null, p=0.41-0.71) — but **carries real, unconditional fat-tail risk** on its own invested days (99.9% CVaR ratio up to 1.89x, larger than momentum's own 1.71x) that a crash-regime test alone would never show (Milestone 53). |
| Capacity — how much capital this could actually absorb | **Never tested.** No market-impact data source exists for any of this project's three markets (Milestone 35's own confirmed gap). Treat every number below as *return-series* economics, not capacity-adjusted economics. |

If you read nothing else: the mechanism behind this combination is real
(independence, no shared crash risk) and the magnitude is not (the specific
Sharpe improvement, the specific crash-mechanism explanation). Size
accordingly — against the worse case the data can't rule out, not the point
estimate.

---

## 2. Position sizing

### 2.1 Starting point: the book's own realized volatility, unlevered

Over the same window used throughout this project (2010-11-01 to
2015-11-30, the only window where both legs' historical data overlap):

| | Ann. return | Ann. vol | Sharpe | Max drawdown |
|---|---|---|---|---|
| ASX momentum alone | +31.77% | 17.24% | +1.69 | -16.50% |
| NSE turn-of-month alone | +8.18% | 6.54% | +1.24 | -7.63% |
| **Combined 50/50 (unlevered)** | **+19.90%** | **9.28%** | **+2.00** | **-9.01%** |

At its own natural 50/50 notional weighting, the combined book already sits
at a moderate ~9.3% annualized volatility — in the typical range targeted
for a systematic satellite sleeve (commonly 8-12%) without any leverage
decision required. **No leverage is recommended here.** Levering a book
whose headline diversification benefit has a 90% CI including zero would
compound an unproven number, exactly the mistake this project's own
uncertainty-propagation milestones (49-51) exist to warn against.

### 2.2 Size against the CI, not the point estimate

The Sharpe figures above are historical point estimates on a short,
overlapping 5.25-year window. Two things this project found should directly
discount how much weight a point estimate deserves:

- The **diversification benefit's own 90% CI reaches +0.47 at best and -0.14
  at worst** (Milestone 49) — i.e., there is a real, non-trivial chance the
  combined book's advantage over just holding ASX momentum alone is zero or
  negative, once more data accumulates.
- **ASX momentum's own forward validity past 2015 is unverified** (Milestone
  52) — the single largest, highest-volatility leg in this book has not
  been checked against a single day of out-of-sample data beyond the
  window its own backtest was built on.

**Sizing rule**: budget risk as if the achievable Sharpe is the *worse
single leg's own standalone Sharpe* (+1.24, NSE turn-of-month, the lower of
the two legs), not the combined +2.00. Treat anything above that as upside
optionality the diversification benefit may or may not deliver, not
as a sizing input. This is a deliberate, conservative judgment call — not a
number this project's own statistics derive mechanically — made because the
alternative (sizing to the point-estimate Sharpe) treats a number with a CI
spanning zero as if it were certain.

### 2.3 Concrete allocation range

For a risk-capital sleeve already earmarked for systematic / alternative
strategies (not core portfolio capital): **5-15% of that sleeve**, starting
at the low end.

- Start at **5%** until at least 12 months of live, out-of-sample monitoring
  data exists (see Section 5) confirming the realized correlation and
  Sharpe improvement are tracking inside their established CIs.
- Scale toward **15%** only if that monitoring period confirms the
  diversification benefit is behaving as the point estimate suggested, not
  as the lower bound of its CI.
- **Never exceed 15%** of the alternatives sleeve on the strength of this
  project's own backtested numbers alone — a single combined book built
  from two markets, one of which (ASX) cannot be forward-validated with
  available data, is not a basis for a larger allocation regardless of its
  backtested Sharpe.

This range is a sizing judgment grounded in the uncertainty this project
actually quantified (the CI widths in Sections 1 and 2.2), not a formula
output — stated explicitly as such rather than dressed up with false
precision.

---

## 3. Risk limits and circuit breakers

Three tiers, each tied to a number this project actually measured, not a
round figure chosen for convenience.

### 3.1 Routine drawdown review trigger

The combined book's own historical max drawdown (same window) was **-9.01%**.
**Trigger a position review (not automatic liquidation) if the live combined
book's drawdown from a rolling 12-month high exceeds 1.5x that figure
(~-13.5%).** A breach does not necessarily mean the edge has failed — it
means the live book is now outside its own backtested historical range and
warrants the same scrutiny this project has applied to every number in its
own history before trusting it further.

### 3.2 Turn-of-month single-occurrence tail trigger

Turn-of-month is flat/cash most days and only exposed on ~4-day windows
around each month boundary — a smooth rolling-drawdown metric will rarely
catch a bad occurrence before it's already happened. Use the signal's own
measured tail instead: Milestone 53 found a 90% bootstrap CI on the 99.9%
CVaR of **(4.919%, 6.191%) on NSE** and **(5.320%, 7.799%) on the US
mirror** (a reference comparison, not a traded leg here) for single-day
losses on days the strategy is actually invested.

**Trigger an immediate review of the turn-of-month leg specifically if any
single turn-of-month-window day loses more than 6%** (the upper end of
NSE's own measured range) — this is a realized tail event, not routine
variance, and the position should be reduced to cash for that leg until
reviewed rather than held through the rest of the current window on the
assumption the edge is unaffected.

### 3.3 Severe-regime stress scenario — know the range, don't predict from it

Milestone 50 propagated the crash-regime coefficient's own estimation
uncertainty through a duration-multiplier stress simulation for momentum's
long leg. These are **scenario bands conditional on an assumed regime
persistence, not probability-weighted forecasts** — included here so an
allocator knows the shape of the tail this project's own data can describe,
not to imply any of these durations is expected:

| Duration (vs. 2008-09's own 196-day episode) | Propagated 90% interval, momentum long leg |
|---|---|
| 1x (196 trading days) | (-40.4%, -6.8%) |
| 2x (392 trading days) | (-62.2%, -18.3%) |
| 3x (588 trading days) | (-76.2%, -29.2%) |
| 4x (784 trading days) | (-84.9%, -37.5%) |

**If the project's own Bear+HighVol regime dummy signals an active crash
regime that persists materially longer than 196 trading days (the entire
2008-09 crisis), treat the ASX momentum leg's downside as open-ended within
this table's ranges, not as bounded by the historical worst case.** Note
also (Section 1) that the coefficient behind this mechanism does not survive
multiple-testing correction — this table is this project's best honest
description of a tail scenario, not a validated forecast, and should be
read with that caveat attached every time it's used.

---

## 4. Execution constraints

| Leg | Rebalance cadence | Cost sensitivity | Implication |
|---|---|---|---|
| ASX momentum | Monthly decile rebalance | Robust to 200bps (20x this project's 10bps baseline) | Cost is not a binding constraint — any reasonably liquid access to the ASX-200-style universe is adequate. |
| NSE turn-of-month | ~12 entry/exit cycles/year, ~4-day windows | Significance crosses zero between 25-50bps round-trip (Milestone 44) | **Requires sub-25bps round-trip execution to stay inside the validated regime** — use liquid index futures or ETF proxies, not individual-stock execution through a high-friction retail channel. A venue that cannot clear this bar should not run this leg at all; the edge is real at low cost and gone well before 50bps. |

The two legs rebalance on independent, unsynchronized calendars. Operate
them as two parallel sub-strategies under one combined risk budget (Section
2), not as a single unified rebalance process.

---

## 5. Forward monitoring — what to track once live

This project's own standing practice is to re-check every number against
fresh scrutiny rather than trust a backtest indefinitely. The same applies
here, now that there is a live recommendation to monitor rather than only a
backtest to audit:

1. **Realized leg correlation vs. the established 90% CI (-0.03, +0.07)**
   (Milestone 49). Sustained drift outside this band is the first sign the
   "genuine independence" premise behind the whole combined-book case may be
   eroding.
2. **Realized Sharpe improvement over the better single leg vs. the
   established 90% CI (-0.14, +0.47)** (Milestone 49). This is the single
   most important number to track — it's the one the backtest could not
   prove, so live data is the only way to eventually learn whether it's real.
3. **Fresh ASX data, the moment any becomes available.** This project's ASX
   mirror ends 2015-12-30; every month of new data is a genuine, never-run
   out-of-sample test of the one leg that could never be walk-forward
   validated here (Milestone 52). This is the single highest-value piece of
   data collection this project could not do and a live deployment can.
4. **Whether NSE turn-of-month's long-run decay (Milestone 38) continues.**
   The live window used in this book predates the system-wide decay fully
   setting in; if the live, forward-traded add-on weakens toward the
   insignificant levels Milestone 38 found in its own most recent
   sub-period, that is this project's own documented pattern repeating, not
   a surprise, and should trigger a reduction in the turn-of-month leg's
   weight specifically.

---

## 6. Explicit do-not list

- **Do not lever the combined book** based on the point-estimate Sharpe
  (+2.00) alone — Section 2.1-2.2.
- **Do not treat the ASX leg as walk-forward-validated.** It cannot be, with
  this project's own available data — Section 1, Section 5.3.
- **Do not execute the turn-of-month leg through a high-cost channel.** The
  edge is gone by 50bps round-trip — Section 4.
- **Do not read the Section 3.3 stress table as a forecast.** It is a
  conditional scenario band built on a coefficient that does not survive
  multiple-testing correction, included for honesty about the tail, not as
  a probability-weighted prediction.
- **Do not assume the current significance of NSE turn-of-month reverses its
  own long-run decay trend.** The live window happened to predate the
  system-wide decay fully setting in (Milestone 52); that is a fact about
  timing, not a reason to expect the edge to persist indefinitely.
- **Do not treat a clean crash-regime result as a clean bill of health** for
  any leg. Turn-of-month passes the crash-regime test and still carries real
  fat-tail risk (Milestone 53) — the two are different questions with
  different answers, and both need checking for any leg, old or new.

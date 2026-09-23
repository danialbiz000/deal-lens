# From research to practice: framework, risk playbook, and product idea

This document translates the research in `README.md` / `case_studies/` /
`signals/` / `risk_simulation/` into the three concrete outputs the project was
scoped for: an investment framework, risk-management lessons, and a
business/product idea.

## 1. Investment framework: the Behavioral Mispricing Score

**What it is.** `signals/composite.py` combines three independently-documented
behavioral anomalies — 12-1 month momentum (underreaction), 52-week-high
proximity (anchoring), and 1-month reversal (overreaction) — into a single,
cross-sectionally z-scored composite per stock per day.

**How it's meant to be used**, based on how Fuller & Thaler / LSV / AQR
actually deploy signals like this (see `case_studies/behavioral_funds.md`):

- **Not as a standalone strategy.** Every fund in the case studies pairs
  behavioral signals with fundamental discipline (value screens, quality
  filters, sector/beta neutralization) rather than trading the raw signal.
  The natural use is a **tilt or flag layered on top of an existing
  fundamentals-driven screen**, not a replacement for it: a stock that
  screens well fundamentally *and* sits in the top behavioral decile is a
  stronger candidate than either signal alone; a stock flagged as a
  behavioral "loser" is worth a second look before initiating or sizing a
  position, even if fundamentals look fine.
- **Decile, not point-estimate.** Treat the score as a rank, not a precise
  number — the whole point of `backtest/engine.py`'s decile-sort methodology
  is that the edge shows up in the spread between the extreme deciles, not in
  any single stock's score being "correct."
- **Never trust the blend without checking its parts — this is now a proven
  failure mode, not a hypothetical one.** The NSE empirical run
  (`README.md`, "Empirical results") shows exactly why: the *composite*
  score looked like a mediocre, roughly break-even signal (Sharpe ≈ 0), and
  stopping there would have been a reasonable-looking but wrong conclusion.
  Decomposing it showed the composite was averaging together one signal that
  actively lost money (52-week-high) with one that *looked* like a real,
  positive edge net of costs (short-term reversal, Sharpe 0.22 net) — a
  conclusion Milestone 8 later retracted (next section). **Rule: always
  report and validate each component signal separately before trusting a
  blended score, and re-weight or drop components that don't independently
  earn their place** — and note that "looks like an edge in the initial
  decomposition" is still not the same as "is a demonstrated edge" (see
  below).
- **Re-validate on each new universe before trusting it there — now confirmed necessary,
  not just prudent.** A second market (US large-caps, 1970–2017) was run through the same
  pipeline (`README.md`, "Replication on a second market"), and momentum and reversal
  **flipped which one looked real**: reversal was NSE's edge and the US's near-zero result;
  momentum was NSE's near-zero result and the US's real edge. Only the 52-week-high
  signal's *loss* was consistent both times. **Rule: a single-market backtest result is
  provisional by default — run it on at least one independent market before including it
  in a live framework, and expect roughly a coin-flip's chance that a specific component
  signal's sign won't hold.** (Milestone 8 later showed the US momentum side of this flip
  was the real one — see below.)
- **A component that survives decomposition should still survive a "why" check before
  being trusted as a real edge or discarded as a real problem.** The 52-week-high signal's
  loss looked at first like it might be a value/growth confound specific to India's bull
  market; a direct test (orthogonalizing against a value proxy, `README.md`
  "Investigating the 52-week-high result") rejected that explanation in both markets. The
  loss is real and not an artifact of an unrelated factor — which makes it more, not less,
  important to keep this specific signal excluded from the composite until its true cause
  is understood.
- **Decompose the legs before discarding a signal — still correct, but the fix isn't
  "long-only" after all.** `README.md`, "Testing momentum-crash risk directly," decomposed
  the 52-week-high signal's long and short legs and found the long leg's raw average
  return significantly positive, the short leg's significantly negative, in every
  specification (Milestone 5). **Rule: don't discard a component signal wholesale because
  its long-short backtest lost money — decompose the legs first.** That rule still holds;
  what it was used to conclude did not (next bullet).
- **The actual cause, found last, was the most basic check: an uncontrolled beta
  mismatch.** Milestone 4's crash-risk story looked compelling descriptively; Milestone 5
  formally rejected it (no significant regime-conditioning in the short leg, either
  market). Milestone 6 then ran the check that should have come *first* — a CAPM regression
  of each leg against the market — and found it: the long leg carries ≈+0.8 market beta,
  the short leg ≈−1.2 to −1.4, leaving the combined book significantly net short-beta
  (−0.32 to −0.70, every cut) in markets that returned ~20%/year over the sample. Once beta
  is controlled for, **alpha is insignificant in all 12 regressions run — both legs, both
  markets, both frequencies.** There is no demonstrated stock-selection skill in this
  signal, long or short, once its uncontrolled market exposure is accounted for. **Rule,
  corrected from the "long-only" conclusion above: this signal is not currently a
  demonstrated source of alpha in either direction.**
- **Milestone 6's regression alpha was independently confirmed, not just re-derived, by
  actually building and testing a hedged version.** A single full-sample regression
  coefficient could in principle have missed a real, time-varying alpha. Milestone 7 built
  the real thing instead: a rolling, strictly out-of-sample beta hedge (re-estimated every
  rebalance from only the preceding ~year of data, applied forward, never using data from
  the period being hedged — the way a real fund would operate it). The hedge cut the
  correlation with the market from strongly negative to near zero and roughly halved the
  loss in both markets — but the residual return remained statistically indistinguishable
  from zero everywhere (p between 0.17 and 0.45). **Rule: when a regression finds no alpha,
  don't stop there if the claim matters — build the actual hedged strategy and test the
  real thing. In this case the two methods agreed, which is what makes the "no alpha"
  conclusion trustworthy rather than an artifact of one modeling choice.** A live version of
  this signal would still need beta-neutralized position sizing (not just a market-return
  overlay) and would face real hedging transaction costs, given the rolling beta itself is
  quite unstable over time in both markets — not modeled here.
- **Check for a beta mismatch between the legs before reaching for a behavioral
  explanation — not after three milestones of chasing more exotic ones.** This project
  tested crash-window concentration, a value/growth confound, and formal momentum-crash
  regime-conditioning — all before checking whether the two legs were even beta-matched.
  They weren't, and that single, mechanical omission fully explains what the other three
  hypotheses were built to explain. **Rule: for any long-short backtest, run the CAPM
  regression on each leg first. It is cheaper than any of the alternatives and, in this
  project's own case, was the one that actually had the answer.**
- **A compelling descriptive pattern is a hypothesis, not a finding, until it's been
  tested formally.** The Milestone 4 → 5 → 6 sequence is a worked example of exactly this,
  twice over: a regime-bucket comparison that looked like strong evidence collapsed under
  formal significance testing, and the formally-tested-but-still-uncontrolled decomposition
  itself collapsed once a basic beta check was added. **"Formally tested, not confirmed" and
  "explained by something more basic" are both genuinely weaker claims than "strongly
  supported," even when the same underlying numbers motivated all three. Report the
  weakest claim that's actually been earned, and keep checking simpler explanations even
  after a more sophisticated one has passed one round of testing.**
- **Apply the same scrutiny to a positive finding as to a negative one — this project had
  been letting its one "success" coast on an old conclusion.** Every beta check through
  Milestone 7 was run on the 52-week-high signal, the one that *lost* money. Short-term
  reversal — this repo's original, and only, reported positive edge — was never re-examined
  the same way. Milestone 8 finally did, and it didn't survive: none of reversal's 12 alpha
  tests (2 markets × 3 legs × 2 frequencies) are significant. **Rule: a positive finding
  earns no exemption from the checks a negative one gets. If a signal was "confirmed"
  before the project's own standards of rigor caught up with it, re-run it under the
  current standard before continuing to cite it.**
- **When the same rigor finally turns up a real positive, that's worth saying plainly, not
  hedging into meaninglessness.** Milestone 8 also tested 12-1 momentum the same way, and
  found something the earlier milestones hadn't: on the US mirror, momentum's long leg and
  combined book show large, highly significant alpha (annualized ≈+8-15%/yr, p<0.01 in
  every cut) with a combined-book beta close to zero. Unlike the isolated marginal p≈0.03
  hits Milestone 5 correctly dismissed as consistent with pure chance, this is a **coherent
  cluster** — same signal, same market, same direction, significant across both legs and
  both frequencies — a qualitatively different and much less noise-like pattern. **Rule: a
  cluster of consistent, high-significance results across related cuts of the same
  hypothesis is stronger evidence than an isolated hit, even before running a formal
  multiple-testing correction; don't apply the same "probably noise" discount to a coherent
  finding that's appropriate for a scattered one.** This is currently this project's single
  most credible candidate for a genuine, demonstrated edge — with the caveat that it is one
  market, unreplicated on NSE, and not yet checked for the publication-decay risk this
  project's own README has flagged since its first commit (momentum was published in 1993;
  a pre/post-1994 sub-sample split has not been run). Promising, not confirmed.

## 2. Risk-management lessons

Derived directly from `risk_simulation/fat_tails_vs_normal.py` and
`case_studies/ltcm_1998.md` / `quant_quake_2007_and_amaranth.md`:

1. **Never calibrate tail risk on a calm-regime correlation matrix alone.**
   The simulation shows a Gaussian VaR model calibrated on "normal" data
   underestimates the true 99.9% tail loss by ~1.3x and the expected
   shortfall beyond it by ~1.65x, purely because it can't see correlations
   rising toward 1 under stress. Any leveraged or market-neutral strategy
   needs a **stress correlation matrix as a second scenario**, not just a
   historical-calibration VaR number.
2. **Leverage doesn't just scale losses, it changes which losses are
   survivable.** LTCM's underlying spread moves were not physically
   unprecedented; 25:1+ leverage turned a bad quarter into a solvency event.
   Position-size and leverage limits should be set against the
   *stress-regime* tail estimate, not the calm-regime one.
3. **Crowding is a correlation risk you can't see in your own book.** The
   2007 Quant Quake shows that even a well-diversified-looking portfolio can
   be secretly correlated with every other fund running a similar signal.
   A practical mitigant: track how "crowded" a factor is (e.g., aggregate
   assets tracking similar signals, or a simple proxy like realized
   correlation of your strategy's returns to a public momentum/value index)
   and de-risk when crowding is high, independent of your own model's
   confidence.
4. **A winning streak is not evidence against tail risk.** Amaranth's Brian
   Hunter had a strong track record before the 2006 blowup; recent success
   under one regime is weak evidence that a concentrated position is safe
   under a different one. Any framework that sizes positions partly on
   trailing Sharpe or recent P&L needs an explicit override for
   concentration limits that doesn't relax just because a book has been
   working.
5. **Treat "the model says it's fine" as a hypothesis, not a fact**,
   especially near known regime-change triggers (sovereign defaults,
   liquidity crunches, crowded-factor unwinds) — which is really the
   project's whole thesis applied to your own tooling, not just to the
   market you're modeling.
6. **The Q1 mechanism and the Q2 investigation asked the same question — Q1 answered it
   with a simulation, Q2's real data gave a more honest, weaker answer.**
   `risk_simulation/fat_tails_vs_normal.py` showed, in a stylized simulation, that tail
   risk compounds specifically when volatility and correlation rise together. `README.md`'s
   momentum-crash-risk investigation set out to find the same signature in a real
   backtest, and a first descriptive pass (Milestone 4) looked like it had. Formal
   significance testing (Milestone 5) did not confirm it. **Any short position built on
   a behavioral signal should still be regime-tested before being sized** — that
   precaution doesn't depend on this specific mechanism being confirmed — but "regime-
   tested" has to mean the HAC-regression version, not the regime-bucket version, given
   what happened here when the two disagreed.
7. **A compelling descriptive pattern is a hypothesis, not a finding — this project
   produced its own cautionary tale.** Milestone 4's regime-bucket comparison (Sharpe by
   volatility tercile, bull vs. bear) looked like a clean, four-signature confirmation of
   momentum-crash risk. Formal HAC-regression testing at daily and monthly frequency
   (Milestone 5) found none of the regime-conditioning coefficients significant in the
   leg the theory actually predicts (the short leg), in either market. Both analyses used
   the same underlying data; only the statistical rigor differed. **Rule: never size a
   position, write a risk limit, or make a claim in a report based on a descriptive
   regime split alone — run the regression with proper standard errors first, and expect
   a real chance that the compelling-looking pattern won't survive it.**
8. **The cheapest test is the one to run first, and this project ran it last.** Three
   escalating hypotheses (crash-window concentration, a value/growth confound, formal
   momentum-crash regime-conditioning) were tested across Milestones 2, 3, and 5 before
   Milestone 6 finally ran a plain CAPM beta regression — the single cheapest, most
   standard check for any long-short book — and found the entire answer in it: an
   uncontrolled beta mismatch between the legs, fully explaining every prior milestone's
   numbers, with no behavioral story needed. **Rule: order your hypothesis tests from
   cheapest/most-mechanical to most-exotic, not the reverse. A beta regression takes
   minutes and rules out (or in) the most common cause of "surprising" long-short
   performance; save the behavioral and regime-conditioning hypotheses for after it comes
   back clean.**
9. **A risk process that only re-tests its losers eventually trusts a winner it never
   should have.** Every rigor upgrade in this project (Milestones 4-7) was applied to the
   signal that was losing money. The one signal reported as a genuine edge (reversal) rode
   on its original, less rigorous validation for six milestones before anyone checked it
   the same way. Milestone 8 found it didn't hold up. **Rule: schedule periodic re-validation
   of every "confirmed" edge under your *current* standard of rigor, not just your
   standard at the time it was confirmed — a standard that improves over the life of a
   book (as this project's did) should apply retroactively, especially to the positions
   still being sized on the old conclusion.**

## 3. Business / product idea: a standalone Behavioral Signal & Stress-Risk analytics service

**The gap this targets.** Off-the-shelf factor data (momentum, value,
quality) is sold by large vendors (MSCI, AQR's own public factor data,
Bloomberg) as pre-blended, black-box composites, priced for institutions
with seven-figure budgets. Smaller systematic funds, family offices, RIAs,
and independent research desks either can't afford that tier or can't see
*inside* the composite to know which component is actually carrying the
edge on their specific universe — exactly the failure mode this project hit
firsthand on the NSE data (section 1, above), and hit *again* when its own
first-reported positive finding (reversal) turned out not to survive a
beta check the project hadn't yet thought to run (Milestone 8). The product
is built directly around fixing that: **decomposed, auditable behavioral
signals plus honest, per-universe, beta-adjusted validation, not another
black-box score** — the same standard that, when finally applied evenly,
is what surfaced this project's one genuine finding (US momentum) instead
of its retracted one (reversal).

**What it is.** A subscription analytics service with two parts:

- **Signal side**: the momentum / 52-week-high / reversal library in
  `signals/`, run per-client against *their* universe (not a generic global
  one), reported as separate, individually-backtested components — never
  pre-blended — with the decile backtest and cost-adjusted Sharpe shown for
  each, on their actual investable names, not a vendor's benchmark universe.
  Every reported number ships with its own beta-regression alpha/beta
  breakdown (Milestone 6) so a client can see whether a signal's performance
  is genuine stock-selection skill or just uncontrolled market exposure — a
  check most factor-data vendors don't surface at all.
- **Risk side**: the regime-switching stress-VaR methodology from
  `risk_simulation/fat_tails_vs_normal.py`, run against a client's actual
  position correlations and leverage, reporting calm-regime vs. stress-regime
  tail loss side by side — the comparison a standard historical-VaR vendor
  tool doesn't show.

**Minimum viable version**: a report generator that takes a client's
portfolio or watchlist and CSV price history, and outputs, per name: each
individual behavioral signal's current value and its own historical
Sharpe/drawdown on that universe (not a pre-blended score), plus a portfolio-
level calm-vs-stress VaR comparison. Buildable directly on the code already
in this repo folder.

**Target customer**: small-to-mid systematic equity funds, family offices,
and independent RIAs — priced out of institutional factor-data tiers but
sophisticated enough to want decomposed, re-validated signals rather than a
black box. A secondary market: finance graduate programs and CFA/PE prep
courses, as a teaching tool for exactly the "don't trust the blend" lesson
this project surfaced.

**Revenue model**: per-seat analytics subscription, tiered by number of
tracked universes/portfolios — the same go-to-market as quant factor-data
vendors, but priced and scoped for the segment those vendors don't serve
well, and differentiated specifically on transparency (every number traces
to runnable code and a stated backtest window, not a vendor's proprietary
methodology).

**Moat, such as it is**: not the signals themselves (all public, published
research) — the moat is the discipline of per-client, per-universe
decomposed validation instead of a generic pre-blended score, which is
exactly what a larger vendor selling a standardized product across all
clients structurally can't do cheaply.

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
  market, unreplicated on NSE.
- **The publication-decay check (Milestone 9) found exactly the textbook pattern: real
  decay, not disappearance.** Split at 1994 (~1yr after Jegadeesh & Titman's 1993
  publication), the long leg's alpha shrinks ~33% (daily) to ~38% (monthly) post-1994 but
  stays significant in both; the combined book's alpha shrinks 30-47% and loses
  significance at daily frequency (p=0.116) while remaining significant monthly (p=0.035).
  The magnitude matches McLean & Pontiff's (2016) documented average post-publication decay
  across anomalies generally — this is the expected pattern playing out exactly as the
  literature predicts, not a surprise finding. **Rule: "promising, not confirmed" was the
  right interim label — the confirmed version is narrower (long leg, primarily) and smaller
  than the full-sample number, which is what a decay check is supposed to do: replace an
  unqualified headline number with the honestly-sized one that survives scrutiny.** Report
  the post-decay number when sizing anything against this finding, not the full-sample one.
- **Milestone 10 tested Milestone 9's own decayed number the same way Milestone 7 tested
  Milestone 6's — with an actual rolling, out-of-sample hedge, not an in-sample regression
  coefficient — and found it does not survive.** Milestone 9 fit one beta per sub-sample
  using that sub-sample's own data; Milestone 10 instead re-estimated beta every rebalance
  from only the preceding year of trailing data (exactly the methodology Milestone 7
  already established as this project's required standard) and applied the identical
  1994 split to the resulting hedged return series. Pre-1994, the hedge strongly confirms
  alpha in both legs (p≤0.025). Post-1994, alpha is not statistically distinguishable from
  zero in either leg at either frequency (p=0.15-0.59), and the hedged combined book's
  average post-1994 return is outright negative. **Rule: an in-sample per-era regression
  and a genuinely out-of-sample rolling hedge can disagree even when both are run
  correctly, and the out-of-sample version is the one that matters — it's the only one a
  real fund could actually have traded. Never let an earlier milestone's more convenient
  methodology stand once a stricter one, already used elsewhere in the same project, is
  available to re-check it.** This project's headline finding is therefore real and robust
  pre-1994, and not currently demonstrated to be forward-sizeable in the post-publication
  era — a materially more conservative conclusion than Milestone 9's, reached by applying
  the project's own best existing method to its own best surviving result.
- **Milestone 11 investigated Milestone 10's null result in depth, at explicit user
  request, rather than stopping at "not significant."** Two obvious objections were
  tested directly: that the post-1994 null result is really just the well-documented 2009
  momentum crash (Daniel & Moskowitz, 2016) distorting the average, and that it's an
  artifact of the specific 252-day rolling hedge window chosen. Neither held up. A
  five-era breakdown showed the long leg's hedged excess return declining steadily from
  +6.5%/yr (1994-99) to +0.1%/yr (2010-2017) — a trend across the whole post-publication
  period, not a single bad episode. Excluding the March-August 2009 crash window (which
  did cost the combined book 40% cumulatively on its own) moved the long leg's p-value
  from 0.149 to a still-marginal 0.095 and barely moved the combined book's (0.590 to
  0.334) — real, but nowhere near sufficient to explain the result on its own. Re-running
  the hedge at 126-, 252-, and 378-day windows gave the identical pattern every time.
  **Rule: when a null result survives the two most obvious "maybe it's just noise/an
  artifact" objections, that's stronger evidence for the result, not a reason to keep
  looking for an out.** This project's most rigorous read of its own headline finding is
  now: genuine, strong pre-1994 alpha, and genuine, ongoing decay since — not a temporary
  shock the strategy is due to recover from.
- **Milestone 12 asked whether that whole pattern is a momentum-specific quirk or a
  market-wide phenomenon, by applying the identical toolkit to the other two US
  signals — and found genuinely different answers for each.** 52-week-high shows no
  significant alpha in either era, in any leg: it never had genuine stock-selection skill,
  consistent with Milestones 6-7's beta-only explanation. Short-term reversal's long leg,
  by contrast, shows the exact same signature as momentum's: real, significant pre-1994
  alpha (+5.31%/yr, p=0.046) that decays completely to noise post-1994 (+0.25%/yr,
  p=0.629) — a pattern invisible in Milestone 8's full-sample regression, which correctly
  found no full-sample significance but could not distinguish "never real" from "real,
  then decayed." **Rule: a full-sample null result answers "is there significant alpha on
  average," not "was there ever genuine alpha" — those are different questions, and this
  project's own reversal signal shows they can have different answers.** The "real
  pre-1994, decayed since" pattern is therefore not a momentum idiosyncrasy: it appears in
  two of three signals' long legs, consistent with a market-wide explanation (the same
  1990s-2000s scaling-up of quantitative, cross-sectional strategies this project's own
  case studies on LTCM and the 2007 Quant Quake already document as reshaping US equity
  markets over exactly this period) rather than a fluke specific to one anomaly. *[Since
  retracted for reversal — Milestone 15 traced this "genuine pre-1994 alpha" to a thin,
  survivorship-biased 1972-1977 sample window; see below.]*
- **Milestone 13 quantified the decay directly instead of relying on a fixed 1994 cutoff,
  and found the two surviving long legs decay in genuinely different shapes.** A
  continuous linear-trend regression on momentum's long leg gives a slope that is not
  statistically significant (p=0.15) — the effect did not decay smoothly. A rolling
  5-year trajectory explains why: momentum's hedged alpha stayed consistently strong
  (+4% to +22%/yr) from the 1970s through the window ending January 2008, then broke
  sharply negative from 2009 on. Splitting explicitly at September 2008 gives a far
  cleaner divide (pre: +8.02%/yr, p=0.0005; post: -0.56%/yr, p=0.998) than the 1994 split
  ever produced. Reversal's long leg, in contrast, shows a real, statistically significant
  linear decay (slope -0.41%/yr, p=0.026) with an implied zero-crossing around November
  2004. **Rule: a binary split at a theoretically-motivated date (here, a publication
  year) can be directionally correct while still misdescribing the actual shape and
  timing of an effect — quantify the trend continuously, and sanity-check it against a
  non-parametric rolling trajectory, before writing up "gradual decay" as the mechanism.**
  Momentum's weakness is better attributed to a 2008-09 regime shift (plausibly the same
  2009 momentum crash examined directly in Milestone 11) than to slow, 1990s
  publication-driven crowding. *[Since retracted for reversal — Milestone 15 found this
  "smooth trend" was itself an artifact of unreliable early data; momentum's finding here
  is unaffected.]*
- **Milestone 14 formalized the "broke around 2008-09" claim with a proper structural-break
  test, and the result is more conservative than Milestone 13's descriptive comparison.** A
  Chow-style test at a single, literature-motivated date (2008-09-01, from Daniel &
  Moskowitz 2016) confirms a real level shift in momentum (p=0.026 daily) — but an
  unconstrained Quandt-Andrews sup-Wald search (which does not assume any break date) finds
  its single best-fitting break 27 months later, at December 2010, and that unconstrained
  maximum is not statistically significant once corrected for the multiple-testing problem
  of searching ~375 candidate dates (400-draw block-bootstrap p=0.138). Reversal shows the
  opposite: no break near 2008 (p=0.34), but a genuine, significant break (bootstrap
  p=0.048) around August 1980 — the sharp early decline from its extraordinarily high
  late-1970s level, not a smoothly accumulating multi-decade slope as the linear-trend
  regression alone suggested. **Rule: a descriptive "this cutoff fits better" comparison
  and a formal, multiple-testing-corrected structural-break test can disagree even when
  both are computed correctly on the same data — trust the formal test, and expect it to
  be more conservative, not less, than the comparison that motivated running it.** *[Since
  retracted for reversal — Milestone 15 found this August 1980 "break" is a thin-universe
  and data-quality artifact, not a real 1980 market event; momentum's finding here is
  unaffected.]*
- **Milestone 15 investigated the mechanism behind that August 1980 break, at explicit
  request — and the answer reverses, not just refines, everything Milestones 9, 12, 13,
  and 14 had concluded about reversal.** The reversal signal's decile long leg is only 2-4
  stocks from 1972 through 1983, drawn from a total universe of 9-14 names — today's
  mega-cap survivors (AAPL, JPM, JNJ, PG, XOM, and so on) backfilled to their earliest
  available data, a textbook survivorship-biased sample where every name, by construction,
  went on to become a winner. Two genuine, previously undocumented data anomalies compound
  this (`WMT` round-trips -52%/+109% across two weeks in December 1974; `INTC` jumps +101%
  and +51% in 1972, both consistent with split-adjustment errors in the raw feed).
  Re-testing reversal's long-leg significance from a range of start dates shows its entire
  positive-alpha claim (already only marginal at full sample, p=0.068) depends completely
  on the unreliable 1972-1977 window: from any later start, including the exact date
  Milestone 14's own search identified (1980-08-29), alpha is never significant (p=0.54 to
  0.96, usually slightly negative). **Momentum, run through the identical thin, biased,
  partly-glitched early data as a control, was unaffected — significant (p≤0.02) at every
  comparable start date.** **Rule: when a signal's finding depends on data density you
  haven't checked, check it before trusting the finding — a decile portfolio with 2-4
  names is not a diversified strategy, it is a handful of individual stock bets, and
  &quot;statistically significant&quot; on such a sample tells you about those specific
  stocks' survivorship, not about a market-wide behavioral effect.** Short-term reversal's
  apparent pre-2005 alpha is retracted outright, not narrowed: this project has found no
  reliably demonstrated reversal edge anywhere in this dataset, in any leg, at any point in
  the sample.
- **Milestone 16 gave momentum's 2008-09 break a genuine causal mechanism, not just a
  confirmed date.** This project's own look-ahead-free Bear × High-Volatility
  momentum-crash regression (built in Milestones 5-6, where it was tested on the
  52-week-high signal, full-sample, and rejected) was applied to momentum's hedged long
  leg, split at the same literature-motivated 2008-09-01 date used since Milestone 14. The
  interaction term is small and statistically insignificant pre-2008 (p=0.42) but large,
  negative, and significant post-2008 (coef=-0.00218/day, p=0.008): on the roughly 9% of
  post-2008 trading days that are both high-volatility and trailing-bear, the long leg
  loses at an annualized rate around 37%, while baseline (non-crash) alpha has fallen to
  statistically indistinguishable from zero. **Rule: a structural break confirmed by a
  date is still an unexplained fact until tested against a specific, named mechanism —
  and a mechanism this project rejected for one signal, in one era, can still be real for
  a different signal, in a different era; don't let an earlier rejection close off
  re-testing the same hypothesis somewhere new.** The classic momentum-crash dynamic
  appears to have been dormant through the pre-crisis decades and active since,
  consistent with a market where momentum-following capital had scaled up enough by 2008
  for the mechanism to actually bite.
- **Milestone 17 tested the same crash mechanism on NSE — and, in the process, exposed a
  methodological gap in this project's own earlier NSE momentum test.** Milestone 8's
  "no significant NSE momentum alpha" used a static full-sample regression, never the
  rolling out-of-sample hedge this project has used for every US momentum test since
  Milestone 7. Applying that hedge to NSE momentum for the first time reaffirms no
  significant full-sample alpha (daily p=0.170, monthly p=0.168) but surfaces a new,
  tentative post-2008 signal (daily p=0.044, monthly p=0.073) the cruder test could not
  have found — with the caveat that NSE's universe grew from ~30 to 48 names over the same
  window, so part of the improvement may be a less-thin cross-section rather than a real
  regime change. Separately, the Bear × High-Vol interaction that explained momentum's US
  break is never significant on NSE (p=0.96 full-sample); NSE instead shows a plain,
  unconditional Bear effect (p=0.002) — a related but mechanistically different pattern.
  **Rule: applying your own best methodology to an already-tested market, not just a new
  one, can still turn up something a cruder earlier pass missed — "already checked" and
  "checked with your current best method" are not the same claim, and a rejected
  full-sample result doesn't mean every sub-period was checked with equal power.**

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
10. **Size a position on the decayed number, not the full-sample number — and check that
    decayed number was itself estimated out-of-sample.** Milestone 9 split this project's
    one surviving edge (US momentum) at its 1993 publication date and found real decay:
    alpha down ~30-47% post-1994, with one cut losing significance entirely. That was
    already a large correction to the full-sample number — but it was still an in-sample
    estimate. Milestone 10 re-tested the same post-1994 period with an actual rolling,
    out-of-sample hedge (the standard Milestone 7 already required for this project's own
    negative findings) and found the post-1994 alpha does not survive at all, in either
    leg. **Rule: for any published anomaly, run the pre/post-publication split before
    sizing anything against it — and don't stop at an in-sample per-era regression;
    re-confirm with a hedge that could actually have been traded forward, because the two
    can and do disagree.** The pre-publication half of the sample describes a market that
    no longer exists; as of this project's most rigorous test, the post-publication market
    has not been shown to pay this edge at all.
11. **Before accepting a null result, rule out the obvious "maybe it's just one bad episode"
    and "maybe it's a methodology artifact" objections — and if it survives both, treat
    that as the null result getting stronger, not weaker.** Milestone 11 tested whether
    Milestone 10's post-1994 null result was really just the 2009 momentum crash, and
    whether it depended on the specific hedge window chosen. Neither objection explained
    it: the era-by-era trend showed ongoing decay through 2017, well after 2009, and the
    result was identical across three different hedge windows. **Rule: a finding that
    survives a genuine attempt to explain it away deserves more confidence, not less —
    the temptation after an unwelcome result is to look for the one adjustment that makes
    it go away; running that check honestly, and reporting it even when it doesn't help,
    is what separates a stress-test from a fishing expedition.**
12. **A full-sample "no significant alpha" verdict does not mean a signal was never real —
    check whether it's actually two eras averaging to zero before writing it off entirely.**
    Milestone 8 declared short-term reversal fully retracted based on a full-sample
    regression, which was the technically correct read of that specific test. Milestone 12
    applied the era-split toolkit built for momentum and found reversal's long leg had been
    genuinely, significantly positive pre-1994 and decayed to noise since — the same
    pattern as momentum, hidden inside a full-sample average that happened to net out near
    zero. **Rule: retest every full-sample null result from before your era-split toolkit
    existed with that toolkit, not just your full-sample findings — a "no effect on
    average" verdict can quietly contain a real, decayed effect that a single-number
    summary cannot distinguish from a signal that was simply never real.**
13. **A binary before/after split can get the direction right while getting the mechanism
    wrong — quantify the trend continuously before naming a cause.** Milestone 13 fit a
    continuous linear decay rate to momentum's and reversal's hedged long legs instead of
    trusting the 1994 publication-date cutoff. Reversal's decay turned out to be genuinely
    smooth and statistically significant, consistent with the publication-decay story.
    Momentum's did not: its linear trend was not significant, because the real pattern is a
    sharp break around the 2008-09 financial crisis, not a gradual erosion starting in
    1994. **Rule: once a binary split finds a real effect, don't stop there — fit a
    continuous trend and inspect a rolling, non-parametric trajectory to check whether the
    story you're about to tell (e.g., "publication-driven crowding") actually matches the
    shape of the data, or just happens to fall on the correct side of an arbitrary cutoff.**
    *[Reversal's "genuinely smooth" decay cited here was itself later retracted by
    Milestone 15 — it turned out to be an artifact of thin, unreliable early data, not a
    real trend at all. The lesson (quantify continuously, don't stop at a binary split)
    still holds; the specific reversal example does not.]*
14. **Even a data-driven, non-arbitrary date can still be the wrong test — correct for the
    search itself before trusting it.** Milestone 13 picked September 2008 by eyeballing a
    rolling trajectory, which is a comparison, not a test: it doesn't say whether that split
    is meaningfully better than what chance alone would produce from searching many candidate
    dates. Milestone 14 ran the actual test two ways: a single pre-registered date (motivated
    by an external, published crash episode, not this project's own plot) confirmed momentum's
    break; an unconstrained search over ~375 candidate dates, corrected via bootstrap for
    having searched that many, did not decisively confirm any single dominant break (its own
    best-fit date, December 2010, wasn't even the one the earlier milestone had proposed).
    **Rule: a hypothesis motivated by an external, independent source (a published crash date,
    a known regulatory change) can be tested directly and cheaply; a hypothesis motivated by
    your own data (the best-looking split you found by eye) requires a multiple-testing-
    corrected test before it earns the same confidence — and expect the corrected version to
    be measurably more conservative.**
15. **When a signal's finding depends on data density you haven't checked, check it before
    trusting the finding.** Milestone 15 traced reversal's August 1980 "break" to its
    source: a decile portfolio of only 2-4 stocks, drawn from a 9-14-name universe of
    today's mega-cap survivors backfilled to the 1970s, plus two previously undocumented
    data anomalies. Reversal's entire positive-alpha claim depended on this unreliable
    window and vanished completely once excluded, at every later start date tested.
    Momentum, run through the identical thin data as a control, was unaffected. **Rule: a
    decile portfolio with 2-4 names is not a diversified strategy, it is a handful of
    individual stock bets, and "statistically significant" on such a sample tells you
    about those specific stocks' survivorship, not about a market-wide behavioral effect —
    check minimum portfolio size and data density for every sub-period a significance
    claim rests on, not just the full sample's average.**
16. **A structural break confirmed by a date is still an unexplained fact until tested
    against a named mechanism.** Milestone 16 applied this project's own Bear ×
    High-Volatility momentum-crash regression (Milestones 5-6, rejected for the
    52-week-high signal, full-sample) to momentum's hedged long leg, split at the same
    2008-09-01 date. The interaction term is insignificant pre-2008 (p=0.42) but large,
    negative, and significant post-2008 (p=0.008) — the classic momentum-crash mechanism
    was dormant through the pre-crisis decades and activated since. **Rule: a mechanism
    this project rejected for one signal, in one era, can still be real for a different
    signal in a different era — don't let an earlier rejection close off re-testing the
    same hypothesis somewhere new; a confirmed break date is a fact, not yet an
    explanation.**
17. **"Already checked" and "checked with your current best method" are not the same
    claim.** Milestone 8's NSE momentum test used a static full-sample regression.
    Applying the rolling out-of-sample hedge this project built in Milestone 7 to NSE
    momentum for the first time reaffirmed no significant full-sample alpha, but surfaced
    a tentative post-2008 signal (daily p=0.044, monthly p=0.073) the cruder test lacked
    the power to see — while the Bear × High-Volatility crash mechanism confirmed for US
    momentum (Milestone 16) turned out not to replicate on NSE at all. **Rule: a rejected
    finding on an already-tested market is worth re-checking with each new methodology
    upgrade this project builds, not just applying new methods to new markets — the
    earlier rejection may have been correct for the test it used and still be missing
    something a better test would find; and a confirmed mechanism on one market is a
    hypothesis, not a law, everywhere else.**

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
  is genuine stock-selection skill or just uncontrolled market exposure, and
  a pre/post-publication decay split re-confirmed with an actual rolling,
  out-of-sample hedge (Milestones 9-10) for any signal drawn from published
  academic research, and a minimum-data-density check flagging any period
  where a decile portfolio would hold fewer than, say, 10 names (Milestone
  15, which found a "genuine" edge that was actually 2-4 survivor-biased
  stocks masquerading as a diversified portfolio) — checks most
  factor-data vendors don't surface at all, and which this project's own
  experience shows can materially change the answer versus an in-sample
  split alone.
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

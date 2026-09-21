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
  In a DealLens-style workflow, the natural use is a **tilt or flag layered on
  top of the existing 8-factor screening score**
  (`docs/phase0-vertical-slice-design.md`), not a replacement for it: a stock
  that screens well fundamentally *and* sits in the top behavioral decile is a
  stronger candidate than either signal alone; a stock flagged as a behavioral
  "loser" (bottom decile, near-anchored, recently overreacted-to) is worth a
  second look before initiating or sizing a position, even if fundamentals
  look fine.
- **Decile, not point-estimate.** Treat the score as a rank, not a precise
  number — the whole point of `backtest/engine.py`'s decile-sort methodology
  is that the edge shows up in the spread between the extreme deciles, not in
  any single stock's score being "correct."
- **Re-validate before trusting it.** Per `README.md`'s stated limitation,
  the backtest has only been run on synthetic data in this environment. The
  very first step of using this framework for real capital is running it on
  a real, survivorship-bias-free universe and checking the long-short Sharpe
  and cost-adjusted return hold up out-of-sample — exactly the discipline
  the case studies show quant shops living and dying by.

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

## 3. Business / product idea: a Behavioral Risk & Signal Overlay module

**The pitch.** A module — usable standalone or, concretely, as a plausible
future phase of this repo's own `packages/finance_engine` /
`apps/api` architecture — that layers behavioral-finance signals onto an
existing fundamentals-driven deal/portfolio screening pipeline, in two parts:

- **Alpha side**: the composite Behavioral Mispricing Score from part 1,
  exposed as an additional factor in the screening score, comps selection,
  or LBO entry-timing decision (e.g., flag targets trading near a 52-week
  low with strong recent-quarter fundamentals as *possible* anchoring-driven
  mispricing worth a closer look, not an automatic buy).
- **Risk side**: a stress-VaR overlay based on the regime-switching
  methodology in `risk_simulation/fat_tails_vs_normal.py`, run against a
  portfolio's or LBO's actual leverage and position correlations, reporting
  both the calm-regime and stress-regime tail loss side by side — the single
  number a rational-markets-only risk model would never show.

**Why this fits as a DealLens extension specifically**: the existing
`apps/api/app/ai` design principle in this repo — "architecturally incapable
of inventing a number, every claim must cite a snapshot of already-computed
outputs" — maps directly onto this module's honesty requirement: a behavioral
score or stress-VaR number is only useful if it's computed from real,
inspectable inputs (the same signals/backtest code in this folder), never
asserted by an LLM. That's a deliberate design constraint carried over from
this repo's Phase 4 AI layer, not a coincidence.

**Minimum viable version**: a report generator that takes a portfolio (or a
DealLens screening shortlist) and outputs, per name: fundamental screening
score (existing), Behavioral Mispricing Score (new), and — for
leveraged/derivative positions — calm-regime vs. stress-regime VaR (new).
That is buildable directly on top of the code already in this folder, once
run against real market data outside this sandbox.

**Revenue framing, if pursued as a standalone product**: sell to
mid-size long/short equity funds and PE shops as a due-diligence and
risk-overlay add-on — priced as a per-seat analytics subscription, the same
go-to-market as the behavioral/quant factor licensing products AQR and
similar quant shops already sell institutionally, but positioned narrower
(a specific, auditable signal + risk overlay) rather than a full asset
management offering.

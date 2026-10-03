# Behavioral Signal & Stress-Risk Analytics toolkit

A signal-agnostic extraction of this project's own 53-milestone statistical
core. `FRAMEWORK.md` (Section 3) has described a "Behavioral Signal &
Stress-Risk Analytics" product since the project's first milestone; this is
that product's actual analysis engine, not just the pitch for one. Point it
at any out-of-sample-hedged daily return series and the price panel used to
build look-ahead-free crash-regime dummies, and it runs the same three
checks this project built and repeatedly refined on its own signals
(momentum, turn-of-month, and in passing low-volatility/MAX), rather than
anything invented for this write-up.

## Why this exists

Milestones 46 and 53 both asked the same question of two completely
different signals — "does this carry the same crash-regime or tail risk
momentum does?" — and had to duplicate significant setup each time because
the project's crash-risk machinery lived inside signal-specific
investigation scripts, not a reusable library. This toolkit is that
duplication removed: `toolkit/demo_52w_high_asx.py` runs the full pipeline
against ASX 52-week-high — a signal that has been in this project since
Milestone 23 but had never once been run through the crash-interaction or
VaR/CVaR tests — as a worked proof that the extraction actually
generalizes, not just a refactor that happens to still pass on the three
signals it was built from.

## What it checks, and why each check exists

1. **`crash_regime_interaction`** — does the signal's return carry a
   Bear+HighVol regime-interaction effect, the mechanism Milestones 16-18
   identified for momentum's 2008-09 break (Daniel & Moskowitz 2016)? Built
   from `build_regime_dummies` + `hac_regression`, unchanged since those
   milestones. A clean null here is not evidence of safety — see point 2.

2. **`tail_risk_profile`** — does the signal's empirical return distribution
   understate tail risk relative to a Gaussian fit, the way Q1's simulation
   warned (Milestone 43)? Includes a bootstrap CI on the CVaR **ratio**
   itself (not just each side separately) from the start — the refinement
   Milestone 51 found was missing from the project's own first VaR/CVaR
   pass, built in here rather than left for a second revision. Milestone 53
   found turn-of-month fails check 1 cleanly (no short leg, no crash-regime
   sensitivity) but still carries real exposure on check 2 — the two checks
   answer genuinely different questions and neither is a substitute for the
   other.

3. **`propagated_crash_stress`** — if (and only if) check 1 comes back
   significant, what does a stress scenario look like once the fitted
   coefficient's own HAC estimation uncertainty is propagated through the
   simulation, not just residual noise bootstrapped around a fixed point
   estimate (Milestone 50's own correction to Milestone 33's original
   stress test)? The toolkit raises this exactly where Milestone 50 put it
   — downstream of a significant interaction only, never run speculatively
   on a null result, since Milestone 46 and 53 both showed a stress
   projection built on a non-significant coefficient would manufacture
   false precision.

`full_report` runs all three in the right order and sequencing (tail risk
always; stress only when warranted) and returns a `SignalRiskReport` with a
`.summary()` string, or inspect the structured dataclass fields directly for
your own reporting.

## Usage

```python
import sys
sys.path.insert(0, "path/to/research/behavioral-finance")  # repo root

from toolkit import full_report

# hedged_returns: your own out-of-sample-hedged daily return series
#   (pd.Series indexed by trading date) -- how you build it (which hedge
#   methodology, which backtest engine) is your own choice; this toolkit
#   analyzes risk, it does not construct signals or hedges.
# prices: the price panel (pd.DataFrame, tickers as columns) used to build
#   look-ahead-free Bear+HighVol regime dummies -- the same universe your
#   signal trades, or any representative market proxy.
report = full_report("my signal", hedged_returns, prices)
print(report.summary())

# or use the three checks independently:
from toolkit import crash_regime_interaction, tail_risk_profile, propagated_crash_stress

crash = crash_regime_interaction("my signal", hedged_returns, prices)
tail = tail_risk_profile("my signal", hedged_returns)
if crash.significant:
    stress = propagated_crash_stress("my signal", crash, prices)
```

See `toolkit/demo_52w_high_asx.py` for a complete worked example, including
how to build `hedged_returns` from this project's own backtest engine.

## What this toolkit deliberately does not do

- **It does not build signals.** Signal construction (which factor, which
  universe, which rebalance frequency) is scope this project's own
  `signals/` package and `backtest/engine.py` cover, and is a decision for
  whoever is using the toolkit, not something it should opinionate on.
- **It does not size positions or set circuit breakers.** That is
  `PLAYBOOK.md`'s job, built on top of this toolkit's output for this
  project's own specific combined book — a worked example of translating a
  report like the one this toolkit produces into actual allocation
  decisions, not a feature of the toolkit itself.
- **It does not claim capacity, liquidity, or execution feasibility.** Every
  number this toolkit reports is a return-series statistic; nothing here
  estimates how much capital a signal could actually absorb (an explicit,
  still-open gap in this project, same as it is for the three signals
  tested directly).
- **It does not correct for multiple testing across however many signals you
  run through it.** If you run this toolkit against many candidate signals
  and only report the ones that come back significant, Milestones 41 and
  47 are the standing warning: you need your own multiple-testing
  correction across that family, exactly as this project built two
  separate ones for its own two families of tests.

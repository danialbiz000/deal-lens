# Behavioral Finance Research Project

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
  max drawdown, turnover, transaction-cost drag), designed to run against real daily price
  history.

## Important limitation of this environment — read before trusting any Q2 numbers

This code was written and committed from a sandboxed session with **no general internet
access** (outbound HTTPS is restricted to package registries and the Anthropic API; Yahoo
Finance, Stooq, SEC EDGAR, and FRED were all unreachable — verified directly, see commit
history / session log). That means:

- The **Q1 risk simulation is a real, executed result** in this repo — it's a Monte Carlo
  study with no external data dependency, so its numbers are genuine, not illustrative.
  As executed (500,000 simulated days, seed=7; see `risk_simulation/fat_tails_vs_normal.py`
  for exact parameters):

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
- The **Q2 backtest code is real and complete**, but has only been exercised here against a
  small synthetic fixture (`tests/`) that checks the mechanics (decile sorting, long-short
  construction, turnover/cost accounting) are correct — it has **not** been run on real
  market history, because this session couldn't reach any price data provider. **Do not
  treat any Q2 numbers in this repo as real backtest results** until you've run
  `python -m data.loaders` (or the notebook-equivalent) yourself, somewhere with normal
  internet access, using the entry point in "How to run" below.

This distinction matters a lot for a project whose entire thesis is "don't trust a model's
output just because it looks rigorous" — so the same discipline applies here.

## Methodology

### Case studies (qualitative, `case_studies/`)

Three episodes, chosen because they are well-documented and pull in different directions:

| Case | Failure mode | Behavioral mechanism |
|---|---|---|
| LTCM (1998) | "Rational" convergence-arbitrage model assumed historical correlations/vol would hold; 25:1+ leverage turned a plausible loss into a solvency event | Flight-to-quality herding by *counterparties*, not LTCM itself, broke the model's correlation assumptions |
| Quant Quake (Aug 2007) | Multiple market-neutral quant funds, each individually "rational," had converged on correlated factor bets; one fund's forced unwind cascaded into a correlated, self-reinforcing selloff across the group | Herding among sophisticated arbitrageurs (crowding), not retail panic |
| Amaranth Advisors (2006) | A single trader's concentrated, highly leveraged natural-gas spread position | Overconfidence / illusion of control |
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

## Data sources (for Q2, to be run outside this sandbox)

- `yfinance` (Yahoo Finance) — daily OHLCV, primary source, free, no key required.
- Stooq CSV endpoint — fallback if Yahoo is rate-limited or blocked.
- Universe: configurable; the loader defaults to a hard-coded liquid large-cap list to
  avoid needing a paid constituents-history provider (a real study should instead use a
  point-in-time index membership list to avoid survivorship bias — see "Limitations").

## How to run

```bash
cd research/behavioral-finance
pip install -r requirements.txt

# Q1 — runs now, no internet needed, no dependency on the rest of the repo
python risk_simulation/fat_tails_vs_normal.py

# Q2 — needs internet access to a market data provider
python -c "
from data.loaders import load_price_history
from signals.momentum import momentum_12_1, high_52w_proximity
from signals.reversal import short_term_reversal
from signals.composite import composite_score
from backtest.engine import run_decile_backtest

prices = load_price_history(period='10y')  # downloads + caches to data/cache/
scores = composite_score(prices)
result = run_decile_backtest(prices, scores)
print(result.summary())
"

# Tests (synthetic fixtures — no internet needed)
pytest tests/ -v
```

## Concrete, applicable outputs

This research is designed to feed three deliverables (full detail in `../FRAMEWORK.md`):

1. **An investment framework** — a composite behavioral mispricing score usable as a
   screening/tilt signal alongside fundamental analysis.
2. **Risk-management lessons** — a stress-testing playbook (derived from the Q1 simulation)
   for any leveraged or "market-neutral" strategy: never calibrate tail risk on a calm-regime
   correlation matrix alone.
3. **A business/product idea** — a concrete pitch for a "Behavioral Risk & Signal Overlay"
   module, including how it could plug into an existing deal-screening or portfolio
   platform (this repo already has one: `packages/finance_engine`).

## Explicit limitations (state these in any paper or pitch built on this)

- **Survivorship bias**: the default loader uses a fixed current-day ticker list, not
  point-in-time index membership. A rigorous version needs a survivorship-bias-free
  universe (e.g., CRSP, or a maintained point-in-time constituents file).
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

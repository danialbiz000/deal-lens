# DealLens -- Phase 0 + Phase 2 + Phase 4

Company &rarr; Financials &rarr; Screening Score &rarr; Comps &rarr; LBO &rarr; Memo/IC Simulation, end-to-end, for public companies.

Three vertical slices of DealLens so far:
- **Phase 0** (`docs/phase0-vertical-slice-design.md`): Company, FinancialPeriod, Assumption, and the 8-factor screening score.
- **Phase 2** (`docs/phase2-comps-lbo-design.md`): comparable-companies peer selection + entry valuation, base/bull/bear scenarios, and a full 5-year LBO underwriting engine with a value-creation bridge that reconciles exactly to MOIC.
- **Phase 4** (`docs/phase4-ai-layer-design.md`): the AI layer -- a memo writer and a 5-role IC simulator, both built on real Claude API calls, both architecturally incapable of inventing a number (every claim must cite a snapshot of already-computed Phase 0/2 outputs), with a deterministic, code-level gate that can force the IC recommendation regardless of what the model says.

See `DealLens_PE_Deal_Screening_Project_Spec.pdf` for the original product
spec. Still explicitly **not** included: `Transaction`/precedent
transactions, a document parser or news synthesizer, formatted memo export,
multi-tranche debt sculpting, the full 6-variable tornado (only entry x
exit multiple here), auth, cloud deployment -- see each design doc's own
"explicitly deferred" section. The point of every slice is proving the
deterministic-engine-vs-everything-else split works end-to-end, with real
data from SEC EDGAR (Phases 0/2) and real model calls confined to one
isolated module (Phase 4).

## What's here

```
apps/web/              Next.js dashboard (company list, screening, valuation/comps, LBO,
                        memo, and IC-simulation pages)
apps/api/               FastAPI backend (companies, financials, assumptions, screening,
                         peers/valuation, scenarios, LBO, memo, ic-simulation)
apps/api/app/ai/         Phase 4 only: bundle assembly, citation validation, Claude API
                         orchestration -- the only place `anthropic` is imported anywhere
packages/finance_engine/ Pure-Python scoring + comps + LBO + ic_gate math -- zero
                         FastAPI/DB/HTTP/AI deps (grep-able: zero references to
                         anthropic/claude anywhere in this package, ever)
db/schema.sql            Canonical Postgres-portable DDL reference
db/seed/                 One-command real-company seed script
docs/                    Design docs (Phase 0 + Phase 2 + Phase 4) + original spec
```

## Fresh-clone-to-working-demo

### 1. Install dependencies

```bash
# Backend + finance engine
cd apps/api
python -m venv .venv
.venv/Scripts/activate        # or `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt   # also installs packages/finance_engine in editable mode

# Frontend
cd ../../apps/web
npm install
```

### 2. Configure environment

```bash
cp .env.example apps/api/.env
# edit apps/api/.env: set EDGAR_USER_AGENT to identify yourself (SEC requires this),
# optionally set FMP_API_KEY (https://site.financialmodelingprep.com/developer/docs),
# and ONLY if you plan to generate a memo or run an IC simulation (Phase 4),
# set ANTHROPIC_API_KEY (https://console.anthropic.com/) -- every other
# endpoint in this project, including the default test suite, needs neither
# FMP_API_KEY nor ANTHROPIC_API_KEY.

cp .env.example apps/web/.env.local   # only the NEXT_PUBLIC_API_BASE_URL line matters here
```

### 3. Create the database

Nothing to run by hand -- `apps/api` creates its SQLite tables automatically
on startup (`app/db.py: init_db()`), using the ORM models in
`apps/api/app/models/` as the live source of truth. `db/schema.sql` is the
hand-maintained Postgres-portable reference for the same 3 tables, kept in
sync by hand (no migrations tool in this slice).

### 4. Seed one real company (optional but recommended)

```bash
cd apps/api && source .venv/Scripts/activate   # if not already active
python ../../db/seed/seed_demo_company.py            # defaults to AAPL / CIK 0000320193
# or: python ../../db/seed/seed_demo_company.py MSFT 0000789019
```

This pulls real SEC EDGAR data (and FMP data if `FMP_API_KEY` is set),
stores it, and prints the resulting screening score breakdown to the
console.

### 5. Start the API

```bash
cd apps/api
uvicorn app.main:app --reload
# -> http://localhost:8000, docs at /docs, health check at /health
```

### 6. Start the web app

```bash
cd apps/web
npm run dev
# -> http://localhost:3000
```

Open `http://localhost:3000`, click into the seeded company, click
**"Ingest financials"** if you haven't run the seed script, and you'll see
the screening score breakdown -- each factor's weight, normalized score,
whether it was `computed` or is a placeholder `default`, and the note
explaining how it was derived.

### 7. Phase 2: comps + LBO (needs 2+ peer companies)

Comps and the LBO both need at least one *other* ingested company to serve
as a peer candidate -- generate a couple more through the same flow above
(e.g. two more real tickers in the same sector as your target), then:

1. On the target's company page, click **"Valuation & comps"**, then
   **"Generate / refresh peers"**. Every candidate stays visible --
   `SELECTED`, `CANDIDATE`, or `REJECTED` with a reason code
   (`MISSING_FINANCIALS`, `REVENUE_SCALE_MISMATCH`, or `SELF`) -- nothing
   is silently dropped. You can override any peer's status manually (a
   reason is required).
2. The entry valuation (median/quartile EV/Revenue and EV/EBITDA multiples,
   implied entry EV and equity value) appears on the same page once >= 2
   peers are `SELECTED`.
3. Click **"LBO underwriting"**, then **"Generate scenarios"** (derives the
   BASE case's growth rate from the target's own historical revenue CAGR --
   reusing the exact same formula the screening score uses -- then applies
   the spec's BULL/BEAR deltas, including the spec-literal `-2.0x` BEAR
   exit-multiple delta).
4. Pick a case (BASE/BULL/BEAR) and click **"Run \_\_\_ case"**. You'll see
   Sources & Uses, MOIC/IRR, the value-creation bridge (which reconciles
   exactly to MOIC, to `1e-6`), the full year-by-year debt schedule, and an
   entry x exit multiple sensitivity grid underneath.

Every step above is a real HTTP call against real ingested SEC EDGAR data
-- nothing in this flow is mocked or pre-baked.

**Note on market cap:** comps need each company's market cap, which is only
populated by the FMP profile endpoint during `/ingest` (design doc section
1.1). Without an `FMP_API_KEY` configured, ingested companies will have
`market_cap: null` and every peer candidate will be rejected with
`MISSING_FINANCIALS` -- set `FMP_API_KEY` in `apps/api/.env` before trying
the comps/LBO walkthrough.

### 8. Phase 4: memo + IC simulation (needs `ANTHROPIC_API_KEY`)

Once BASE (and, for the IC simulation, BULL and BEAR too) LBO cases exist
for your target company from step 7:

1. On the target's company page, click **"Investment memo"**, then
   **"Generate new memo version"**. This makes one real, schema-forced call
   to the Claude API and returns exactly the 10 spec-named sections. Any
   citation ([[source: ...]]) pointing at a bundle path that doesn't exist
   is flagged in a warning banner; regenerating creates a new version
   without touching the old one.
2. Click **"IC simulation"**, then **"Run new IC simulation"**. This runs 5
   *sequential* Claude calls -- Analyst, Industry, Credit, Risk, IC Chair --
   each seeing every prior role's output, and displays the full transcript.
   If the model's own recommendation is `PROCEED_TO_DD` but the BEAR LBO
   case fails a hard threshold (IRR floor, MOIC floor, exit-leverage
   ceiling, or an interest-coverage breach in any year), the page shows an
   explicit override banner: the final recommendation is forced to `HOLD`
   in code, and the model's original answer stays visible, struck through,
   right next to it -- never silently substituted.

This, along with `POST .../documents/extract` (upload a financial statement
or investor-relations PDF for a private company and get back AI-proposed
candidate periods with citations -- see "Rate limiting" below), is the only
part of the whole project that talks to a third-party AI API, and the only
part that needs `ANTHROPIC_API_KEY` set. Without it, all three endpoints
return `503` with a clear message rather than a raw stack trace; every
other endpoint in the app is completely unaffected.

## Running the tests

```bash
# finance_engine (pure math, no I/O)
cd packages/finance_engine
pip install -e ".[dev]"
pytest

# apps/api (FastAPI + SQLAlchemy, isolated in-memory SQLite per test run)
cd apps/api
pip install -r requirements.txt
pytest
```

Both suites are green (73 + 113 tests, 2 of the apps/api tests skipping
gracefully without `ANTHROPIC_API_KEY`). `packages/finance_engine`'s
screening tests cover the normal case, missing-period case,
negative-EBITDA case, zero-revenue case, and zero-interest-expense case for
each of the 4 computable factors, plus a test asserting the 8 factor
weights sum to `1.0`. Its Phase 2 `lbo.py` tests additionally cover: exact
Sources=Uses reconciliation, exact debt-schedule roll-forward, debt fully
repaid before year 5 (no negative-debt bug), a bear case with a genuinely
negative-CFADS year (no sweep, no crash, a warning), the zero-interest
edge case, the value-creation bridge reconciling to MOIC within `1e-6`
across 4 distinct scenarios, the exit-multiple-dependent and
value-destructive flags, and sensitivity-grid monotonicity in both
directions (entry and exit multiple). Its Phase 4 `ic_gate.py` tests cover
a pass-all bear case and one failing each of the 4 named thresholds
individually, plus boundary cases (exactly at a floor/ceiling passes) and
year-0's null interest never being mistaken for a coverage breach.

`apps/api`'s Phase 4 tests never call the real Claude API by default: a
`FakeClaudeClient` fixture returns canned structured JSON, so
`packages/finance_engine` and `apps/api` together need zero API keys and
make zero network calls to pass. The one test that matters most in this
phase, `test_ic_simulation_override_fires_when_bear_case_fails_and_llm_says_proceed`,
mocks the IC Chair to say `PROCEED_TO_DD` while feeding a bear case that
fails the IRR floor, then asserts the persisted `recommendation` is
`HOLD`, `override_fired` is `true`, and `llm_recommendation` still shows
the original `PROCEED_TO_DD` untouched. Two optional live tests
(`test_memo_live.py`, `test_ic_simulation_live.py`) skip automatically
without `ANTHROPIC_API_KEY`. They were run for real once a key was
configured -- and both failed with a `503`, but for a reason that has
nothing to do with this codebase: `Your credit balance is too low to
access the Anthropic API`, straight from Anthropic's own API response.
The key authenticates fine and `ClaudeClient` forms the request correctly
(confirmed directly against the SDK, independent of pytest) -- the account
behind it simply has no credits, which is an account/billing action only
whoever holds that key can take, not something fixable in code. This
incidentally still exercised something real: `ClaudeApiError` correctly
wrapped Anthropic's 400 and the router correctly turned it into the
documented `503` with a clear message -- just not the "happy path" these
two tests exist to prove. They remain written and correctly gated; running
them again once the account has credits requires no code changes.

## The screening score, honestly

The score is `sum(weight_i * normalized_factor_i)` across 8 factors. Only
4 of them -- **growth, margins, cash conversion, leverage capacity**
(55% combined weight) -- are computed purely from ingested financials, with
exact formulas in `docs/phase0-vertical-slice-design.md` section 3.2.

The other 4 -- **business quality, market structure, exit optionality,
management/execution** (45% combined weight) -- cannot be derived from
financial statements alone. They default to a neutral score of 50 until an
analyst supplies an `Assumption` row via `POST /companies/{id}/assumptions`
(the web UI has a form for this on the company detail page). This is a
deliberate, spec-compliant MVP limitation, not an oversight: the "rule" for
a qualitative factor is "ask a human," and the "source" is
`Assumption.source`. Every screening-score response labels each factor's
`source` as `computed`, `default`, or `assumption` so this is never hidden.

## Comps + LBO, honestly

There is **no automated peer/market screener** in this slice (design doc
section 2.1): the peer candidate pool is whatever companies you've already
ingested into DealLens. Real market-wide peer discovery is a v1.0 data
connector problem, not a comps-formula problem, and is explicitly deferred.

The LBO makes several standard, disclosed MVP simplifications rather than
blocking on a fuller data model: capex stands in for a real depreciation
schedule as the interest tax-shield proxy; net working capital is a flat
percentage of *incremental* revenue rather than driven by granular AR/AP/
inventory line items (Phase 0's `FinancialPeriod` doesn't ingest those); a
single blended debt tranche with a cash sweep, no multi-tranche debt
sculpting; and no revolving credit facility -- if the base case runs cash
negative in some year, that's surfaced as a warning, not silently patched
over or crashed on. All of this is stated plainly in
`docs/phase2-comps-lbo-design.md` sections 4.3 and 9, not hidden in code.

## AI layer, honestly

The spec's non-negotiable rule (slide 13, verbatim): *"AI may propose or
explain. Python owns the financial math."* Concretely, in this codebase:

- The model **never sees raw data** -- it only ever sees `bundle.py`'s
  snapshot of already-computed Phase 0/2 outputs (screening score,
  valuation, LBO base/bull/bear). It cannot invent a number because it is
  never given the means to compute one; every numeric claim it makes must
  cite a `[[source: <dot.path>]]` back into that snapshot.
- `citation_validation.py` is a pure, no-network, no-LLM post-hoc check.
  It is a best-effort heuristic, not a fact-checker: an uncited number is a
  soft warning (natural prose has plenty of non-claim numbers, like "the
  5-year hold" or a section number). Two categories are hard warnings: a
  citation pointing at a bundle path that doesn't exist at all
  (`invalid_citations`), and a citation pointing at a *real* path whose
  actual value doesn't match the number stated right next to it
  (`mismatched_citations`) -- e.g. `"MOIC is 999.0x [[source:
  screening.score]]"` when `screening.score` is actually `62.4`. The second
  category was added after adversarial testing found that checking "does
  this path exist" and "does this number appear somewhere in the bundle"
  independently let exactly that kind of fabrication through clean; see
  `docs/phase4-ai-layer-design.md` section 5.1 for the full writeup.
- The IC simulator's bear-case gate (`finance_engine/ic_gate.py`) is the
  one place in this whole slice where code overrides the model outright:
  if the bear case fails a hard threshold and the model still says
  `PROCEED_TO_DD`, the stored recommendation is forced to `HOLD` -- but the
  model's original answer (`llm_recommendation`) is always preserved
  alongside it, so the override is visible and auditable, never silent.
  This lives inside `packages/finance_engine`, not `apps/api/app/ai/`,
  specifically so it is physically incapable of importing anything
  AI-related -- the AI layer calls into it, it never calls back.
- `memos` and `ic_simulations` are the only two **append-only** tables in
  the whole schema (everything else upserts in place). Every regeneration
  is a new version; nothing is ever overwritten, matching the spec's own
  requirement that a memo's output be reproducible later from its stored
  inputs.

## Rate limiting

Added once a real `ANTHROPIC_API_KEY` was configured and the repo went
public on GitHub (`docs/phase4-ai-layer-design.md` section 12, extended in
section 13 for document extraction). `POST .../memo`, `POST
.../ic-simulation` (1 and 5 paid Claude calls per invocation respectively),
and `POST .../documents/extract` (1 call, but a whole PDF's worth of
tokens) each carry two independent, stacked limits:

- **Per-company** (the real cost control): keyed on the `{company_id}` path
  parameter, not caller identity -- default `5/hour;20/day` per company per
  endpoint for memo/IC-simulation (`5/hour;15/day` for document extraction,
  slightly stricter given the larger token cost per call), capping
  worst-case spend for a single company at roughly $1/hour.
- **Per-IP** (abuse/blast-radius backstop): keyed on remote address,
  combined across all three AI endpoints -- default `10/minute`.

`POST .../ingest` gets the same two dimensions at a lighter touch (`20/
minute` per IP, `10/hour` per company) purely as good-citizenship
throttling toward SEC EDGAR/FMP, not a cost issue. Everything else (reads,
screening score, comps/LBO computation) is pure local computation and
carries no limit at all.

Exceeding a limit returns `429` with `{ "error": "rate_limit_exceeded",
"scope": "ai_per_company" | "ai_per_ip" | "extraction_per_company" |
"ingest_per_ip" | "ingest_per_company", "message": "...",
"retry_after_seconds": N }` and, where obtainable, a `Retry-After` header.
All 6 limit values are env vars (`RATE_LIMIT_ENABLED`,
`RATE_LIMIT_AI_PER_IP`, `RATE_LIMIT_AI_PER_COMPANY`,
`RATE_LIMIT_EXTRACTION_PER_COMPANY`, `RATE_LIMIT_INGEST_PER_IP`,
`RATE_LIMIT_INGEST_PER_COMPANY`), never hardcoded; set
`RATE_LIMIT_ENABLED=false` for local dev convenience. The
test suite always runs with it disabled by default (`tests/conftest.py`)
regardless of what's in `.env` -- otherwise its many repeated calls to
these same endpoints would start failing with `429`s partway through a
run -- with a small set of dedicated tests (`tests/test_rate_limit.py`)
that explicitly re-enable it with low override limits to prove a `429`
actually fires, on both dimensions independently, for both the AI and
ingest endpoints.

**Two real bugs were caught building this, not just design nuances --
both found by testing actual cross-request behavior, not by reading
slowapi's docs and assuming.**

1. slowapi's `Limiter` defaults to `key_style="url"`, which folds the raw
   request path into every rate-limit storage key. For a route like
   `/companies/{company_id}/memo`, that path is *different for every
   company* -- so with the default, the per-IP limit was silently being
   scoped to one company at a time too, completely defeating its purpose
   as a limit that combines usage "across all companies from this
   address." A dedicated test (`test_ai_per_ip_limit_fires_independently_of_company`)
   caught this immediately: hitting two different companies from the same
   client only tripped the per-IP limit after the fix
   (`key_style="endpoint"` in `app/rate_limit.py`, keying on the route's
   function name instead of its URL).
2. That fix wasn't enough on its own: `key_style="endpoint"` still
   differentiates `/memo` from `/ic-simulation` as two separate buckets
   (different view-function names), so the per-IP limit -- which the
   design doc specifies as "10/minute **across both AI endpoints
   combined**" -- was still being enforced independently per route rather
   than as one shared counter. Alternating calls between the two routes
   never tripped it at all. The actual fix needed a second, distinct
   slowapi mechanism: `shared_limit(..., scope="ai_per_ip")` instead of a
   plain `.limit()` call, on *both* routes' per-IP decorator --
   `scope=` overrides slowapi's per-endpoint differentiation entirely
   (confirmed by reading slowapi's own `__evaluate_limits`: `limit_scope =
   lim.scope or endpoint`), which `key_style` alone cannot do. The
   per-company decorators never set `scope`, so they're untouched and
   correctly keep their separate-per-endpoint behavior (design doc section
   12.2: per-company limits are "per company, per endpoint" *deliberately*
   -- a dedicated test
   (`test_ai_per_company_limit_still_separate_per_endpoint_after_shared_ip_fix`)
   confirms the second fix didn't accidentally erase that distinction too).

Both bugs were caught by dedicated tests, not incidental coverage, and
both were verified twice over: once via `TestClient`, once again against a
live `uvicorn` server over real HTTP with deliberately low override
limits, confirming the exact documented `429` JSON shape and `Retry-After`
header end-to-end in both cases.

## Data sources

- **Primary:** SEC EDGAR `companyfacts` API -- free, no key, but requires a
  descriptive `User-Agent` (set `EDGAR_USER_AGENT`).
- **Supplementary:** Financial Modeling Prep free tier -- chosen over Alpha
  Vantage for a more consistent field set and a higher free-tier request
  volume. Optional; ingestion degrades gracefully to EDGAR-only if
  `FMP_API_KEY` is unset.
- **AI layer (Phase 4 only):** the Claude API (`ANTHROPIC_API_KEY`,
  model configurable via `ANTHROPIC_MODEL`, default `claude-sonnet-4-5`).
  Confined entirely to `apps/api/app/ai/` -- `POST .../memo`,
  `POST .../ic-simulation`, and `POST .../documents/extract` are the only
  three endpoints in the whole codebase that make an outbound call to a
  third-party API.

See `docs/phase0-vertical-slice-design.md` section 5 for the full rationale
and normalization rules.

## Notes on pragmatic calls made during implementation

A few points the design doc left implicit, resolved here rather than
blocking on them:

- **EBITDA from EDGAR** is reconstructed as `operating_income +
  depreciation_and_amortization` when both XBRL tags are present. EDGAR
  does not tag EBITDA directly; this is a standard, disclosed
  reconstruction, not GAAP EBITDA as such.
- **XBRL tag aliasing is per-fiscal-year, not per-tag.** Filers migrate
  concepts over time (e.g. Apple tagged revenue as `Revenues` through
  ~2018, then switched to `RevenueFromContractWithCustomerExcluding
  AssessedTax`). The EDGAR extractor tries each alias per fiscal year and
  lets a lower-priority alias fill in years a higher-priority one doesn't
  cover, rather than committing to whichever alias has *any* data at all.
- **A factor's `source` is `"default"` whenever any part of it fell back**
  to a neutral/assumed value, even if part of the computation succeeded
  (e.g. `leverage_capacity` when `leverage_ratio` computed fine but
  `interest_expense` was null) -- this errs toward flagging partial
  data-quality issues rather than hiding them behind an all-or-nothing
  label.
- **No migrations tool.** `db/schema.sql` is a hand-maintained reference;
  the running app bootstraps its SQLite file via
  `SQLAlchemy.metadata.create_all()`. Alembic was called out as optional in
  the design doc and isn't worth the overhead for a single local dev file
  in this slice.
- **The web app has no server-side data fetching/caching layer** -- pages
  fetch client-side on mount. Fine for a single-analyst local demo; would
  need revisiting before any multi-user deployment.
- **D&A alias resolution needed a second fix beyond the tag-migration one
  above.** Testing Phase 2's EBITDA-dependent comps against real Microsoft
  and Alphabet EDGAR data (not just Apple) surfaced that many filers tag
  depreciation and intangible amortization as two *separate* concepts
  (`Depreciation` + `AmortizationOfIntangibleAssets`) with no combined
  `DepreciationDepletionAndAmortization` tag at all -- Apple happens to use
  the combined tag, which is why Phase 0's testing against Apple alone
  didn't catch it. The extractor now sums the split tags per fiscal year
  whenever no combined tag covers that year; see
  `apps/api/app/ingestion/edgar_client.py`'s
  `_depreciation_and_amortization_by_fy` and the regression tests in
  `apps/api/tests/test_edgar_client.py`.
- **The sensitivity grid centers on the last-run LBO case's resolved
  inputs, not a fresh comps lookup.** If `/run` was called with an
  explicit `entry_ev` override, `/sensitivity` reuses that exact override
  (and every other resolved input) by reading the persisted `LboCase`
  rather than re-deriving `entry_ev` from `SELECTED` peers each time --
  otherwise the two endpoints could silently disagree about what "the
  base case" even is. Falls back to a fresh comps-derived resolution only
  when no LBO case has been run yet for that scenario.
- **`ic_gate.py` takes a self-contained `BearCaseInput`, not
  `finance_engine.lbo.LboResult` directly.** The design doc's own
  pseudocode types the gate's parameter generically; rather than importing
  the full LBO dataclass (with many fields the gate doesn't need) into
  `ic_gate.py`, it takes a minimal duck-typed structure (`irr`, `moic`,
  `exit_leverage`, and a list of `{year, ebitda, interest}` rows). The API
  layer reconstructs this from a persisted `LboCase`'s columns and
  `schedule_json` at call time. This keeps the gate's dependency surface to
  exactly the 4 numbers/rows the policy check actually needs, and means it
  has zero coupling to `lbo.py`'s internal shape even though both modules
  live in the same package.
- **A factor's `source` labeling convention (Phase 0) extends naturally to
  the AI layer's `validation_report.status`.** `"ok"` vs `"warnings"`
  follows the same "surface partial data-quality issues rather than hide
  them behind an all-or-nothing flag" philosophy used throughout this
  project -- a single invalid citation, mismatched citation, or uncited
  number anywhere in a memo/transcript flips the aggregated status to
  `"warnings"`, even if every other section/role was clean.
- **The bundle building logic (`app/ai/bundle.py`) duplicates a small
  amount of DB-row-to-`finance_engine`-input glue code that also exists in
  `routers/screening.py` and `routers/comps.py`**, rather than extracting a
  shared service layer. The actual math is never duplicated (both paths
  call the same `finance_engine.score_company`/`compute_valuation`
  functions) -- only the small, mechanical "turn a SQLAlchemy row into a
  finance_engine dataclass" mapping is repeated. A shared query/service
  layer would be the right move if a 4th consumer of this mapping shows up;
  for two call sites it isn't worth the added indirection yet.
- **Live Claude API verification was not performed** -- no
  `ANTHROPIC_API_KEY` was available in the environment this was built in.
  Everything that can be verified without one was: the full offline test
  suite (`FakeClaudeClient`-backed), a live-server smoke test of every
  endpoint's routing/validation/404/422 behavior (real HTTP requests, real
  SQLite, just no real model call), and the OpenAPI schema generating
  successfully (confirming every new Pydantic response model is
  well-formed). The two live integration tests are written, correctly
  gated, and ready to run the moment a real key is available.

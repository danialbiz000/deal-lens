# DealLens — Phase 4 Design: AI Layer (Memo Writer + IC Simulator)

**Scope:** spec slides 13–15 and 20 — the IC memo generator (an explicit MVP item, "2-page memo export") and the Investment Committee simulator. Builds on Phase 0 (screening) and Phase 2 (comps + LBO), both of which remain untouched: this phase adds Claude API calls for the first time, and does not change a single formula in `packages/finance_engine`.

**The non-negotiable guardrail (spec slide 13, verbatim):** *"AI may propose or explain. Python owns the financial math. Every factual claim should retain a source or be labeled as an assumption."* Concretely, in this design: **the AI layer is architecturally incapable of inventing or overriding a number.** It only ever reads a snapshot of already-computed deterministic outputs and narrates/synthesizes/debates around them. Every number the model states must carry an inline citation into that snapshot; a hard, code-level check (not a prompt instruction) can force the IC simulator's recommendation regardless of what the model outputs. Dependency direction is one-way: `apps/api/app/ai/` may import from `packages/finance_engine`; `packages/finance_engine` never imports anything AI-related and has zero knowledge this layer exists.

**Out of scope (explicitly deferred):** a document parser for arbitrary uploaded filings/PDFs (Phase 0/2 already get structured data from EDGAR/FMP — no unstructured-ingestion need yet), a news research synthesizer (no news data source wired up), peer-classifier narrative explanations (Phase 2's algorithmic similarity + reason codes already cover this), formatted PDF/document export of the memo (structured JSON/HTML content only), in-place manual editing of generated text (regenerate a new version instead), streaming responses, cost/rate-limit management beyond basic error handling, UI polish beyond a functional trigger-and-view page.

---

## 1. Why this needs a physically separate module

`packages/finance_engine` has been the project's credibility anchor since Phase 0: zero I/O, zero nondeterminism, fully unit-tested. That guarantee must survive this phase unchanged. Concretely:

- All new AI code lives in `apps/api/app/ai/` — a new module, not a new top-level package, because it is orchestration (DB reads, API calls, persistence), not a reusable deterministic library like `finance_engine`.
- The **one exception** is the bear-case gate check (§4.3): it is deterministic financial policy logic, and it lives in `packages/finance_engine/finance_engine/ic_gate.py` — a pure function with zero AI/HTTP dependency, unit-tested exactly like `screening.py` and `lbo.py`. This placement is itself part of the guardrail: the gate cannot be construed as "AI-influenced" because it is physically incapable of importing anything from `apps/api/app/ai/`. The AI layer calls into it; it never calls back.
- A grep-able guarantee (same pattern as Phases 0 and 2): `packages/finance_engine` contains zero references to `anthropic`, `claude`, or `apps.api.app.ai` anywhere.

```
apps/api/app/ai/
├── __init__.py
├── client.py                # single choke point for the Anthropic SDK — see §2
├── bundle.py                 # build_source_bundle() — the ONLY thing the model is allowed to treat as fact, see §3
├── citation_validation.py    # pure Python, no LLM — post-hoc numeric/citation check, see §5
├── memo.py                    # generate_memo(bundle) -> sections + validation report
├── ic_simulation.py           # run_ic_simulation(bundle) -> 5-role transcript + recommendation
└── prompts/
    ├── memo_sections.py       # one shared system prompt + JSON schema for all 10 sections
    ├── ic_analyst.py
    ├── ic_industry.py
    ├── ic_credit.py
    ├── ic_risk.py
    └── ic_chair.py

packages/finance_engine/finance_engine/
└── ic_gate.py                 # evaluate_bear_case_thresholds() — pure, deterministic, zero AI
```

---

## 2. Claude API client — single choke point

`client.py` wraps the Anthropic SDK behind one narrow interface so nothing else in the codebase touches it directly, and so tests can substitute a fake with zero mocking gymnastics:

```python
class ClaudeClient(Protocol):
    def complete_structured(self, system: str, user: str, json_schema: dict) -> dict: ...
```

- Real implementation reads `ANTHROPIC_API_KEY` from the environment (never hardcoded) and the model id from `ANTHROPIC_MODEL` (env var, default `claude-sonnet-4-5` — overridable without a code change so the model can be bumped later without touching prompt logic).
- Uses Claude's tool-use / forced-JSON-schema output for every call in this phase (memo sections, each of the 5 IC roles) — **never** free-text parsing of prose into structured fields. This is a real reliability choice, not a style preference: brittle regex-parsing of LLM prose is exactly the kind of hidden nondeterminism this project has avoided everywhere else.
- `.env.example` gets two new lines: `ANTHROPIC_API_KEY=` and `ANTHROPIC_MODEL=claude-sonnet-4-5`.

---

## 3. The source bundle — the model's entire universe of facts

`bundle.py`'s `build_source_bundle(company_id, db) -> dict` is the single function that assembles everything the AI layer is allowed to know. It calls the same underlying service functions Phases 0/2 already expose via their endpoints (screening score, valuation, LBO base/bull/bear) — not new calculations — and flattens them into a dot-addressable structure:

```json
{
  "company": { "ticker": "...", "name": "...", "sector": "...", "industry": "..." },
  "screening": {
    "score": 62.4, "formula_version": "v0.1",
    "factors": { "growth": { "normalized_score": 71.2, "source": "computed", "weight": 0.15 }, ... }
  },
  "valuation": {
    "entry_ev": 0, "entry_equity_value": 0,
    "ev_ebitda": { "median": 0, "q1": 0, "q3": 0 },
    "selected_peers": [ { "ticker": "...", "ev_ebitda_multiple": 0, "similarity_score": 0 }, ... ]
  },
  "lbo": {
    "base": { "moic": 0, "irr": 0, "entry_leverage": 0, "exit_leverage": 0, "value_creation_bridge": {...} },
    "bull": { ... }, "bear": { ... }
  }
}
```

Because Phase 0's screening score and Phase 2's valuation are computed **on demand, not persisted**, this snapshot is the only stable, reproducible record of "the figures a given memo/IC run was based on" — which is exactly what the spec's `Memo` entity requires ("stores scenario, model version, source timestamps... so the output can be reproduced later," slide 15). The bundle is stored verbatim as `source_bundle_json` on both new entities (§6), so a memo remains fully reconstructable even if the underlying `FinancialPeriod`/`Assumption`/`Peer` data changes later.

Both `memo.py` and `ic_simulation.py` consume the identical bundle — one builder function, no duplicated assembly logic.

---

## 4. IC Simulator (spec slide 14)

### 4.1 Five sequential calls, not one

Matches the spec's own agent-workflow diagram exactly: **Analyst → Industry → Credit → Risk → IC Chair**, each call receiving the bundle plus every prior role's structured output (a real sequential debate, not five independent takes) — this is why it is 5 calls and not a single multi-turn generation, and why it cannot be collapsed into the memo's one-call design.

| Role | Sees | Structured output |
|---|---|---|
| Analyst | bundle only | `{ case_summary, key_points: [str] }` |
| Industry | bundle + Analyst | `{ market_challenges: [str] }` |
| Credit | bundle + Analyst + Industry | `{ credit_concerns: [str] }` — prompt explicitly directs it to reference the bear-case LBO figures in the bundle |
| Risk | bundle + all prior | `{ risk_flags: [str] }` |
| IC Chair | bundle + all 4 prior | `{ llm_recommendation: "PROCEED_TO_DD"\|"HOLD"\|"PASS", key_strengths: [str], key_risks: [str], unanswered_dd: [str] }` |

Every prose field from every role is run through citation validation (§5) before being persisted, same as memo sections.

### 4.2 The recommendation enum

Three states, matching a real IC's actual range of outcomes (the spec's illustrative example only shows the positive case, `PROCEED TO DD`, but a simulator needs the other two to be a real gate):
- `PROCEED_TO_DD` — the only "positive" recommendation
- `HOLD` — needs more work/data before advancing
- `PASS` — the LLM's own judgment, never forced by the code (the override in §4.3 only ever pushes *toward* more conservative, never the reverse)

### 4.3 The deterministic override — code, not prompt

Spec's rule, verbatim: *"Do not permit a positive recommendation if critical assumptions fail the bear case thresholds."* This must hold even if the model ignores every instruction in its prompt, so it is enforced by `finance_engine.ic_gate.evaluate_bear_case_thresholds(bear_lbo_result) -> GateResult`, called by `apps/api/app/ai/ic_simulation.py` **after** the IC Chair call returns, independent of anything the LLM said:

```python
BEAR_IRR_FLOOR = 0.08              # typical PE hurdle rate
BEAR_MOIC_FLOOR = 1.0              # capital loss below this
BEAR_EXIT_LEVERAGE_CEILING = 6.0   # still overlevered at exit -> refinancing risk
# + any schedule year in the bear case where ebitda_t <= interest_t (interest coverage < 1.0x)
```

```python
def evaluate_bear_case_thresholds(bear_case: LBOResult) -> GateResult:
    failures = []
    if bear_case.irr < BEAR_IRR_FLOOR: failures.append(f"bear IRR {bear_case.irr:.1%} below floor {BEAR_IRR_FLOOR:.0%}")
    if bear_case.moic < BEAR_MOIC_FLOOR: failures.append(f"bear MOIC {bear_case.moic:.2f}x below {BEAR_MOIC_FLOOR}x (capital loss)")
    if bear_case.exit_leverage > BEAR_EXIT_LEVERAGE_CEILING: failures.append(f"bear exit leverage {bear_case.exit_leverage:.1f}x exceeds {BEAR_EXIT_LEVERAGE_CEILING}x")
    for year_row in bear_case.schedule:
        if year_row.ebitda <= year_row.interest:
            failures.append(f"year {year_row.year}: EBITDA does not cover interest (coverage < 1.0x)")
    return GateResult(passes=(len(failures) == 0), failures=failures)
```

Override logic (in `ic_simulation.py`, immediately after the IC Chair call):
```python
gate = evaluate_bear_case_thresholds(bear_lbo_result)
llm_recommendation = ic_chair_output["llm_recommendation"]
if not gate.passes and llm_recommendation == "PROCEED_TO_DD":
    final_recommendation = "HOLD"
    override_fired = True
    override_reason = "; ".join(gate.failures)
else:
    final_recommendation = llm_recommendation
    override_fired = False
    override_reason = None
```

Both `llm_recommendation` (what the model actually said) and `recommendation` (the final, possibly-overridden value) are persisted — an override is a visible, auditable event, never a silent correction. Running the IC simulation requires a `BEAR` `LBOCase` to already exist for the company (`422` otherwise); `BASE`/`BULL` are needed too since the bundle includes all three.

---

## 5. Citation validation (`citation_validation.py`) — pure Python, no LLM

Every prompt (memo sections and all 5 IC roles) carries the same instruction: **any numeric claim must be immediately followed by an inline tag `[[source: <dot.path>]]`** referencing the exact key in the source bundle where that number lives (e.g. `Bear-case IRR is 6.2% [[source: lbo.bear.irr]]`). Qualitative commentary or judgment that isn't a bundle-backed fact must be phrased as commentary, not as a cited claim.

`validate_citations(text: str, bundle: dict) -> ValidationReport` is a pure function (regex + dict traversal, no network, fully unit-testable with synthetic inputs):

1. Extract every `[[source: <path>]]` tag.
2. For each, attempt to resolve `<path>` by dot-traversal into `bundle`. Unresolvable path → **`invalid_citations`** (hard signal — the model cited a fact that does not exist in the data; this is a genuine hallucination-on-the-citation-mechanism-itself, and is surfaced prominently as a warning, distinct from an uncited number).
3. Separately, regex-extract standalone numeric tokens (percentages, `x`-multiples, currency amounts) from the text. For each, check whether it sits within a short word-window of a citation tag, or whether a rounded/formatted match exists anywhere in the bundle's values. No match on either → **`uncited_numbers`** (a soft, best-effort heuristic warning, not a failure — natural language contains plenty of non-claim numbers like "5-year hold" or section numbering, so this will have false positives by design and is documented as an auditability aid, not a fact-checker).
4. Output: `{ total_citations, invalid_citations: [...], uncited_numbers: [...], status: "ok"|"warnings" }`.

Design decision: neither category blocks generation or storage — this is a best-effort heuristic layered on top of the prompt instruction, not a hard gate (unlike the IC bear-case gate in §4.3, which *is* hard because it protects a recommendation, not a narrative). `invalid_citations` should be rendered as a clear warning banner in the UI; `uncited_numbers` is informational.

### 5.1 Addendum — `mismatched_citations` (post-implementation fix)

**Gap found in adversarial testing, fixed on explicit user instruction after implementation.** Steps 2 and 3 above check "does this path exist" and "does this number appear anywhere in the bundle" *independently*. That leaves a real gap: a fabricated number paired with a citation to a real-but-unrelated bundle path passes both checks cleanly — e.g. `"MOIC is 999.0x [[source: screening.score]]"` against `screening.score = 62.4` originally produced `invalid_citations: []`, `uncited_numbers: []`, `status: "ok"`. The path is real (step 2 passes) and *some* number in the text technically has a tag near it (step 3's loose proximity check was satisfied by that same tag), but the two were never cross-checked against each other.

Fix: a third category, **`mismatched_citations`**, folded into the same hard-signal severity as `invalid_citations` (both flip `status` to `"warnings"`). For every citation tag, the numeric token immediately adjacent to it (a tight ~20-character window, not the looser 40-character window used for the general uncited-number heuristic) is resolved against *that specific citation's* bundle value — not the bundle at large — with tolerance for normal formatting variance (percent-vs-fraction dual interpretation, e.g. `6.2%` matching a bundle value of either `6.2` or `0.062`; common currency-scale suffixes `bn`/`billion`/`mn`/`million`; ~2% relative / 0.05 absolute tolerance for rounding). A number with no citation tag immediately adjacent still falls through to the original step-3 heuristic unchanged. Output is now `{ total_citations, invalid_citations, mismatched_citations, uncited_numbers, status }`. Implementation: `apps/api/app/ai/citation_validation.py`; regression coverage (including the exact adversarial case above) in `apps/api/tests/test_citation_validation.py`.

---

## 6. Schema additions

Both new entities are **append-only and versioned**, a deliberate departure from Phase 0/2's upsert-in-place pattern (`Assumption`, `Peer`, `Scenario` all have one live row per key) — because the spec explicitly wants memo/IC reproducibility across regenerations ("Memo... version, timestamp," slide 15), not just a single current state. Regenerating creates a new row with `version = max(existing) + 1`; old versions remain fetchable.

### 6.1 `memos`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | String(36) | PK | uuid4 |
| company_id | String(36) | FK -> companies.id, NOT NULL, INDEXED | |
| version | Integer | NOT NULL | |
| prompt_version | String(20) | NOT NULL | e.g. `memo_prompt_v0.1`, independent of `formula_version` upstream |
| model | String(50) | NOT NULL | resolved model id actually used |
| source_bundle_json | JSON | NOT NULL | snapshot per §3 |
| sections_json | JSON | NOT NULL | array of `{ section_key, title, content }`, the 10 spec-named sections (§7.1) |
| validation_report_json | JSON | NOT NULL | per §5, aggregated across all 10 sections |
| generated_at | DateTime | NOT NULL | |
| created_at | DateTime | NOT NULL | |

Unique constraint: `(company_id, version)`.

### 6.2 `ic_simulations`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | String(36) | PK | uuid4 |
| company_id | String(36) | FK -> companies.id, NOT NULL, INDEXED | |
| version | Integer | NOT NULL | |
| model | String(50) | NOT NULL | |
| source_bundle_json | JSON | NOT NULL | |
| transcript_json | JSON | NOT NULL | ordered array of the 5 role outputs + their individual `validation_report` |
| llm_recommendation | String(15) | NOT NULL | raw IC Chair output, pre-override |
| recommendation | String(15) | NOT NULL | final, possibly-overridden value |
| override_fired | Boolean | NOT NULL, DEFAULT false | |
| override_reason | Text | NULLABLE | populated iff `override_fired` |
| key_strengths_json | JSON | NOT NULL | |
| key_risks_json | JSON | NOT NULL | |
| unanswered_dd_json | JSON | NOT NULL | |
| generated_at | DateTime | NOT NULL | |
| created_at | DateTime | NOT NULL | |

Unique constraint: `(company_id, version)`.

---

## 7. Memo generation (spec slide 15)

### 7.1 One structured call, ten fixed sections

Unlike the IC simulator, the memo is generated in **one** call with a forced JSON schema requesting an array of exactly the 10 spec-named sections (cheaper, simpler to test, and there's no "debate" structure to preserve the way there is for the IC roles):

```
transaction_overview | company_and_industry | investment_thesis | financial_performance |
comparable_valuation | lbo_returns | value_creation_plan | risks_and_downside |
dd_questions | recommendation
```

System prompt (shared preamble, the guardrail spelled out for the model itself, not just enforced after the fact):
> "You are drafting sections of an internal PE investment committee memo. You are given a JSON bundle of pre-computed, verified financial figures — this is your only source of numeric fact. Do not invent, calculate, adjust, or estimate any number not present in the bundle. Every numeric claim must be immediately followed by `[[source: <dot.path>]]` citing the exact bundle key. If you want to make a qualitative judgment not backed by the bundle, phrase it explicitly as commentary or opinion, never as a cited fact. Output must match the provided JSON schema exactly: an array of 10 objects with `section_key`, `title`, `content`."

### 7.2 Prerequisites

Generating a memo (or running an IC simulation, §4) requires: a screening score is computable (i.e. `FinancialPeriod` data exists), `GET .../valuation` succeeds (≥2 `SELECTED` peers), and at least a `BASE` `LBOCase` exists (memo) / `BASE`+`BULL`+`BEAR` all exist (IC simulation, since the gate needs `BEAR` specifically and the bundle wants all three). Missing prerequisites return `422` naming exactly what's missing and which endpoint to call first — same pattern as Phase 2's `422`s.

---

## 8. API contract

| Endpoint | Purpose |
|---|---|
| `POST /companies/{id}/memo` | Generate a new memo version from current state; `422` if prerequisites unmet |
| `GET /companies/{id}/memo` | List memo versions (summary: version, generated_at, validation status) |
| `GET /companies/{id}/memo/{version}` | Fetch one full memo version |
| `POST /companies/{id}/ic-simulation` | Run a new IC simulation version; `422` if prerequisites unmet |
| `GET /companies/{id}/ic-simulation` | List IC simulation versions (summary incl. `recommendation`, `override_fired`) |
| `GET /companies/{id}/ic-simulation/{version}` | Fetch one full IC simulation version (transcript + gate detail) |

Both `POST` endpoints are the only two in the whole codebase that make outbound network calls to a third-party API — document this plainly in the response (`503` with a clear message, not a raw stack trace, if the Claude API errors or times out).

---

## 9. Testing strategy

- `ClaudeClient` (§2) is a `Protocol`/injectable interface. The default test suite uses a `FakeClaudeClient` returning canned structured JSON — **zero live network calls, zero API key required** to run `pytest` normally, matching the FMP-key-optional pattern already used for Phase 2's market-data tests.
- `citation_validation.py` and `finance_engine/ic_gate.py` are pure functions — fully unit-tested with synthetic inputs, no mocking needed at all.
- Required constructed test cases for the gate: one bear case passing all thresholds, and one failing *each* individual threshold (IRR floor, MOIC floor, exit leverage ceiling, interest-coverage breach) — 5 cases minimum.
- Required constructed test proving the override actually overrides: mock the IC Chair call to return `PROCEED_TO_DD` while feeding a bear-case `LBOCase` that fails a threshold; assert the persisted `recommendation` is `HOLD`, `override_fired` is `true`, and `llm_recommendation` still shows the original `PROCEED_TO_DD` (the override must be visible, not silently substituted).
- One optional **live** integration test per feature (`test_memo_live.py`, `test_ic_simulation_live.py`) that skips gracefully (`pytest.mark.skipif` on `ANTHROPIC_API_KEY` absence) — when the key *is* present, it runs one real memo generation and one real IC simulation against the seeded demo company and asserts basic shape (10 sections present, recommendation is one of the 3 valid enum values) rather than exact content, since LLM output isn't byte-reproducible the way the rest of this project deliberately is.

---

## 10. Acceptance criteria — Phase 4 "done" checklist

- [ ] `memos` and `ic_simulations` tables added (append-only/versioned, unique on `(company_id, version)`), Postgres-portable per prior phases' rules.
- [ ] `apps/api/app/ai/` created; `packages/finance_engine` has zero imports of anything AI-related anywhere (grep-able) except being imported *by* the AI module, never the reverse.
- [ ] `finance_engine/ic_gate.py` is a pure function with the 4 named threshold constants, unit tested against 5+ constructed bear-case scenarios (pass-all, and one failing each threshold individually).
- [ ] `bundle.py`'s `build_source_bundle` assembles the full nested structure from §3 against a seeded demo company, unit tested.
- [ ] All Claude API access goes through the single `ClaudeClient` interface; default `pytest` run requires no `ANTHROPIC_API_KEY` and makes no network calls.
- [ ] Memo generation produces exactly the 10 named sections via schema-forced structured output (not prose parsing).
- [ ] `citation_validation.py` unit tested: correctly extracts valid citations, correctly flags a constructed invalid citation (nonexistent bundle path), correctly demonstrates both a flagged and an unflagged case for the uncited-number heuristic.
- [ ] IC simulation runs the 5 roles strictly sequentially, each receiving the full prior transcript; the override test from §9 passes (LLM says `PROCEED_TO_DD`, bear case fails a threshold, stored `recommendation` is `HOLD` with `override_fired=true` and the original `llm_recommendation` preserved).
- [ ] All 6 endpoints implemented with the documented `422` prerequisite checks.
- [ ] Regeneration creates a new version (append-only); old versions remain individually fetchable via `GET .../memo/{version}` and `GET .../ic-simulation/{version}`.
- [ ] Optional live integration tests exist for both features, skip gracefully without `ANTHROPIC_API_KEY`, pass when the key is present (verified once locally with a real key by whoever implements this, not required for CI).
- [ ] `.env.example` updated with `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` (default `claude-sonnet-4-5`); no API key hardcoded anywhere in source.
- [ ] `apps/web` has a minimal functional page to trigger memo/IC generation for a company and view the latest version (memo: 10 sections with citation warnings surfaced; IC: 5-role transcript, final recommendation, and a visible override banner when `override_fired` is true) — no styling polish required.
- [ ] README walkthrough extended: after Phase 2's LBO runs (base/bull/bear all present), generate a memo and run an IC simulation for the same demo company; note plainly that `ANTHROPIC_API_KEY` must be set for this step specifically, unlike every prior phase.

---

## 12. Rate limiting (added post-review — cost control)

Added after Phase 4 review: a real `ANTHROPIC_API_KEY` is now configured, and the repo is public on GitHub, so the two AI endpoints need a hard ceiling on paid API usage before anyone (including a future publicly-deployed instance) can run up cost by hitting them repeatedly. This is a small addition to the already-built Phase 4 surface, not a new phase — no new entities, no new business logic, just guards in front of existing endpoints.

### 12.1 Which endpoints, and why

| Endpoint | Priority | Why |
|---|---|---|
| `POST /companies/{id}/memo` | **High** | 1 paid Claude call per invocation |
| `POST /companies/{id}/ic-simulation` | **High** | 5 sequential paid Claude calls per invocation — the single most expensive action in the whole app |
| `POST /companies/{id}/ingest` | Low | Calls external SEC EDGAR/FMP APIs — free, but both have courtesy-request expectations worth respecting; not a cost-control issue, just good citizenship |
| Everything else (reads, screening score, comps/LBO computation) | None | Pure local computation or local DB reads — no external cost, no reason to limit; do not over-apply this |

### 12.2 Two independent limit dimensions on the AI endpoints

A single dimension isn't enough: a per-IP limit alone doesn't stop one company's memo/IC-simulation from being regenerated endlessly by different callers, and a per-company limit alone doesn't stop one client hammering many different companies. Both `POST /companies/{id}/memo` and `POST /companies/{id}/ic-simulation` get **both**, stacked:

- **Per-company limit** (business-cost control — this is the one that actually matters): keyed on the `{id}` path parameter, not on caller identity. Default **`5/hour` and `20/day`** per company, per endpoint. Rationale: at the documented ~$0.15–0.20 for one memo + one IC-simulation run, 5 full regenerations/hour/company caps worst-case spend for a single company at roughly $1/hour — generous for genuine iterative demo use (tweaking an assumption and re-running), well below "someone is scripting this in a loop."
- **Per-IP limit** (abuse/backstop): keyed on remote address. Default **`10/minute`** across both AI endpoints combined. This is the blast-radius cap if something loops or a public instance gets hit repeatedly from one source — independent of which company is targeted.

### 12.3 Ingestion endpoint (lighter touch)

`POST /companies/{id}/ingest` gets a lighter pair of limits, same two dimensions, purely as good API citizenship toward EDGAR/FMP rather than cost control: default **`20/minute` per IP** and **`10/hour` per company**.

### 12.4 Mechanism

In-memory rate limiting is the right call here, not a distributed store — this is a single-instance FastAPI app backed by SQLite, and there is no multi-process/multi-node deployment in scope anywhere in this project. Use `slowapi` (wraps the `limits` package, integrates with FastAPI via a decorator + a registered exception handler) rather than hand-rolling a token bucket — it directly supports everything needed here: multiple named limiter instances with different key functions (one keyed by `get_remote_address`, one by a custom function reading `request.path_params["id"]`), multi-window limit strings (`"5/hour;20/day"` in one decorator), and a `RateLimitExceeded` exception with enough information to build a `429` response and a `Retry-After` header. If stacking two independent `Limiter` instances' decorators on one route proves awkward in practice, a small hand-rolled in-memory fixed-window counter (a `dict[key, deque[timestamp]]` guarded by a lock) is an acceptable fallback for the exact same two-dimension scheme — implementer's judgment, the *behavior* specified above is what matters, not the specific library.

New module: `apps/api/app/rate_limit.py` — defines the limiter instance(s), the company-id key function, and the `429` response shape:
```json
{ "error": "rate_limit_exceeded", "scope": "ai_per_company" | "ai_per_ip" | "ingest_per_ip" | "ingest_per_company",
  "message": "Rate limit exceeded: 5 per hour for this company. Try again later.",
  "retry_after_seconds": 1234 }
```
Set the `Retry-After` header on the response whenever the underlying limiter can supply the window reset time; a missing header is acceptable if that turns out to be awkward to extract, but the JSON body's `retry_after_seconds` should always be attempted.

### 12.5 Configuration — env vars, not hardcoded constants

Following the same "named, documented, overridable" pattern as every other calibration constant in this project:

| Env var | Default | Meaning |
|---|---|---|
| `RATE_LIMIT_ENABLED` | `true` | Global on/off switch — set `false` for local dev convenience without touching code |
| `RATE_LIMIT_AI_PER_IP` | `10/minute` | Backstop, both AI endpoints combined |
| `RATE_LIMIT_AI_PER_COMPANY` | `5/hour;20/day` | Business cost control, per AI endpoint per company |
| `RATE_LIMIT_INGEST_PER_IP` | `20/minute` | |
| `RATE_LIMIT_INGEST_PER_COMPANY` | `10/hour` | |

Values use the `limits` package's own string syntax directly (e.g. `"5/hour;20/day"`) rather than separate numeric env vars per window — fewer env vars, and directly parseable by the library doing the enforcement. Add all 5 to `.env.example` with the defaults above.

### 12.6 Testing implication — do not let this break the existing suite

The in-memory limiter's state persists for the lifetime of the test process, and the existing Phase 0/2/4 test suites call these same endpoints many times across many test functions in one run. Without accounting for this, the full suite would start failing with `429`s partway through a run — a real, easy-to-miss regression. Required approach: the test configuration sets `RATE_LIMIT_ENABLED=false` by default (e.g. in `conftest.py` / the test settings override), so the existing suite is unaffected, with a small number of **dedicated** rate-limit tests that explicitly set `RATE_LIMIT_ENABLED=true` and use very low limits (e.g. `2/minute`) to prove a `429` actually fires on the 3rd call and that the response includes the documented fields.

### 12.7 Acceptance criteria — rate limiting

- [ ] `POST /companies/{id}/memo` and `POST /companies/{id}/ic-simulation` each enforce both the per-company and per-IP limits from §12.2.
- [ ] `POST /companies/{id}/ingest` enforces both limits from §12.3.
- [ ] All limit values are read from the 5 env vars in §12.5, not hardcoded in route code; `RATE_LIMIT_ENABLED=false` fully disables enforcement.
- [ ] Exceeding a limit returns `429` with the documented JSON body shape and, where feasible, a `Retry-After` header.
- [ ] A dedicated test proves the per-company AI limit fires (low override limit, 3rd call in the window returns 429) and a separate test proves the per-IP limit fires independently of company.
- [ ] The full existing test suite (Phases 0, 2, 4) still passes unmodified in behavior with rate limiting wired in — confirmed via `RATE_LIMIT_ENABLED=false` in test config, per §12.6.
- [ ] `.env.example` updated with the 5 new env vars and their defaults.
- [ ] `requirements.txt` updated if `slowapi` is added (or no new dependency if the hand-rolled fallback is used instead).

---

## 11. Explicitly deferred (not this phase)

~~Document parser for arbitrary uploaded filings/PDFs~~ **built, see §13**; news research synthesizer; peer-classifier narrative explanations (Phase 2's algorithmic similarity already covers this); formatted PDF/document export of the memo (structured content only); in-place manual editing of generated text (regenerate a new version instead); streaming responses; sophisticated cost/rate-limit management; multi-tenant auth; cloud deployment; UI polish beyond a functional trigger-and-view page. All consistent with the spec's own MVP/v1.0 split (slide 20) and this project's running discipline of building exactly the vertical slice in front of it before adding the next layer.

## 13. Document extraction for private-company financials (v1.0)

The manual-entry workflow (`POST /companies/{id}/financials`, phase0 design doc §8) closes the "how does a private company's data get in at all" gap, but still requires an analyst to retype every figure by hand. `POST /companies/{id}/documents/extract` (`apps/api/app/routers/financials.py`) removes that retyping step: upload a financial statement or investor-relations PDF, and Claude's document-understanding API reads it and proposes one candidate period per reporting period found, each numeric field paired with a short verbatim citation quote so a reviewer can check it in seconds without re-reading the source document.

This is additive, not a replacement — it never writes to the database itself. The spec's own guidance is explicit here ("Implement filing extraction with source spans, confidence, and a human-review queue. Never write extracted values directly into the financial model without validation."), and the existing, already-tested `POST /companies/{id}/financials` endpoint remains the *only* path from "a number" to a trusted `FinancialPeriod` row — an extracted candidate reaches the database through the identical review-and-save flow a manually-typed period does, just prefilled. Zero new database-write code paths were added for this feature.

`ClaudeClient` (`apps/api/app/ai/client.py`) gained a second method, `complete_structured_from_document`, alongside the existing text-only `complete_structured` — same forced-JSON-schema contract, but the message content is `[document block, text instruction]` instead of a plain string, using Claude's Messages API document content-block format (`{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": ...}}`). Both real (`AnthropicClaudeClient`) and fake (`FakeClaudeClient`, tests) implementations share the same call/parse plumbing as the text-only path, refactored into a private `_create_and_parse` helper.

One real API constraint discovered live (never caught by the fake test client, same class of gap as the §7.1/memo `minItems`/`maxItems` issue): Anthropic's structured-output schema rejects a schema with more than 16 nullable/union-typed (`"type": ["number", "null"]`-style) parameters ("too many parameters with union types ... causes exponential compilation cost"). The first draft of `financial_extraction.JSON_SCHEMA` paired 11 nullable numeric fields with 11 nullable citation-string fields (22 total) and was rejected with a live 400. Fixed by changing `citations` from a fixed object (one nullable key per numeric field) to a variable-length array of `{field, quote}` pairs — only fields Claude actually found get an entry, so no nullability is needed there at all, dropping the count back to 11. `extraction.py` converts that array back into a `{field: quote}` dict before it reaches the router/schema/UI, so nothing downstream needed to change shape. A regression test (`test_extraction_schema_stays_under_anthropic_union_type_limit`, mirroring the memo schema's own `minItems`/`maxItems` regression test) walks the schema tree so this can't silently reappear.

Rate-limited the same way as `/memo` and `/ic-simulation` (§12 of this doc): shares the combined `ai_per_ip` backstop across all three Claude-calling endpoints, plus its own dedicated per-company budget (`SCOPE_EXTRACTION_PER_COMPANY`, stricter default than memo/IC since a whole document is far more tokens per call than a pre-computed bundle).

Verified live end-to-end against the real Anthropic API with a hand-built minimal PDF (a short one-page financial summary with revenue, adjusted EBITDA, a parenthesized negative capex figure, total debt, and cash): the endpoint returned all five figures correctly extracted, capex correctly normalized to a positive magnitude, each figure paired with an accurate citation, and an honest `notes` field flagging which standard fields (gross profit, EBIT, net income, operating cash flow, interest expense, shares outstanding) the document simply didn't contain rather than guessing at them.

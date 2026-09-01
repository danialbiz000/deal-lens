# DealLens — Phase 0 Vertical Slice Design

**Scope:** Company -> Financials -> Screening Score, end-to-end, for public companies only. No comps, no LBO, no AI layer. This is the spec's own recommended first build (spec slide 19: *"Implement Company -> Financials -> Screening Score end-to-end. Use typed schemas, tests, and seed data. Do not build LBO yet."*).

**Non-goals for this slice:** Peer/comps engine, Transaction data, Scenario/LBOCase, Memo generation, any AI/LLM call. These come in later phases per the spec's roadmap (slide 17).

**Guiding principle (spec slide 1 & 13):** deterministic finance engine, strictly separate from any future AI layer. Every number in this slice must trace to a formula or a stored source — no black boxes, no manual fudge factors hidden in code.

---

## 1. Monorepo structure

Kept lean — three real workspaces, not a platform.

```
deal-lens/
├── apps/
│   ├── web/                        # Next.js 14+ (App Router), TypeScript, React
│   │   ├── app/
│   │   │   ├── page.tsx                    # company list
│   │   │   └── companies/[id]/page.tsx     # company detail + screening score
│   │   ├── lib/api.ts                      # thin fetch client for apps/api
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   └── api/                        # FastAPI application
│       ├── app/
│       │   ├── main.py                     # FastAPI app, router registration, /health
│       │   ├── config.py                   # env/settings (pydantic-settings)
│       │   ├── db.py                       # SQLAlchemy engine/session, get_db dependency
│       │   ├── models/                     # SQLAlchemy ORM models
│       │   │   ├── company.py
│       │   │   ├── financial_period.py
│       │   │   └── assumption.py
│       │   ├── schemas/                    # Pydantic request/response DTOs
│       │   │   ├── company.py
│       │   │   ├── financial_period.py
│       │   │   ├── assumption.py
│       │   │   └── screening.py
│       │   ├── routers/
│       │   │   ├── companies.py            # POST/GET /companies, GET /companies/{id}
│       │   │   ├── financials.py           # POST /companies/{id}/ingest, GET .../financials
│       │   │   ├── assumptions.py          # POST/GET /companies/{id}/assumptions
│       │   │   └── screening.py            # GET /companies/{id}/screening-score
│       │   └── ingestion/
│       │       ├── edgar_client.py         # SEC/EDGAR company facts fetch + parse
│       │       ├── market_data_client.py   # Alpha Vantage OR FMP client (pick one, see §5)
│       │       └── normalize.py            # currency/units/period normalization (spec slide 5)
│       ├── tests/
│       │   ├── test_companies_api.py
│       │   ├── test_ingestion_normalize.py
│       │   └── test_screening_api.py
│       ├── requirements.txt
│       └── alembic/ (optional)             # only if migrations are wanted beyond schema.sql
│
├── packages/
│   └── finance_engine/             # pure Python, zero FastAPI/DB/HTTP deps — importable & unit-testable standalone
│       ├── finance_engine/
│       │   ├── __init__.py
│       │   ├── types.py                    # FinancialPeriodInput, AssumptionInput dataclasses
│       │   ├── factors.py                  # the 4 computable factor functions
│       │   ├── screening.py                # score_company(periods, assumptions) -> ScreeningResult
│       │   └── constants.py                # normalization anchors, weights (versioned, see §3)
│       ├── tests/
│       │   ├── test_factors.py
│       │   └── test_screening.py
│       └── pyproject.toml
│
├── db/
│   ├── schema.sql                  # canonical DDL, Postgres-portable (source of truth alongside ORM models)
│   └── seed/
│       └── seed_demo_company.py    # loads one real public company end-to-end for local dev/demo
│
├── docs/
│   └── phase0-vertical-slice-design.md   # this file
│
├── .env.example
└── README.md                       # setup + the one-command demo walkthrough (see §6 acceptance criteria)
```

Why `packages/finance_engine` is separate from `apps/api`: the spec's core design principle is deterministic-engine-vs-AI-layer separation. Physically isolating the scoring math from the web framework means (a) it has zero HTTP/DB test overhead, (b) it can be reused unchanged when the AI layer is added later (the AI layer must never write into it directly — only through validated Assumption rows), and (c) it's the one package that should never import anything nondeterministic.

---

## 2. Database schema — Company, FinancialPeriod, Assumption

Target: SQLite file for local Phase 0 dev (`deal_lens.db`), trivially portable to Postgres later. Portability rules applied throughout:
- Primary keys are `String(36)` UUIDs generated in Python (`uuid4()`), not DB-native UUID or autoincrement — identical behavior on SQLite and Postgres.
- Money/ratio fields use SQLAlchemy `Numeric` (maps to `DECIMAL` on Postgres, `NUMERIC` on SQLite) — never `Float`, to avoid binary rounding drift in financial figures.
- Timestamps stored as UTC `DateTime`.
- No SQLite-only pragmas or features relied upon anywhere in application code.

### 2.1 `companies`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | String(36) | PK | uuid4 |
| ticker | String(16) | UNIQUE, NOT NULL | public-company ticker, uppercase |
| cik | String(10) | UNIQUE, NULLABLE | SEC EDGAR CIK, zero-padded string; nullable until first ingest resolves it |
| name | String(255) | NOT NULL | |
| sector | String(100) | NULLABLE | free text for MVP (GICS sector later) |
| industry | String(100) | NULLABLE | |
| country | String(2) | NULLABLE | ISO 3166-1 alpha-2 |
| reporting_currency | String(3) | NOT NULL, DEFAULT 'USD' | currency of the raw financials as filed |
| description | Text | NULLABLE | |
| created_at | DateTime | NOT NULL, server default now | |
| updated_at | DateTime | NOT NULL, server default now, on update now | |

Relations: one-to-many -> `financial_periods`, one-to-many -> `assumptions`.

### 2.2 `financial_periods`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | String(36) | PK | uuid4 |
| company_id | String(36) | FK -> companies.id, NOT NULL, INDEXED | |
| fiscal_year | Integer | NOT NULL | |
| period_end_date | Date | NOT NULL | canonical period end |
| period_type | String(4) | NOT NULL | `FY`, `Q1`..`Q4`, or `TTM` |
| currency | String(3) | NOT NULL | as-reported currency for this row, pre-normalization |
| source | String(20) | NOT NULL | `SEC_EDGAR` \| `ALPHA_VANTAGE` \| `FMP` \| `MANUAL` |
| source_ref | String(255) | NULLABLE | e.g. EDGAR accession number, or API request id — audit trail |
| revenue | Numeric(20,2) | NULLABLE | |
| gross_profit | Numeric(20,2) | NULLABLE | |
| ebitda | Numeric(20,2) | NULLABLE | as-reported or reconstructed; see §3 for how the engine derives FCF/margins from this |
| ebit | Numeric(20,2) | NULLABLE | |
| net_income | Numeric(20,2) | NULLABLE | |
| operating_cash_flow | Numeric(20,2) | NULLABLE | |
| capex | Numeric(20,2) | NULLABLE | stored as a positive magnitude (outflow); documented sign convention |
| total_debt | Numeric(20,2) | NULLABLE | |
| cash_and_equivalents | Numeric(20,2) | NULLABLE | |
| interest_expense | Numeric(20,2) | NULLABLE | |
| shares_outstanding | Numeric(20,2) | NULLABLE | |
| is_estimate | Boolean | NOT NULL, DEFAULT false | |
| raw_payload | JSON | NULLABLE | verbatim snapshot of the source API response for this period — reproducibility per spec slide 5's "store raw... separately" rule |
| ingested_at | DateTime | NOT NULL, server default now | |

Unique constraint: `(company_id, period_end_date, period_type, source)` — prevents duplicate ingestion from the same source, while deliberately *allowing* the same period to exist from two different sources (e.g. SEC_EDGAR and FMP both report FY2023) so provenance conflicts stay visible rather than being silently overwritten. The screening engine (§3) always prefers `SEC_EDGAR` over other sources when both exist for the same period, per the spec's Tier-1-source-first rule (slide 5).

Deliberately **not** stored as columns: `net_debt`, `free_cash_flow`, `net_working_capital`. These are always *derived* by the finance engine from the raw fields above (net_debt = total_debt − cash_and_equivalents; FCF = operating_cash_flow − capex) rather than persisted, so there is exactly one place the formula lives and no risk of a stored derived value silently drifting from its inputs.

### 2.3 `assumptions`

The placeholder/manual-input mechanism for anything the financial-derived engine cannot compute (see §3).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | String(36) | PK | uuid4 |
| company_id | String(36) | FK -> companies.id, NOT NULL, INDEXED | |
| name | String(100) | NOT NULL | key used to look up the assumption, e.g. `business_quality_score` |
| value_numeric | Numeric(10,4) | NULLABLE | |
| value_text | String(500) | NULLABLE | for qualitative assumptions; numeric and text are mutually exclusive by convention |
| unit | String(30) | NULLABLE | e.g. `score_0_100`, `percent`, `x` |
| source | String(100) | NOT NULL | e.g. `manual:analyst`, `default:neutral` |
| confidence | Numeric(3,2) | NULLABLE | 0.00–1.00 |
| notes | Text | NULLABLE | |
| created_at | DateTime | NOT NULL, server default now | |
| updated_at | DateTime | NOT NULL, server default now, on update now | |

Unique constraint: `(company_id, name)` — the API upserts by name (§4), so there is always exactly one live value per assumption key per company, with `updated_at` as the audit trail. (Full history-of-overrides / versioning is a v1.0 concern, per spec slide 20; out of scope here.)

---

## 3. Screening Score — the 8 factors

Formula per spec slide 6: `Score = sum(weight_i * normalized_factor_i)`, each `normalized_factor_i` on a 0–100 scale, weights summing to 1.0. This slice computes the score **on demand** from current `FinancialPeriod` + `Assumption` rows — it is not persisted as its own table yet (no `Scenario`/versioning entity exists in this slice), so add a `formula_version` string constant (`"v0.1"`) to every response so the specific version of the calibration constants below is always traceable even before real persistence/versioning is built.

### 3.1 Which factors are computable now vs. placeholder-only

| Factor | Weight | Computable from `FinancialPeriod`? | Mechanism |
|---|---|---|---|
| Growth | 15% | **Yes** | Revenue CAGR |
| Margins | 15% | **Yes** | Avg. EBITDA margin |
| Cash conversion | 15% | **Yes** | Avg. FCF / EBITDA |
| Leverage capacity | 10% | **Yes** | Net debt/EBITDA + interest coverage |
| Business quality | 20% | **No** — recurring revenue %, retention, market position are not in `FinancialPeriod` | `Assumption` row, default neutral 50 |
| Market structure | 10% | **No** — fragmentation, pricing power, competitive intensity are qualitative | `Assumption` row, default neutral 50 |
| Exit optionality | 10% | **No** — strategic buyer universe, sponsor appetite; real signal needs `Transaction`/`Peer` data, out of scope this slice | `Assumption` row, default neutral 50 |
| Management / execution | 5% | **No** — track record, key-person risk, governance | `Assumption` row, default neutral 50 |

Honest limitation to state plainly in the UI and README: **45% of the score's weight (Business quality 20 + Market structure 10 + Exit optionality 10 + Management 5) is manual/placeholder in this slice**, defaulting to a neutral 50 until an analyst supplies an `Assumption`. Only the remaining 55% is derived purely from financial data today. This is intentional and spec-compliant (slide 7 lists these as needing "a simple rule, a data source, and an explanation field" — for the qualitative ones, the "rule" *is* "ask a human," and the "source" is `Assumption.source`).

### 3.2 Computable factor formulas (`packages/finance_engine`)

Use up to the **3 most recent `FY` (annual) periods**, preferring `SEC_EDGAR` source when duplicates exist across sources for the same period. All normalization anchors below are named constants in `finance_engine/constants.py`, not inline magic numbers, so they're independently unit-testable and tunable without touching the scoring logic.

**Growth (15%)** — requires ≥2 FY periods; if only 1 exists, factor = `None` and the engine substitutes the neutral default 50 with a `data_quality` warning (not silently computed as 0).
```
revenue_cagr = (revenue_latest / revenue_earliest) ** (1 / n_years) - 1
score = clamp((revenue_cagr - (-0.10)) / (0.30 - (-0.10)) * 100, 0, 100)
# -10% CAGR -> 0 pts | 0% -> 25 pts | 10% -> 50 pts | 30%+ -> 100 pts
```

**Margins (15%)** — average EBITDA margin across available FY periods (periods with revenue <= 0 excluded, not divided-by-zero).
```
ebitda_margin_t = ebitda_t / revenue_t
avg_margin = mean(ebitda_margin_t for available periods)
score = clamp(avg_margin / 0.40 * 100, 0, 100)
# 0% margin -> 0 pts | 20% -> 50 pts | 40%+ -> 100 pts
```

**Cash conversion (15%)** — FCF is always recomputed, never read from a stored field (see §2.2).
```
fcf_t = operating_cash_flow_t - capex_t
cash_conversion_t = fcf_t / ebitda_t   # skip periods where ebitda_t <= 0
avg_cash_conversion = mean(cash_conversion_t for available periods)
score = clamp(avg_cash_conversion * 100, 0, 100)
# 0% or negative -> 0 pts | 50% -> 50 pts | 100%+ -> 100 pts
```

**Leverage capacity (10%)** — latest FY period only (point-in-time balance-sheet metric), 50/50 blend of two sub-scores.
```
net_debt = total_debt - cash_and_equivalents
leverage_ratio = net_debt / ebitda_latest        # if ebitda_latest <= 0 -> leverage_score = 0, flagged
leverage_score = clamp((1 - leverage_ratio / 6) * 100, 0, 100)
# 0x net debt/EBITDA -> 100 pts | 6x+ -> 0 pts

interest_coverage = ebitda_latest / interest_expense_latest   # if interest_expense is null/0 -> coverage_score = 100 (no debt service burden), flagged
coverage_score = clamp((interest_coverage - 1) / (10 - 1) * 100, 0, 100)
# 1x coverage -> 0 pts | 10x+ -> 100 pts

leverage_capacity_score = (leverage_score + coverage_score) / 2
```

### 3.3 Placeholder factors (Assumption-based)

For `business_quality_score`, `market_structure_score`, `exit_optionality_score`, `management_execution_score`:
```
value = Assumption.value_numeric where company_id = X and name = "<factor>_score"
if not found: value = 50   # neutral default
```
Each is expected on a `0–100` scale (`unit = "score_0_100"`) so it combines with the computed factors without a separate normalization step. The API for writing these (§4) validates the value is in `[0, 100]`.

### 3.4 Final score
```
score = 0.20*business_quality + 0.15*growth + 0.15*margins + 0.15*cash_conversion
      + 0.10*leverage_capacity + 0.10*market_structure + 0.10*exit_optionality
      + 0.05*management_execution
```
A unit test in `packages/finance_engine/tests/test_screening.py` must assert the 8 weights sum to exactly `1.0` so a future edit can't silently break the formula's completeness.

---

## 4. API contract (FastAPI, `apps/api`)

All responses are JSON. All list endpoints support basic pagination later; not required for this slice's acceptance criteria.

### `GET /health`
Trivial liveness check for CI/deploy. `200 {"status": "ok"}`.

### `POST /companies`
Create a company.
```
Request:  { "ticker": "AAPL", "name": "Apple Inc.", "cik": "0000320193",
            "sector": "Technology", "industry": "Consumer Electronics",
            "country": "US", "reporting_currency": "USD" }
Response: 201 { "id": "uuid", "ticker": "AAPL", "name": "Apple Inc.", ... , "created_at": "..." }
Errors:   409 if ticker or cik already exists
```

### `GET /companies`
List companies (for the dashboard's company list). `200 [ {company summary}, ... ]`

### `GET /companies/{id}`
```
Response: 200 { ...company fields..., "latest_financial_period": { ... } | null }
Errors:   404 if not found
```

### `POST /companies/{id}/ingest`
Pulls financials from SEC/EDGAR (primary) plus the chosen market-data API (supplementary — see §5) and upserts `FinancialPeriod` rows.
```
Request:  { "years_back": 3, "sources": ["SEC_EDGAR", "FMP"] }   # sources optional, defaults to both configured
Response: 200 { "company_id": "uuid", "ingested_periods": 3,
                "periods": [ {financial_period}, ... ],
                "warnings": [ "FMP: shares_outstanding missing for FY2022" ] }
Errors:   404 if company not found, 502 if upstream source unreachable (with which source in the message)
```

### `GET /companies/{id}/financials`
```
Query params: period_type? (FY|Q1..Q4|TTM), limit? (default 10)
Response: 200 [ {financial_period}, ... ]   # newest first
```

### `POST /companies/{id}/assumptions`
Upsert-by-name a manual assumption (the placeholder mechanism from §3.3).
```
Request:  { "name": "business_quality_score", "value_numeric": 65,
            "unit": "score_0_100", "source": "manual:analyst",
            "confidence": 0.7, "notes": "Strong retention per 10-K MD&A" }
Response: 200 { "id": "uuid", "company_id": "uuid", "name": "business_quality_score", ... }
Errors:   422 if value_numeric outside [0, 100] for a *_score assumption
```

### `GET /companies/{id}/assumptions`
`200 [ {assumption}, ... ]`

### `GET /companies/{id}/screening-score`
The slice's core deliverable endpoint.
```
Response: 200 {
  "company_id": "uuid",
  "formula_version": "v0.1",
  "score": 62.4,
  "factors": [
    { "name": "business_quality", "weight": 0.20, "normalized_score": 50,
      "source": "default", "contribution": 10.0, "notes": "no assumption on file; neutral default used" },
    { "name": "growth", "weight": 0.15, "normalized_score": 71.2,
      "source": "computed", "contribution": 10.68, "notes": "revenue CAGR 18.4% over 2 years, FY2021-FY2023" },
    ...
  ],
  "warnings": [ "management_execution: no assumption on file; neutral default (50) used" ],
  "computed_at": "2026-09-01T12:00:00Z"
}
Errors:   404 if company not found, 422 if no FinancialPeriod rows exist yet ("run /ingest first")
```

---

## 5. Data sources for MVP

- **Primary (Tier 1 per spec slide 5):** SEC EDGAR `companyfacts` API (`data.sec.gov/api/xbrl/companyfacts/CIK##########.json`) — free, no key required, but requires a `User-Agent` header identifying the app per SEC's access policy. Supplies revenue, EBITDA-adjacent XBRL tags (operating income + D&A reconstruction where EBITDA isn't tagged directly), cash flow statement lines, balance sheet lines.
- **Supplementary (Tier 2):** pick **Financial Modeling Prep (FMP)** over Alpha Vantage for this slice — its free tier exposes a single `/v3/income-statement`, `/v3/balance-sheet-statement`, `/v3/cash-flow-statement` set of endpoints per ticker with consistent field names and higher free-tier request volume (250/day) than Alpha Vantage (25/day), which matters when iterating during development. Used to backfill fields EDGAR's raw XBRL tagging makes awkward (e.g., a clean `ebitda` figure, `sharesOutstanding`) and as a cross-check.
- Normalization rules applied in `ingestion/normalize.py` per spec slide 5: currency left as-reported for MVP (no live FX — single-currency demo companies only, USD), accounting periods mapped to canonical `fiscal_year` + `period_end_date` + `period_type`, units normalized to plain currency units (not millions) with `Numeric(20,2)` precision, signs made consistent (capex always positive magnitude, debt always positive), `source_ref` and `raw_payload` always preserved for audit.

---

## 6. Acceptance criteria — "Phase 0 slice is done" checklist

- [ ] Monorepo scaffolded exactly per §1; `apps/web` renders a default page, `apps/api` serves `GET /health` returning `200`.
- [ ] `db/schema.sql` and the SQLAlchemy models in `apps/api/app/models/` agree on the 3 tables in §2; running against a local SQLite file works with zero code changes required to point `DATABASE_URL` at Postgres later (verified by keeping all types portable per §2's rules).
- [ ] `POST /companies` creates a company; duplicate `ticker` or `cik` returns `409`.
- [ ] `POST /companies/{id}/ingest` pulls >= 2 fiscal years of real data for one demo public ticker from SEC EDGAR, supplemented by FMP, with `source`, `source_ref`, and `raw_payload` populated on every ingested `FinancialPeriod` row.
- [ ] `GET /companies/{id}/financials` returns the normalized periods matching what was ingested.
- [ ] `packages/finance_engine` has unit tests for all 4 computable factors (`growth`, `margins`, `cash_conversion`, `leverage_capacity`) covering: normal case, single-period/missing-data case, negative-EBITDA case, zero-revenue case, and zero-interest-expense case — all deterministic, no I/O.
- [ ] A unit test asserts the 8 factor weights sum to `1.0`.
- [ ] `GET /companies/{id}/screening-score` returns a 0–100 score with all 8 factors itemized and each factor's `source` correctly labeled `computed` / `default`; placeholder factors default to neutral 50 when no `Assumption` exists.
- [ ] `POST /companies/{id}/assumptions` lets an analyst set any of the 4 manual factors; a subsequent `GET .../screening-score` call reflects the override, and calling it twice with the same inputs returns the identical score (no randomness anywhere in this code path).
- [ ] Zero AI/LLM API calls exist anywhere in this slice's code path — grep-able guarantee (no `anthropic`, `openai` imports in `apps/api` or `packages/finance_engine`).
- [ ] `README.md` documents a fresh-clone-to-working-demo path: install deps -> set `.env` (EDGAR user-agent string + FMP API key) -> run migrations/`schema.sql` -> run `db/seed/seed_demo_company.py` for one real ticker -> start `apps/api` -> start `apps/web` -> see the company's screening score in the browser.
- [ ] `apps/web` has a company list page and a company detail page showing the screening score breakdown (styling can be minimal — the point is proving the contract end-to-end, not visual polish, per the user's explicit priority: correctness/auditability before UI polish, matching spec slide 17's stated priority order).

---

## 7. Explicitly deferred (not this slice)

Comps/`Peer`, `Transaction`, `Scenario`, `LBOCase`, `Memo` entities and all associated engines/endpoints; any document parsing, synthesis, IC-agent, or memo-writing AI functionality; multi-currency FX conversion; private-company upload workflow; auth; cloud deployment. All per spec slide 20's MVP/v1.0 scope split and slide 17's phased roadmap — this document only covers Phase 0/1 (repo + schema + data layer) and the screening half of Phase 2.

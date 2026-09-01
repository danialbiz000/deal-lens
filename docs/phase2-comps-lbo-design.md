# DealLens — Phase 2 Design: Comparable Companies + LBO Underwriting

**Scope:** spec slides 8–12, MVP column of slide 20 — basic peer comps, entry valuation, a 5-year LBO, base/bull/bear scenarios, and an entry/exit multiple sensitivity grid. Builds directly on the Phase 0 slice (`docs/phase0-vertical-slice-design.md`) — same discipline: deterministic Python, zero AI/LLM involvement, every number traces to a formula or a stored input.

**Out of scope (explicitly deferred):** `Transaction`/precedent-transactions entity, `Memo`/IC-memo generator, any AI/LLM layer, multi-tranche debt sculpting, full tornado sensitivity across all 6 variables (growth/margin/entry multiple/leverage/interest rate/exit multiple — only entry×exit multiple is in scope here), granular working-capital ingestion (AR/AP/inventory line items — see §4.3 for how NWC is simplified without it), auth, cloud deployment, UI polish beyond functional pages.

---

## 1. Schema additions

### 1.1 `companies` — new columns (additive, non-breaking to Phase 0)

Comps multiples need a peer's *market* EV, which needs market cap — not captured in Phase 0. Rather than a new price-history entity (out of scope — this is deal screening, not a trading terminal), store the latest known snapshot directly on `companies`, refreshed on ingest:

| Column | Type | Notes |
|---|---|---|
| market_cap | Numeric(20,2) | NULLABLE |
| share_price | Numeric(12,4) | NULLABLE |
| market_data_as_of | Date | NULLABLE |
| market_data_source | String(20) | NULLABLE, e.g. `FMP` |

`POST /companies/{id}/ingest` (existing Phase 0 endpoint) is extended to also call FMP's profile/quote endpoint and populate these 4 fields — no new ingestion endpoint needed.

### 1.2 `peers` (new table)

Spec slide 5 describes `Peer` as "peer identity + similarity attributes." Pragmatic deviation: since this MVP is public-companies-only and every company — target or peer — goes through the identical EDGAR/FMP pipeline from Phase 0, a peer is not a separate identity record; it is a **relationship row between a target `Company` and a peer `Company`** (both full rows in the same `companies` table). This avoids maintaining two different representations of "a company" in the schema. A private-company peer with no ingestion pipeline (identity-only, per the spec's literal wording) is a v1.0 concept — deferred.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | String(36) | PK | uuid4 |
| target_company_id | String(36) | FK -> companies.id, NOT NULL, INDEXED | |
| peer_company_id | String(36) | FK -> companies.id, NOT NULL, INDEXED | must already exist as an ingested `Company` |
| status | String(10) | NOT NULL | `CANDIDATE` \| `SELECTED` \| `REJECTED` |
| reason_code | String(40) | NULLABLE | see §2.2 |
| reason_notes | Text | NULLABLE | free text, required when an analyst manually overrides status |
| similarity_score | Numeric(5,2) | NULLABLE | 0–100, null if hard-filtered out before scoring |
| ev_revenue_multiple | Numeric(10,4) | NULLABLE | snapshot at last computation |
| ev_ebitda_multiple | Numeric(10,4) | NULLABLE | snapshot at last computation |
| source | String(30) | NOT NULL | `auto:top_k_similarity` \| `manual:analyst` |
| computed_at | DateTime | NOT NULL | |
| created_at, updated_at | DateTime | NOT NULL | |

Unique constraint: `(target_company_id, peer_company_id)` — one relationship row per pair, upserted on regeneration (status/reason/multiples refresh in place; this is why `REJECTED` peers stay visible instead of being deleted — the spec's explicit rule that "peer selection should never be silently accepted" is satisfied by every candidate, selected or rejected, remaining a queryable row with a reason).

### 1.3 `scenarios` (new table)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | String(36) | PK | uuid4 |
| company_id | String(36) | FK -> companies.id, NOT NULL, INDEXED | |
| case_type | String(4) | NOT NULL | `BASE` \| `BULL` \| `BEAR` |
| revenue_growth_rate | Numeric(6,4) | NOT NULL | annual, applied flat across the hold period |
| ebitda_margin_delta | Numeric(6,4) | NOT NULL | additive vs. entry-year margin, ramped linearly to this value by the final hold year (§4.2) |
| exit_multiple_delta | Numeric(6,4) | NOT NULL | additive vs. entry multiple |
| source | String(30) | NOT NULL | `default:spec_calibration` \| `manual:analyst` |
| notes | Text | NULLABLE | |
| created_at, updated_at | DateTime | NOT NULL | |

Unique constraint: `(company_id, case_type)` — exactly one of each case per company, upserted (same pattern as Phase 0's `Assumption` table).

### 1.4 `lbo_cases` (new table)

Modeled as a computed-artifact snapshot, not a wide flat table of every input — full inputs and the year-by-year schedule live in JSON columns (exact shapes in §4.5) so the whole waterfall is inspectable without recomputation, while key outputs get real columns for querying/sorting.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | String(36) | PK | uuid4 |
| company_id | String(36) | FK -> companies.id, NOT NULL, INDEXED | |
| scenario_id | String(36) | FK -> scenarios.id, NOT NULL, INDEXED | |
| formula_version | String(20) | NOT NULL | `lbo_v0.1` |
| inputs_json | JSON | NOT NULL | resolved snapshot of every input used (§4.5) — reproducible even if `Assumption`/`Scenario` rows change later |
| sources_uses_json | JSON | NOT NULL | §4.5 |
| schedule_json | JSON | NOT NULL | year-by-year array, §4.5 |
| value_creation_bridge_json | JSON | NOT NULL | §5 |
| entry_ev | Numeric(20,2) | NOT NULL | |
| exit_ev | Numeric(20,2) | NOT NULL | |
| exit_equity_value | Numeric(20,2) | NOT NULL | |
| moic | Numeric(10,4) | NOT NULL | |
| irr | Numeric(10,4) | NOT NULL | |
| entry_leverage | Numeric(6,2) | NOT NULL | new_debt / entry_ebitda — should equal the `lbo_leverage_multiple` assumption; a cheap built-in consistency check |
| exit_leverage | Numeric(6,2) | NOT NULL | ending_debt / exit_ebitda |
| computed_at | DateTime | NOT NULL | |
| created_at, updated_at | DateTime | NOT NULL | |

Unique constraint: `(company_id, scenario_id)` — one live LBO case per company+scenario, upserted on re-run (same "same inputs -> same outputs, no history yet" pattern as Phase 0; full run history/versioning is a v1.0 concern).

### 1.5 New `Assumption` keys (no schema change — reuses Phase 0's mechanism)

The LBO's capital-structure and operating-simplification inputs are genuinely analyst-overridable choices (not "unknowable" like Phase 0's management-quality score), so they use the existing `assumptions` table rather than new columns — same "default unless overridden, source always labeled" transparency pattern.

| name | default | unit | meaning |
|---|---|---|---|
| lbo_leverage_multiple | 5.0 | x | new debt / entry EBITDA (spec's illustrative entry leverage) |
| lbo_interest_rate | 0.08 | percent | annual cash interest on the debt balance |
| lbo_cash_sweep_pct | 1.0 | percent | share of excess FCF swept to debt paydown after mandatory amortization |
| lbo_mandatory_amort_pct | 0.01 | percent | % of *original* principal amortized per year |
| lbo_tax_rate | 0.25 | percent | cash tax rate |
| lbo_capex_pct_revenue | historical avg capex/revenue from `FinancialPeriod`; 0.03 if no history | percent | |
| lbo_nwc_pct_revenue_change | 0.05 | percent | NWC cash absorbed per $1 of revenue growth — see §4.3 for why this is a simplification |
| lbo_transaction_fees_pct | 0.02 | percent | fees as % of purchase EV |
| lbo_hold_period_years | 5 | years | |

---

## 2. Comparable companies engine

### 2.1 Peer universe (known MVP limitation, stated plainly)

There is no automated market/sector screener in this slice. The peer candidate pool is **companies already ingested into DealLens** (i.e. an analyst must `POST /companies` + `/ingest` a handful of plausible peers through the same Phase 0 pipeline before generating comps for a target). This mirrors Phase 0's honesty about the `Assumption` placeholders: real peer discovery (screening the whole public market) is a v1.0 data-connector problem, not a comps-formula problem, and is deferred accordingly.

### 2.2 Hard filters (rejection, no scoring needed)

Applied before similarity scoring; each sets `status = REJECTED` with a `reason_code`:

- `MISSING_FINANCIALS` — peer has no `FY` `FinancialPeriod` with both `revenue` and `ebitda` populated, or has no `market_cap`.
- `REVENUE_SCALE_MISMATCH` — peer's latest-FY revenue is outside `[target_revenue * 0.33, target_revenue * 3.0]`.
- `SELF` — a company cannot be its own peer (defensive check, not user-facing in practice).

### 2.3 Similarity score (0–100), for candidates that pass the hard filters

Uses each company's **latest FY** `FinancialPeriod` (consistent point-in-time comparison, same convention as Phase 0's leverage factor):

```
sector_score   = 50 if peer.sector == target.sector else 0
industry_score = 20 if peer.industry == target.industry else 0

revenue_ratio  = peer_latest_revenue / target_latest_revenue
log_ratio      = abs(ln(revenue_ratio))
scale_score    = clamp(15 * (1 - log_ratio / ln(3)), 0, 15)
# identical revenue -> 15 pts | 3x or 1/3x apart (the hard-filter boundary) -> 0 pts

peer_margin    = peer_latest_ebitda / peer_latest_revenue
target_margin  = target_latest_ebitda / target_latest_revenue
margin_diff    = abs(peer_margin - target_margin)
margin_score   = clamp(15 * (1 - margin_diff / 0.20), 0, 15)
# identical margin -> 15 pts | 20+ pt margin gap -> 0 pts

similarity_score = sector_score + industry_score + scale_score + margin_score   # max 100
```

Generating peers for a target with `sector = null` returns `422` — sector is required for candidate generation (it must be set at company creation or backfilled before running comps).

### 2.4 Selection

`POST /companies/{id}/peers/generate` upserts a `Peer` row for every other ingested company against the target: hard-filtered ones become `REJECTED` with their reason code; the rest become `CANDIDATE` with a `similarity_score`, and the **top 5 by similarity score (configurable, min score 50 by default)** are auto-promoted to `SELECTED` with `source = auto:top_k_similarity`. This keeps the endpoint useful out of the box while satisfying "never silently accepted": every non-selected candidate is still a visible, queryable row with a computed score, and every rejection carries a reason code. An analyst overrides any row's status via `PATCH .../peers/{peer_id}`, which sets `source = manual:analyst` and requires `reason_notes`.

### 2.5 Entry valuation (`GET /companies/{id}/valuation`)

Using only `SELECTED` peers (min. 2 required, else `422`):

```
peer_ev = peer.market_cap + peer.total_debt(latest FY) - peer.cash_and_equivalents(latest FY)
ev_revenue_multiple = peer_ev / peer.revenue(latest FY)
ev_ebitda_multiple  = peer_ev / peer.ebitda(latest FY)
```
(These two multiples are the values snapshotted onto the `Peer` row in §2.4.)

```
median_ev_revenue, q1_ev_revenue, q3_ev_revenue = quartiles(selected peers' ev_revenue_multiple)
median_ev_ebitda,  q1_ev_ebitda,  q3_ev_ebitda  = quartiles(selected peers' ev_ebitda_multiple)

implied_ev_from_revenue = median_ev_revenue * target_latest_revenue
implied_ev_from_ebitda  = median_ev_ebitda  * target_latest_ebitda

entry_ev = implied_ev_from_ebitda        # EV/EBITDA is the standard PE convention; EV/Revenue is returned as a cross-check only, not blended in
entry_net_debt = target_total_debt(latest FY) - target_cash_and_equivalents(latest FY)
entry_equity_value = entry_ev - entry_net_debt
```

`entry_ev` and the target's latest-FY EBITDA/revenue here are the values the LBO engine (§4) consumes as "Year 0" — the same underlying `FinancialPeriod` row, so `entry_multiple` recomputed inside the LBO (`entry_ev / entry_ebitda`) is always internally consistent with the comps step.

---

## 3. Scenario framework

`POST /companies/{id}/scenarios/generate` upserts exactly 3 `Scenario` rows. Base case reuses Phase 0's own growth-factor CAGR calculation (import from `finance_engine`, do not reimplement) rather than a fresh calculation — one growth formula in the whole codebase.

| case_type | revenue_growth_rate | ebitda_margin_delta | exit_multiple_delta | Rationale |
|---|---|---|---|---|
| BASE | historical 3yr revenue CAGR from `FinancialPeriod` (Phase 0's growth-factor formula) | 0.0 | 0.0 | "Consensus / normalized... market exit multiple" (spec slide 12) |
| BULL | base + 0.05 | +0.02 | +1.0 | "High growth, margin expansion, flat-to-up exit multiple" |
| BEAR | base − 0.05 (floored at −0.05) | −0.02 | **−2.0** | Spec slide 12 gives bear's exit-multiple delta explicitly: "-2.0x exit multiple" |

These deltas are named constants in `finance_engine/constants.py` (`BULL_GROWTH_DELTA`, `BEAR_GROWTH_DELTA`, `BULL_MARGIN_DELTA`, `BEAR_MARGIN_DELTA`, `BULL_EXIT_MULTIPLE_DELTA`, `BEAR_EXIT_MULTIPLE_DELTA`), independently unit-testable, and every value is analyst-overridable via `PATCH /companies/{id}/scenarios/{case_type}` (sets `source = manual:analyst`).

---

## 4. LBO underwriting engine (`packages/finance_engine`, pure Python)

New modules: `finance_engine/comps.py` (similarity scoring + multiples math from §2), `finance_engine/lbo.py` (the waterfall below). Both zero I/O, zero DB/HTTP — same discipline as Phase 0's `screening.py`.

### 4.1 Sources & Uses (Year 0)

```
purchase_ev   = entry_ev                          # from §2.5, or an explicit override
fees_amount   = purchase_ev * lbo_transaction_fees_pct
new_debt      = entry_ebitda * lbo_leverage_multiple
uses_total    = purchase_ev + fees_amount
sponsor_equity = uses_total - new_debt            # equity is the plug, standard LBO convention
sources_total = new_debt + sponsor_equity
reconciles    = abs(sources_total - uses_total) < 0.01   # must always be true by construction; asserted in a test, not just trusted
```

### 4.2 Operating case, year by year (t = 1..hold_period_years)

`base_margin = entry_ebitda / entry_revenue` (Year 0). Margin delta ramps linearly to its full scenario value by the final hold year rather than stepping immediately — a more realistic and still fully deterministic/testable choice:

```
revenue_t     = revenue_(t-1) * (1 + revenue_growth_rate)     # revenue_0 = entry_revenue
margin_t      = base_margin + ebitda_margin_delta * (t / hold_period_years)
ebitda_t      = revenue_t * margin_t
capex_t       = revenue_t * lbo_capex_pct_revenue
delta_rev_t   = revenue_t - revenue_(t-1)
nwc_invest_t  = delta_rev_t * lbo_nwc_pct_revenue_change      # see §4.3
```

### 4.3 Working capital — documented simplification

Phase 0's `FinancialPeriod` has no AR/AP/inventory line items (out of scope there), so precise NWC modeling isn't possible yet. Rather than block the LBO on a data-model expansion, NWC investment is approximated as a flat percentage of *incremental* revenue (`lbo_nwc_pct_revenue_change`, default 5%) — a standard back-of-envelope LBO convention. This is a real, stated limitation, not a hidden shortcut: granular working-capital ingestion (and a proper NWC drag/release diagnostic per spec slide 7) is a v1.0 item.

### 4.4 Debt schedule and cash flow waterfall

```
interest_t          = beginning_debt_(t-1) * lbo_interest_rate          # on beginning-of-year balance
pretax_income_t     = ebitda_t - capex_t - interest_t                   # capex stands in for D&A as a tax shield proxy — standard simplifying convention for an illustrative model; a real depreciation schedule is a v1.0 refinement
taxes_t             = max(0, pretax_income_t) * lbo_tax_rate            # no loss carryforward benefit in MVP
cfads_t             = ebitda_t - capex_t - taxes_t - nwc_invest_t       # cash flow available for debt service

mandatory_amort_t   = min(beginning_debt_(t-1), new_debt * lbo_mandatory_amort_pct)
cash_before_sweep_t = cfads_t - interest_t - mandatory_amort_t
sweep_t             = clamp(cash_before_sweep_t, 0, beginning_debt_(t-1) - mandatory_amort_t) * lbo_cash_sweep_pct
unswept_cash_t      = cash_before_sweep_t - (sweep_t if cash_before_sweep_t > 0 else 0)

ending_debt_t  = beginning_debt_(t-1) - mandatory_amort_t - sweep_t
ending_cash_t  = beginning_cash_(t-1) + unswept_cash_t
# beginning_debt_0 = new_debt ; beginning_cash_0 = 0 (cash-free/debt-free close, standard convention)
```

No revolving credit facility is modeled: if `cash_before_sweep_t` is negative, `ending_cash_t` is allowed to go negative rather than crashing or silently flooring at zero. A negative ending-cash value in `schedule_json` is a genuine warning worth surfacing (it means the base case as specified would need incremental financing not modeled here) — add it to the `warnings` array in the run response; do not build a revolver mechanic to fix it, that's out of scope.

### 4.5 Exit, returns, and the JSON shapes

```
exit_ebitda    = ebitda_N                          # N = hold_period_years
exit_multiple  = entry_multiple + exit_multiple_delta      # entry_multiple = entry_ev / entry_ebitda
exit_ev        = exit_ebitda * exit_multiple
exit_net_debt  = ending_debt_N - ending_cash_N
exit_equity_value = exit_ev - exit_net_debt

moic = exit_equity_value / sponsor_equity
irr  = moic ** (1 / hold_period_years) - 1          # single entry/exit, no interim distributions modeled — clean-exit convention, standard for an illustrative LBO
```

`inputs_json` shape:
```json
{
  "entry_ev": 0, "entry_ebitda": 0, "entry_revenue": 0, "entry_multiple": 0,
  "lbo_leverage_multiple": 5.0, "lbo_interest_rate": 0.08, "lbo_cash_sweep_pct": 1.0,
  "lbo_mandatory_amort_pct": 0.01, "lbo_tax_rate": 0.25, "lbo_capex_pct_revenue": 0.03,
  "lbo_nwc_pct_revenue_change": 0.05, "lbo_transaction_fees_pct": 0.02,
  "hold_period_years": 5, "revenue_growth_rate": 0.0, "ebitda_margin_delta": 0.0,
  "exit_multiple_delta": 0.0
}
```

`sources_uses_json` shape:
```json
{ "sources": { "new_debt": 0, "sponsor_equity": 0 },
  "uses": { "purchase_ev": 0, "fees": 0 },
  "reconciles": true }
```

`schedule_json` shape — array of per-year rows, `year: 0` included as the entry snapshot:
```json
[ { "year": 0, "revenue": 0, "ebitda": 0, "beginning_debt": 0, "ending_debt": 0, "ending_cash": 0 },
  { "year": 1, "revenue": 0, "ebitda": 0, "margin": 0, "capex": 0, "nwc_investment": 0,
    "interest": 0, "taxes": 0, "cfads": 0, "mandatory_amort": 0, "sweep": 0,
    "beginning_debt": 0, "ending_debt": 0, "beginning_cash": 0, "ending_cash": 0 },
  ... ]
```

---

## 5. Value creation bridge (`GET`-able via `value_creation_bridge_json` on the `LBOCase`)

Spec slide 11 requires the attribution to "reconcile exactly to the model outputs" — not merely illustrative. Derivation (verified algebraically, not just numerically, so it reconciles by construction rather than needing a plug/rounding line):

```
ebitda_at_entry_margin = revenue_N * base_margin        # what EBITDA would be if margin never moved
ebitda_growth      = (ebitda_at_entry_margin - entry_ebitda) * entry_multiple      / sponsor_equity
margin_expansion   = (exit_ebitda - ebitda_at_entry_margin) * entry_multiple       / sponsor_equity
debt_paydown       = (new_debt - exit_net_debt)                                   / sponsor_equity
multiple_expansion = exit_ebitda * (exit_multiple - entry_multiple)               / sponsor_equity
transaction_fees   = -fees_amount                                                 / sponsor_equity
entry_equity       = 1.00
```

Identity (proved by algebraic expansion of `Exit_EV - Entry_EV` and `Entry_EV - new_debt = sponsor_equity - fees`): `entry_equity + ebitda_growth + margin_expansion + debt_paydown + multiple_expansion + transaction_fees == moic`, exactly, no residual. This is a hard unit-test requirement (tolerance `1e-6`), not a soft approximation — if a future change to the LBO math breaks this identity, the test must fail loudly.

Note the deviation from spec slide 11's 5-line illustrative example: this design adds a 6th line (`transaction_fees`) specifically *because* slide 11 also says the calculation "should reconcile exactly" — with fees excluded there's a small unexplained gap between the components and the actual MOIC. Showing fees as an explicit small drag is more honest than folding it invisibly into another line.

**Red flag rule (spec slide 11, literal):**
```
value_creation_total = moic - 1.00     # everything except the entry-equity baseline
exit_multiple_dependent = (value_creation_total > 0) and (multiple_expansion / value_creation_total > 0.50)
```
If `value_creation_total <= 0` (the deal loses money on these assumptions), report `exit_multiple_dependent = false` and add a separate `value_destructive = true` flag instead — being multiple-dependent isn't the relevant problem in that case.

---

## 6. Sensitivity grid (`GET /companies/{id}/lbo/{case_type}/sensitivity`)

Entry × exit multiple grid only (spec's other 5 sensitivity variables — growth, margin, leverage, interest rate — are explicitly deferred to v1.0's "tornado + scenario engine," per spec slide 20). Query params `step` (default `1.0`) and `size` (default `4`, matching spec slide 12's illustrative 4×4).

```
entry_multiples = [ base_entry_multiple + (i - (size-1)/2) * step  for i in range(size) ]
exit_multiples  = [ base_exit_multiple  + (i - (size-1)/2) * step  for i in range(size) ]
```
For every `(entry_multiple_i, exit_multiple_j)` pair, recompute the *entire* LBO (new `purchase_ev = entry_ebitda * entry_multiple_i`, hence new `sponsor_equity`, unchanged operating case, `exit_ev = exit_ebitda * exit_multiple_j`) using the same `finance_engine.lbo` function as the main run — no separate/duplicated sensitivity formula. Response returns `entry_multiples`, `exit_multiples`, an `irr_grid`, and a `moic_grid` (both `size × size`, row = entry multiple, column = exit multiple). Not persisted — computed on demand, same as Phase 0's screening score.

A monotonicity unit test is required in addition to golden-value tests: holding entry multiple fixed, IRR must strictly increase as exit multiple increases (and vice versa) — this catches sign/indexing bugs that a single hardcoded expected grid would not.

---

## 7. API contract summary

| Endpoint | Purpose |
|---|---|
| `POST /companies/{id}/peers/generate` | Generate/refresh candidate peers; auto-select top-K by similarity |
| `GET /companies/{id}/peers?status=` | List peers (candidate/selected/rejected), filterable |
| `PATCH /companies/{id}/peers/{peer_id}` | Analyst override of status + required `reason_notes` |
| `GET /companies/{id}/valuation` | Median/quartile multiples from selected peers, implied EV, entry equity value |
| `POST /companies/{id}/scenarios/generate` | Upsert Base/Bull/Bear scenarios (Base derives from real historical CAGR) |
| `PATCH /companies/{id}/scenarios/{case_type}` | Analyst override of growth/margin/exit-multiple deltas |
| `POST /companies/{id}/lbo/{case_type}/run` | Run/re-run the deterministic LBO; body may override `entry_ev` |
| `GET /companies/{id}/lbo/{case_type}` | Fetch the last-computed LBOCase (no recompute) |
| `GET /companies/{id}/lbo/{case_type}/sensitivity` | Entry×exit multiple IRR/MOIC grid |

`case_type` path segments are `base` \| `bull` \| `bear` (lowercase in the URL, mapped to the stored `BASE`/`BULL`/`BEAR`). All `run`/`generate` endpoints are idempotent upserts — calling twice with unchanged inputs yields byte-identical JSON, per this whole project's "deterministic and reproducible" principle.

---

## 8. Acceptance criteria — Phase 2 "done" checklist

- [ ] `db/schema.sql` and ORM models updated: `companies` gets the 4 market-data columns; `peers`, `scenarios`, `lbo_cases` tables added, all Postgres-portable per Phase 0's rules (String(36) UUID PKs, `Numeric` not `Float`, JSON columns work identically on SQLite/Postgres).
- [ ] `/ingest` extended to populate `market_cap`/`share_price`/`market_data_as_of`/`market_data_source` from FMP.
- [ ] `POST /companies/{id}/peers/generate` applies the hard filters with correct reason codes, computes similarity per §2.3, auto-selects top-K, and is idempotent (regenerating without new data doesn't change existing manual overrides' `source`).
- [ ] `PATCH .../peers/{peer_id}` override works and requires `reason_notes`.
- [ ] `GET .../valuation` returns correct median/quartile multiples and entry EV/equity bridge from `SELECTED` peers only; `422` with <2 selected peers.
- [ ] `POST .../scenarios/generate` derives Base growth via `finance_engine`'s existing CAGR function (not a reimplementation); Bull/Bear deltas match §3's table exactly, including the spec-literal `-2.0x` bear exit-multiple delta.
- [ ] `finance_engine/lbo.py` unit tests cover: a standard 5-year run; exact Sources=Uses reconciliation; exact debt-schedule roll-forward; a scenario where debt is fully repaid before year 5 (cash accumulates, no negative-debt bug); a bear case with a negative-CFADS year (no sweep, no crash, correct warning); zero-interest edge case; and the value-creation bridge reconciling to `moic` within `1e-6` across at least 3 distinct scenarios.
- [ ] Exit-multiple-dependent flag unit-tested with one deliberately multiple-dependent constructed case and one that isn't; value-destructive case also tested.
- [ ] `POST .../lbo/{case_type}/run` upserts one `LBOCase` per company+scenario and is fully deterministic — two consecutive runs with unchanged inputs produce byte-identical `schedule_json`/`moic`/`irr`.
- [ ] `GET .../lbo/{case_type}/sensitivity` returns a grid of the requested size; monotonicity test passes (IRR increases with exit multiple at fixed entry multiple, and with lower entry multiple at fixed exit multiple).
- [ ] `apps/web` has minimal functional pages: a valuation/comps view (peer table incl. rejected-with-reasons, median multiples, entry EV) and an LBO view (Sources & Uses, key outputs, value creation bridge, sensitivity grid) — no styling polish required.
- [ ] No AI/LLM imports anywhere in this phase's code — same grep-able guarantee as Phase 0 (`apps/api`, `packages/finance_engine`).
- [ ] `README.md` walkthrough extended: after Phase 0's ingest, ingest 2–3 more real public companies as peer candidates, then run `/peers/generate` -> `/valuation` -> `/scenarios/generate` -> `/lbo/{base,bull,bear}/run` -> `/lbo/base/sensitivity`, all against real data, fully reproducible from a fresh clone.

---

## 9. Explicitly deferred (not this phase)

`Transaction`/precedent-transactions entity and its own comps cross-check; `Memo`/IC-memo generator; any AI/LLM functionality (document parsing, IC agents, synthesis); multi-tranche debt / debt sculpting (single blended tranche only, per §4); full tornado sensitivity across growth/margin/leverage/interest-rate (entry×exit multiple grid only, per §6); granular AR/AP/inventory ingestion for a precise NWC diagnostic (flat-percentage simplification per §4.3 stands until then); automated peer/market screening beyond "companies already ingested" (§2.1); auth; cloud deployment; UI polish. All per spec slide 20's MVP/v1.0 split and slide 17's phased roadmap.

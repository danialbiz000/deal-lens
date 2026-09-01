-- DealLens -- canonical DDL reference (Phase 0 + Phase 2).
--
-- This is the Postgres-portable source of truth for every table the app
-- needs: Phase 0's companies/financial_periods/assumptions
-- (docs/phase0-vertical-slice-design.md section 2) plus Phase 2's market
-- columns on companies and its peers/scenarios/lbo_cases tables
-- (docs/phase2-comps-lbo-design.md section 1). Written in Postgres dialect
-- since that is the eventual production target.
--
-- Local dev does NOT execute this file directly: apps/api/app/db.py calls
-- SQLAlchemy's Base.metadata.create_all() against a SQLite file on
-- startup, using the ORM models in apps/api/app/models/ as the live
-- source. This file exists so the schema can be inspected/reviewed/ported
-- to a real Postgres instance without reverse-engineering it from ORM code,
-- and the two are expected to be kept in agreement by hand (no migrations
-- tool in this slice -- alembic was called out as optional and unneeded
-- for a single SQLite dev file).
--
-- Portability rules applied throughout (see design doc section 2):
--   * Primary keys are String(36) UUIDs generated in application code
--     (uuid4()), not DB-native UUID or autoincrement -- identical on
--     SQLite and Postgres.
--   * Money/ratio fields are NUMERIC, never FLOAT/REAL, to avoid binary
--     rounding drift in financial figures.
--   * Timestamps are UTC.

CREATE TABLE companies (
    id                    VARCHAR(36)   PRIMARY KEY,
    ticker                VARCHAR(16)   NOT NULL UNIQUE,
    cik                   VARCHAR(10)   UNIQUE,
    name                  VARCHAR(255)  NOT NULL,
    sector                VARCHAR(100),
    industry              VARCHAR(100),
    country               VARCHAR(2),
    reporting_currency    VARCHAR(3)    NOT NULL DEFAULT 'USD',
    description           TEXT,

    -- Phase 2 additions: latest known market snapshot, refreshed on every
    -- /ingest call. Not a price-history entity -- this is deal screening,
    -- not a trading terminal (design doc section 1.1).
    market_cap            NUMERIC(20, 2),
    share_price           NUMERIC(12, 4),
    market_data_as_of     DATE,
    market_data_source    VARCHAR(20),  -- e.g. FMP

    created_at            TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE financial_periods (
    id                     VARCHAR(36)   PRIMARY KEY,
    company_id             VARCHAR(36)   NOT NULL REFERENCES companies(id),
    fiscal_year            INTEGER       NOT NULL,
    period_end_date        DATE          NOT NULL,
    period_type            VARCHAR(4)    NOT NULL,   -- FY | Q1..Q4 | TTM
    currency               VARCHAR(3)    NOT NULL,   -- as-reported, pre-normalization
    source                 VARCHAR(20)   NOT NULL,   -- SEC_EDGAR | ALPHA_VANTAGE | FMP | MANUAL
    source_ref             VARCHAR(255),             -- e.g. EDGAR accession number / API request id
    revenue                NUMERIC(20, 2),
    gross_profit           NUMERIC(20, 2),
    ebitda                 NUMERIC(20, 2),
    ebit                   NUMERIC(20, 2),
    net_income             NUMERIC(20, 2),
    operating_cash_flow    NUMERIC(20, 2),
    capex                  NUMERIC(20, 2),           -- stored as a positive magnitude (outflow)
    total_debt             NUMERIC(20, 2),
    cash_and_equivalents   NUMERIC(20, 2),
    interest_expense       NUMERIC(20, 2),
    shares_outstanding     NUMERIC(20, 2),
    is_estimate            BOOLEAN       NOT NULL DEFAULT FALSE,
    raw_payload            JSONB,                    -- verbatim snapshot of the source API response
    ingested_at            TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_financial_period_identity
        UNIQUE (company_id, period_end_date, period_type, source)
    -- Deliberately allows the SAME period from TWO different sources (e.g.
    -- SEC_EDGAR and FMP both reporting FY2023) so provenance conflicts stay
    -- visible instead of being silently overwritten. The screening engine
    -- always prefers SEC_EDGAR when both exist for the same fiscal year.
);

CREATE INDEX ix_financial_periods_company_id ON financial_periods (company_id);

-- Deliberately NOT stored as columns: net_debt, free_cash_flow,
-- net_working_capital. These are always derived by packages/finance_engine
-- from the raw fields above (net_debt = total_debt - cash_and_equivalents;
-- FCF = operating_cash_flow - capex) so there is exactly one place the
-- formula lives and no risk of a stored derived value silently drifting
-- from its inputs.

CREATE TABLE assumptions (
    id              VARCHAR(36)    PRIMARY KEY,
    company_id      VARCHAR(36)    NOT NULL REFERENCES companies(id),
    name            VARCHAR(100)   NOT NULL,   -- e.g. business_quality_score
    value_numeric   NUMERIC(10, 4),
    value_text      VARCHAR(500),              -- numeric/text mutually exclusive by convention
    unit            VARCHAR(30),               -- e.g. score_0_100, percent, x
    source          VARCHAR(100)   NOT NULL,   -- e.g. manual:analyst, default:neutral
    confidence      NUMERIC(3, 2),             -- 0.00-1.00
    notes           TEXT,
    created_at      TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_assumption_company_name UNIQUE (company_id, name)
    -- The API upserts by name, so there is always exactly one live value
    -- per assumption key per company; updated_at is the audit trail.
    -- Full override history/versioning is a v1.0 concern (design doc
    -- section 2.3), out of scope here.
);

CREATE INDEX ix_assumptions_company_id ON assumptions (company_id);

-- =====================================================================
-- Phase 2: comps + LBO underwriting (docs/phase2-comps-lbo-design.md)
-- =====================================================================

-- A relationship row between a target Company and a peer Company -- NOT a
-- separate identity entity (design doc section 1.2). Every peer is a full
-- row in `companies`, ingested through the same EDGAR/FMP pipeline as any
-- target.
CREATE TABLE peers (
    id                     VARCHAR(36)   PRIMARY KEY,
    target_company_id      VARCHAR(36)   NOT NULL REFERENCES companies(id),
    peer_company_id        VARCHAR(36)   NOT NULL REFERENCES companies(id),
    status                 VARCHAR(10)   NOT NULL,   -- CANDIDATE | SELECTED | REJECTED
    reason_code            VARCHAR(40),              -- e.g. MISSING_FINANCIALS, REVENUE_SCALE_MISMATCH
    reason_notes           TEXT,                     -- required when an analyst manually overrides status
    similarity_score       NUMERIC(5, 2),            -- 0-100, null if hard-filtered out before scoring
    ev_revenue_multiple    NUMERIC(10, 4),           -- snapshot at last computation
    ev_ebitda_multiple     NUMERIC(10, 4),
    source                 VARCHAR(30)   NOT NULL,   -- auto:top_k_similarity | manual:analyst
    computed_at            TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at             TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_peer_target_candidate UNIQUE (target_company_id, peer_company_id)
    -- One relationship row per pair, upserted on regeneration. REJECTED
    -- peers stay visible (never deleted) so "peer selection is never
    -- silently accepted" holds for rejections too, not just selections.
);

CREATE INDEX ix_peers_target_company_id ON peers (target_company_id);
CREATE INDEX ix_peers_peer_company_id ON peers (peer_company_id);

CREATE TABLE scenarios (
    id                      VARCHAR(36)   PRIMARY KEY,
    company_id              VARCHAR(36)   NOT NULL REFERENCES companies(id),
    case_type               VARCHAR(4)    NOT NULL,   -- BASE | BULL | BEAR
    revenue_growth_rate     NUMERIC(6, 4) NOT NULL,   -- annual, flat across the hold period
    ebitda_margin_delta     NUMERIC(6, 4) NOT NULL,   -- additive vs. entry-year margin, ramped linearly
    exit_multiple_delta     NUMERIC(6, 4) NOT NULL,   -- additive vs. entry multiple
    source                  VARCHAR(30)   NOT NULL,   -- default:spec_calibration | manual:analyst
    notes                   TEXT,
    created_at              TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_scenario_company_case_type UNIQUE (company_id, case_type)
    -- Exactly one of each case per company, upserted -- same pattern as
    -- the `assumptions` table above.
);

CREATE INDEX ix_scenarios_company_id ON scenarios (company_id);

-- A computed-artifact snapshot, not a wide flat table of every input
-- (design doc section 1.4): full inputs and the year-by-year schedule live
-- in JSON columns so the whole waterfall is inspectable without
-- recomputation, while key outputs get real columns for querying/sorting.
CREATE TABLE lbo_cases (
    id                          VARCHAR(36)    PRIMARY KEY,
    company_id                  VARCHAR(36)    NOT NULL REFERENCES companies(id),
    scenario_id                 VARCHAR(36)    NOT NULL REFERENCES scenarios(id),
    formula_version             VARCHAR(20)    NOT NULL,   -- lbo_v0.1
    inputs_json                 JSONB          NOT NULL,   -- resolved snapshot of every input used
    sources_uses_json           JSONB          NOT NULL,
    schedule_json                JSONB          NOT NULL,   -- year-by-year array
    value_creation_bridge_json  JSONB          NOT NULL,
    entry_ev                    NUMERIC(20, 2) NOT NULL,
    exit_ev                     NUMERIC(20, 2) NOT NULL,
    exit_equity_value           NUMERIC(20, 2) NOT NULL,
    moic                        NUMERIC(10, 4) NOT NULL,
    irr                         NUMERIC(10, 4) NOT NULL,
    entry_leverage               NUMERIC(6, 2)  NOT NULL,   -- new_debt / entry_ebitda
    exit_leverage                NUMERIC(6, 2)  NOT NULL,   -- ending_debt / exit_ebitda
    computed_at                  TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at                   TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                   TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_lbo_case_company_scenario UNIQUE (company_id, scenario_id)
    -- One live LBO case per company+scenario, upserted on re-run -- same
    -- "same inputs -> same outputs, no history yet" pattern as Phase 0.
    -- Full run history/versioning is a v1.0 concern.
);

CREATE INDEX ix_lbo_cases_company_id ON lbo_cases (company_id);
CREATE INDEX ix_lbo_cases_scenario_id ON lbo_cases (scenario_id);

-- Phase 2's LBO capital-structure/operating-simplification inputs
-- (lbo_leverage_multiple, lbo_interest_rate, lbo_cash_sweep_pct,
-- lbo_mandatory_amort_pct, lbo_tax_rate, lbo_capex_pct_revenue,
-- lbo_nwc_pct_revenue_change, lbo_transaction_fees_pct,
-- lbo_hold_period_years) reuse the existing `assumptions` table above --
-- no schema change needed for those (design doc section 1.5).

-- =====================================================================
-- Phase 4: AI layer -- memo writer + IC simulator
-- (docs/phase4-ai-layer-design.md)
-- =====================================================================

-- Both memos and ic_simulations are APPEND-ONLY and versioned -- a
-- deliberate departure from Phase 0/2's upsert-in-place pattern
-- (assumptions/peers/scenarios/lbo_cases all have one live row per key).
-- The spec wants memo/IC reproducibility across regenerations, not just
-- current state (design doc section 6): regenerating creates a new row
-- with version = max(existing) + 1; old versions remain fetchable.

CREATE TABLE memos (
    id                          VARCHAR(36)    PRIMARY KEY,
    company_id                  VARCHAR(36)    NOT NULL REFERENCES companies(id),
    version                     INTEGER        NOT NULL,
    prompt_version              VARCHAR(20)    NOT NULL,   -- e.g. memo_prompt_v0.1
    model                       VARCHAR(50)    NOT NULL,   -- resolved model id actually used
    source_bundle_json          JSONB          NOT NULL,   -- snapshot per design doc section 3
    sections_json               JSONB          NOT NULL,   -- array of {section_key, title, content}, the 10 sections
    validation_report_json      JSONB          NOT NULL,   -- citation_validation output, aggregated across sections
    generated_at                TIMESTAMP      NOT NULL,
    created_at                  TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_memo_company_version UNIQUE (company_id, version)
);

CREATE INDEX ix_memos_company_id ON memos (company_id);

CREATE TABLE ic_simulations (
    id                          VARCHAR(36)    PRIMARY KEY,
    company_id                  VARCHAR(36)    NOT NULL REFERENCES companies(id),
    version                     INTEGER        NOT NULL,
    model                       VARCHAR(50)    NOT NULL,
    source_bundle_json          JSONB          NOT NULL,
    transcript_json             JSONB          NOT NULL,   -- ordered 5-role array, each with its own validation_report
    llm_recommendation          VARCHAR(15)    NOT NULL,   -- raw IC Chair output, pre-override
    recommendation              VARCHAR(15)    NOT NULL,   -- final, possibly-overridden value
    override_fired              BOOLEAN        NOT NULL DEFAULT FALSE,
    override_reason             TEXT,                      -- populated iff override_fired
    key_strengths_json          JSONB          NOT NULL,
    key_risks_json              JSONB          NOT NULL,
    unanswered_dd_json          JSONB          NOT NULL,
    generated_at                TIMESTAMP      NOT NULL,
    created_at                  TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_ic_simulation_company_version UNIQUE (company_id, version)
    -- override_fired=true means the deterministic bear-case gate
    -- (finance_engine.ic_gate) forced the recommendation to HOLD despite
    -- the LLM saying PROCEED_TO_DD -- llm_recommendation always preserves
    -- what the model actually said, so the override is auditable, never
    -- silent.
);

CREATE INDEX ix_ic_simulations_company_id ON ic_simulations (company_id);

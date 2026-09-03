"""Versioned normalization anchors and weights for the screening score.

Named constants only, per design doc section 3.2 -- no magic numbers inline
in factors.py/screening.py, so the calibration can be inspected, unit-tested,
and tuned independently of the scoring logic itself.

Bumping FORMULA_VERSION is mandatory whenever any constant below changes,
since the API always reports `formula_version` alongside a score so a score
is always traceable to the exact calibration that produced it (design doc
section 3, since there is no persisted Scenario/versioning entity yet).
"""

FORMULA_VERSION = "v0.1"

# --- Factor weights (must sum to 1.0 -- enforced by a unit test) ---
WEIGHTS = {
    "business_quality": 0.20,
    "growth": 0.15,
    "margins": 0.15,
    "cash_conversion": 0.15,
    "leverage_capacity": 0.10,
    "market_structure": 0.10,
    "exit_optionality": 0.10,
    "management_execution": 0.05,
}

# The 4 factors computed purely from FinancialPeriod data.
COMPUTABLE_FACTOR_NAMES = ("growth", "margins", "cash_conversion", "leverage_capacity")

# The 4 factors that only ever come from an Assumption row (or the neutral
# default below) -- see design doc section 3.3. Maps factor name -> the
# Assumption.name key an analyst writes to override it.
PLACEHOLDER_FACTOR_NAMES = {
    "business_quality": "business_quality_score",
    "market_structure": "market_structure_score",
    "exit_optionality": "exit_optionality_score",
    "management_execution": "management_execution_score",
}

NEUTRAL_DEFAULT_SCORE = 50.0

# Assumption *_score values must fall in this range (validated at the API
# boundary too, but re-asserted here since finance_engine must stay safe to
# call standalone).
ASSUMPTION_SCORE_MIN = 0.0
ASSUMPTION_SCORE_MAX = 100.0

# --- Growth: revenue CAGR normalization anchors ---
# -10% CAGR -> 0 pts | 0% -> 25 pts | 10% -> 50 pts | 30%+ -> 100 pts
GROWTH_CAGR_FLOOR = -0.10
GROWTH_CAGR_CEILING = 0.30
GROWTH_MIN_FY_PERIODS = 2

# --- Margins: average EBITDA margin normalization anchor ---
# 0% margin -> 0 pts | 20% -> 50 pts | 40%+ -> 100 pts
MARGIN_CEILING = 0.40

# --- Cash conversion: average FCF/EBITDA normalization ---
# 0% or negative -> 0 pts | 50% -> 50 pts | 100%+ -> 100 pts
CASH_CONVERSION_CEILING = 1.00

# --- Leverage capacity: two 50/50-blended sub-scores, latest FY only ---
# 0x net debt/EBITDA -> 100 pts | 6x+ -> 0 pts
LEVERAGE_RATIO_CEILING = 6.0
# 1x interest coverage -> 0 pts | 10x+ -> 100 pts
INTEREST_COVERAGE_FLOOR = 1.0
INTEREST_COVERAGE_CEILING = 10.0

# How many of the most recent FY periods feed the computable factors.
MAX_FY_PERIODS_USED = 3

# Source preferred when the same fiscal_year exists from >1 source
# (design doc section 2.2's Tier-1-source-first rule).
PREFERRED_SOURCE = "SEC_EDGAR"

# =====================================================================
# Phase 2: comps engine (docs/phase2-comps-lbo-design.md section 2)
# =====================================================================

COMPS_SECTOR_MATCH_POINTS = 50.0
COMPS_INDUSTRY_MATCH_POINTS = 20.0
COMPS_SCALE_MAX_POINTS = 15.0
COMPS_MARGIN_MAX_POINTS = 15.0
COMPS_MARGIN_GAP_CEILING = 0.20  # 20+ pt margin gap -> 0 scale points

# Revenue-scale hard filter: peer revenue must be within [1/3x, 3x] of target.
COMPS_REVENUE_SCALE_MISMATCH_MIN_RATIO = 1.0 / 3.0
COMPS_REVENUE_SCALE_MISMATCH_MAX_RATIO = 3.0

COMPS_TOP_K = 5
COMPS_MIN_SELECTED_SCORE = 50.0
COMPS_MIN_PEERS_FOR_VALUATION = 2

REASON_MISSING_FINANCIALS = "MISSING_FINANCIALS"
REASON_REVENUE_SCALE_MISMATCH = "REVENUE_SCALE_MISMATCH"
REASON_SELF = "SELF"

# =====================================================================
# Phase 2: scenario framework (design doc section 3)
# =====================================================================

BULL_GROWTH_DELTA = 0.05
BEAR_GROWTH_DELTA = -0.05
BEAR_GROWTH_RATE_FLOOR = -0.05  # the resulting BEAR growth rate itself is floored here

BULL_MARGIN_DELTA = 0.02
BEAR_MARGIN_DELTA = -0.02

BULL_EXIT_MULTIPLE_DELTA = 1.0
BEAR_EXIT_MULTIPLE_DELTA = -2.0  # spec-literal value (spec slide 12)

# =====================================================================
# Phase 2: LBO engine (design doc section 4) -- default capital-structure
# / operating-simplification assumptions. These are the Assumption-table
# defaults (docs/phase2-comps-lbo-design.md section 1.5); the API layer
# passes an analyst override through unchanged when one exists.
# =====================================================================

LBO_FORMULA_VERSION = "lbo_v0.1"

LBO_DEFAULT_LEVERAGE_MULTIPLE = 5.0
LBO_DEFAULT_INTEREST_RATE = 0.08
LBO_DEFAULT_CASH_SWEEP_PCT = 1.0
LBO_DEFAULT_MANDATORY_AMORT_PCT = 0.01
LBO_DEFAULT_TAX_RATE = 0.25
LBO_DEFAULT_CAPEX_PCT_REVENUE = 0.03
LBO_DEFAULT_NWC_PCT_REVENUE_CHANGE = 0.05
LBO_DEFAULT_TRANSACTION_FEES_PCT = 0.02
LBO_DEFAULT_HOLD_PERIOD_YEARS = 5

# Value-creation-bridge red-flag rule (design doc section 5).
EXIT_MULTIPLE_DEPENDENT_THRESHOLD = 0.50

# Sensitivity grid defaults (design doc section 6).
SENSITIVITY_DEFAULT_STEP = 1.0
SENSITIVITY_DEFAULT_SIZE = 4

# Full tornado sensitivity (v1.0, design doc section 11): default +/- swing
# applied around the base case for each of the spec's 6 variables. Each is
# on its own natural scale (a leverage "turn", a rate in absolute
# percentage points, a valuation multiple in "x"), not a uniform percentage
# -- a uniform relative swing would make a 5% growth rate swing by an
# implausibly tiny absolute amount while swinging a 12x entry multiple by
# an enormous one.
TORNADO_DEFAULT_DELTAS = {
    "revenue_growth_rate": 0.05,  # +/- 5 percentage points
    "ebitda_margin_delta": 0.03,  # +/- 3 percentage points of margin trajectory
    "entry_multiple": 1.0,  # +/- 1.0x
    "exit_multiple": 1.0,  # +/- 1.0x
    "leverage": 1.0,  # +/- 1.0 turn of EBITDA
    "interest_rate": 0.02,  # +/- 2 percentage points
}

TORNADO_VARIABLE_LABELS = {
    "revenue_growth_rate": "Revenue growth",
    "ebitda_margin_delta": "Margin expansion",
    "entry_multiple": "Entry multiple",
    "exit_multiple": "Exit multiple",
    "leverage": "Leverage",
    "interest_rate": "Interest rate",
}

# Floors preventing an aggressive delta from pushing a variable into an
# economically meaningless region (negative leverage, a sub-1x multiple).
# Growth and margin deltas are deliberately NOT floored -- negative growth
# and margin compression are valid, meaningful bear-case territory.
TORNADO_VARIABLE_FLOORS = {
    "entry_multiple": 0.5,
    "exit_multiple": 0.5,
    "leverage": 0.0,
    "interest_rate": 0.0,
}

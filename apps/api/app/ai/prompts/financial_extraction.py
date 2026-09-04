"""Extraction prompt + schema for turning an uploaded financial statement /
investor-relations PDF into candidate ManualFinancialPeriodCreate rows
(design doc section 8's own guidance: "Implement filing extraction with
source spans, confidence, and a human-review queue. Never write extracted
values directly into the financial model without validation.").

Mirrors memo_sections.py's structure: one shared SYSTEM_PROMPT + JSON_SCHEMA,
Python-side validation of the response shape (extraction.py), zero writes to
the database from this module -- the router only ever returns candidates,
and the existing POST /companies/{id}/financials endpoint is the one and
only path anything extracted here can reach a FinancialPeriod row, same as
a human typing the manual-entry form.
"""

PROMPT_VERSION = "financial_extraction_prompt_v0.1"

# Matches ManualFinancialPeriodCreate's numeric fields exactly (design doc's
# source-agnostic FinancialPeriod model) -- so a candidate can be handed
# straight to that endpoint's payload shape with no renaming.
NUMERIC_FIELD_KEYS = [
    "revenue",
    "gross_profit",
    "ebitda",
    "ebit",
    "net_income",
    "operating_cash_flow",
    "capex",
    "total_debt",
    "cash_and_equivalents",
    "interest_expense",
    "shares_outstanding",
]

VALID_PERIOD_TYPES = ["FY", "Q1", "Q2", "Q3", "Q4", "TTM"]

SYSTEM_PROMPT = (
    "You are extracting structured financial data from an uploaded document "
    "(a financial statement, annual/quarterly report, or investor-relations "
    "filing) for a private equity analyst. The document itself is your only "
    "source of fact -- do not invent, calculate, or estimate any figure that "
    "is not stated (or directly derivable by simple addition/subtraction of "
    "figures that ARE stated, e.g. gross profit from revenue minus cost of "
    "goods sold if both appear) in the document.\n\n"
    "Find every distinct reporting period presented (e.g. FY2023 and FY2024 "
    "columns in the same statement are two separate periods) and return one "
    "object per period. For each period, extract:\n"
    "- fiscal_year, period_end_date (best inferred calendar date, YYYY-MM-DD), "
    "period_type (one of FY, Q1, Q2, Q3, Q4, TTM), currency (the ISO 3-letter "
    "code the document actually reports in -- infer from a symbol or word if "
    "no code is printed, e.g. '$' with a US company means USD).\n"
    "- Each of these figures, in full units (if the document states "
    "'$ in thousands' or 'in millions', multiply accordingly before "
    "reporting): revenue, gross_profit, ebitda, ebit, net_income, "
    "operating_cash_flow, capex, total_debt, cash_and_equivalents, "
    "interest_expense, shares_outstanding. Use null for any figure the "
    "document does not state and that cannot be simply derived from figures "
    "it does state.\n"
    "- capex and total_debt must be reported as POSITIVE magnitudes "
    "regardless of how the document signs them (e.g. capex shown as a "
    "negative cash outflow of -3,000 must be extracted as 3000).\n\n"
    "For every non-null numeric field, also add one entry to that period's "
    "`citations` list -- {field: <the field's key>, quote: <a short verbatim "
    "quote, plus page number if the document shows one, e.g. \"p.3: 'Total "
    "net sales of $42.0 million'\">} -- so a human reviewer can verify the "
    "number in seconds without re-reading the whole document. If a value "
    "was derived rather than directly stated, say so in the quote (e.g. "
    "\"derived: revenue 42.0m minus COGS 30.0m, p.3-4\"). Never fabricate a "
    "citation for a value you did not actually find or derive, and never add "
    "a citation entry for a field you left null.\n\n"
    "Set `notes` to a brief, honest summary of anything a reviewer should "
    "double-check (ambiguous units, inconsistent totals, a figure you "
    "derived rather than read directly, periods you were unsure how to "
    "date) -- empty string if nothing stands out."
)

_PERIOD_PROPERTIES = {
    "fiscal_year": {"type": "integer"},
    "period_end_date": {"type": "string", "description": "YYYY-MM-DD"},
    "period_type": {"type": "string", "enum": VALID_PERIOD_TYPES},
    "currency": {"type": "string", "description": "ISO 4217 3-letter code"},
    **{key: {"type": ["number", "null"]} for key in NUMERIC_FIELD_KEYS},
    # A variable-length list of {field, quote} pairs, one per non-null
    # numeric field above -- NOT a fixed object with one (nullable) key per
    # field. Anthropic's structured-output schema caps the number of
    # nullable/union-typed parameters in a single schema at 16 (a real 400
    # from the live API, never caught by the fake test client); the 11
    # numeric fields above already use most of that budget, so citations
    # must not add another 11 nullable string fields on top.
    "citations": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "field": {"type": "string", "enum": NUMERIC_FIELD_KEYS},
                "quote": {"type": "string"},
            },
            "required": ["field", "quote"],
            "additionalProperties": False,
        },
    },
}

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "periods": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": _PERIOD_PROPERTIES,
                "required": list(_PERIOD_PROPERTIES.keys()),
                "additionalProperties": False,
            },
            # NOTE: as in memo_sections.JSON_SCHEMA, Anthropic's structured-
            # output schema only supports minItems/maxItems of 0 or 1 on
            # array types, so the "at least one period" contract is enforced
            # in Python instead (see extraction.py's _validate_periods).
        },
        "notes": {"type": "string"},
    },
    "required": ["periods", "notes"],
    "additionalProperties": False,
}

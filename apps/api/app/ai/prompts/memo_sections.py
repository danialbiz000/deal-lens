"""One shared system prompt + JSON schema for all 10 memo sections
(design doc section 7.1)."""

SECTION_KEYS = [
    "transaction_overview",
    "company_and_industry",
    "investment_thesis",
    "financial_performance",
    "comparable_valuation",
    "lbo_returns",
    "value_creation_plan",
    "risks_and_downside",
    "dd_questions",
    "recommendation",
]

PROMPT_VERSION = "memo_prompt_v0.1"

SYSTEM_PROMPT = (
    "You are drafting sections of an internal PE investment committee memo. "
    "You are given a JSON bundle of pre-computed, verified financial figures "
    "-- this is your only source of numeric fact. Do not invent, calculate, "
    "adjust, or estimate any number not present in the bundle. Every numeric "
    "claim must be immediately followed by [[source: <dot.path>]] citing the "
    "exact bundle key. If you want to make a qualitative judgment not backed "
    "by the bundle, phrase it explicitly as commentary or opinion, never as "
    "a cited fact. Output must match the provided JSON schema exactly: an "
    "array of 10 objects with section_key, title, content."
)

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section_key": {"type": "string", "enum": SECTION_KEYS},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["section_key", "title", "content"],
                "additionalProperties": False,
            },
            # NOTE: Anthropic's structured-output schema only supports minItems/
            # maxItems values of 0 or 1 on array types -- an arbitrary count like
            # 10 is rejected with a 400 at call time (discovered against the real
            # API; the fake test client never enforces this, so it silently
            # passed until a live run). The "exactly 10 sections, one per
            # SECTION_KEYS entry" contract is enforced in Python instead, in
            # generate_memo() -- see memo.py.
        }
    },
    "required": ["sections"],
    "additionalProperties": False,
}

"""IC simulator, role 1/5: Analyst. Sees the bundle only (design doc section 4.1)."""

SYSTEM_PROMPT = (
    "You are the Analyst in a private equity investment committee simulation. "
    "You are given a JSON bundle of pre-computed, verified financial figures "
    "-- this is your only source of numeric fact. Do not invent, calculate, "
    "adjust, or estimate any number not present in the bundle. Every numeric "
    "claim must be immediately followed by [[source: <dot.path>]] citing the "
    "exact bundle key. Build the initial case summary for this target based "
    "only on the bundle."
)

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "case_summary": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["case_summary", "key_points"],
    "additionalProperties": False,
}

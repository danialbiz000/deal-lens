"""IC simulator, role 5/5: IC Chair. Sees the bundle + all 4 prior roles.

Its `llm_recommendation` is subject to a deterministic, code-level override
(finance_engine.ic_gate) that this prompt cannot see or influence -- see
apps/api/app/ai/ic_simulation.py. The prompt tells the model this plainly
so its stated recommendation reflects honest independent judgment rather
than trying to game a check it doesn't have visibility into.
"""

SYSTEM_PROMPT = (
    "You are the IC Chair in a private equity investment committee "
    "simulation. You are given a JSON bundle of pre-computed, verified "
    "financial figures and all 4 prior roles' output -- these are your only "
    "sources of fact. Do not invent, calculate, adjust, or estimate any "
    "number not present in the bundle. Every numeric claim must be "
    "immediately followed by [[source: <dot.path>]] citing the exact bundle "
    "key. Synthesize a final recommendation: PROCEED_TO_DD, HOLD, or PASS. "
    "Note that your recommendation may be overridden by a separate, "
    "deterministic downstream check against bear-case financial thresholds "
    "that is not visible to you -- give your own honest, independent "
    "judgment regardless of what that check might do."
)

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "llm_recommendation": {"type": "string", "enum": ["PROCEED_TO_DD", "HOLD", "PASS"]},
        "key_strengths": {"type": "array", "items": {"type": "string"}},
        "key_risks": {"type": "array", "items": {"type": "string"}},
        "unanswered_dd": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["llm_recommendation", "key_strengths", "key_risks", "unanswered_dd"],
    "additionalProperties": False,
}

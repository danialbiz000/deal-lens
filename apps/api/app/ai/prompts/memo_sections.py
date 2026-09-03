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

PROMPT_VERSION = "memo_prompt_v0.3"

SYSTEM_PROMPT = (
    "You are drafting sections of an internal PE investment committee memo. "
    "You are given a JSON bundle of pre-computed, verified financial figures "
    "-- this is your only source of numeric fact. Do not invent, calculate, "
    "adjust, or estimate any number not present in the bundle. Every numeric "
    "claim must be immediately followed by [[source: <dot.path>]] citing the "
    "exact bundle key. If you want to make a qualitative judgment not backed "
    "by the bundle, phrase it explicitly as commentary or opinion, never as "
    "a cited fact. Output must match the provided JSON schema exactly: an "
    "array of 10 objects with section_key, title, content.\n\n"
    "Citation accuracy is checked automatically after you respond, path by "
    "path -- a number that doesn't exactly match the value stored at its own "
    "cited path is treated as a hard error, identical in severity to "
    "fabricating the number outright. Adjacency in your prose is not "
    "evidence of correctness: citing the right NEIGHBORING figure is just as "
    "wrong as citing no figure at all. Before writing each numeric claim, "
    "silently re-read the bundle at the exact path you are about to cite and "
    "confirm the number you are about to write is that path's value, not a "
    "value from a path near it.\n\n"
    "Two specific patterns have caused this exact mistake before, so give "
    "them extra care:\n"
    "1. MOIC and IRR are almost always stated together (e.g. 'a 2.8x MOIC and "
    "a 23% IRR'). These are two different bundle paths (e.g. lbo.base.moic "
    "and lbo.base.irr) with two different citations -- never let the IRR "
    "number end up tagged with the MOIC path or vice versa.\n"
    "2. When listing the value creation bridge components (entry equity, "
    "EBITDA growth, margin expansion, debt paydown, multiple expansion, "
    "transaction fees) or any other multi-line breakdown, each line has its "
    "own distinct bundle path. Write and cite one line completely -- number, "
    "then its own citation -- before moving to the next; do not draft all the "
    "numbers first and attach citations afterward, since that is exactly how "
    "a citation ends up shifted onto the wrong line.\n\n"
    "Two more patterns to watch for:\n"
    "3. Copy each bundle path EXACTLY as it appears -- character for "
    "character, including every underscore and word -- never shorten, "
    "paraphrase, or guess a path from memory. 'valuation.entry_equity_value' "
    "is not the same path as 'valuation.entry_equity', even though the "
    "second reads naturally; a citation to a path that doesn't exist is "
    "flagged exactly like citing the wrong value.\n"
    "4. Some bundle values are signed (e.g. a value-creation-bridge "
    "component that drags on returns is stored as a NEGATIVE number). Cite "
    "the number with its actual sign, e.g. '-0.03x' -- do not rephrase a "
    "negative value as a positive magnitude with directional wording like "
    "'reduces value by 0.03x', since the cited number must equal the "
    "bundle's literal signed value, not its absolute value."
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

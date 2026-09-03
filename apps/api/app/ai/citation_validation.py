"""Pure Python, no LLM: post-hoc citation + numeric-claim checking against
the source bundle (design doc section 5).

Every prompt (memo sections and all 5 IC roles) carries the same
instruction: any numeric claim must be immediately followed by an inline
tag `[[source: <dot.path>]]` referencing the exact key in the source bundle
where that number lives. This module never calls the model -- it is a
regex + dict-traversal check, fully unit-testable with synthetic inputs,
with no network dependency whatsoever.

Three categories (neither blocks generation or storage -- this is a
best-effort heuristic layered on top of the prompt instruction, not a hard
gate like ic_gate.py):
  - invalid_citations: the model cited a path that does not exist in the
    bundle at all -- a genuine hallucination-on-the-citation-mechanism-
    itself, surfaced as a hard warning signal.
  - mismatched_citations: the model cited a path that DOES exist, but the
    number sitting next to the citation tag doesn't match the value
    actually stored at that path (within reasonable rounding/formatting
    tolerance) -- also a hard warning signal. This is the fix for a real
    adversarial gap found in testing: checking "does this path exist" and
    "does this number appear somewhere in the bundle" independently, as an
    earlier version of this module did, lets a fabricated number paired
    with a real-but-unrelated citation pass completely clean (e.g. "MOIC
    is 999.0x [[source: screening.score]]" against screening.score=62.4).
    Now the number claimed by a specific citation is checked against that
    citation's own resolved value, not the bundle at large.
  - uncited_numbers: a standalone number with no nearby citation and no
    matching bundle value -- a soft heuristic (natural language has plenty
    of non-claim numbers like "5-year hold"), documented as an
    auditability aid, not a fact-checker.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

CITATION_PATTERN = re.compile(r"\[\[source:\s*([a-zA-Z0-9_.]+)\s*\]\]")

# Captures a leading '$', digits/commas/decimal, and an optional trailing
# unit -- a percent/multiple sign, or a common currency-scale word. Loose by
# design (see module docstring): this is a heuristic aid, not a parser for
# arbitrary natural-language quantities.
NUMERIC_TOKEN_PATTERN = re.compile(
    # Leading `(?<![A-Za-z])` excludes digits glued to a preceding letter --
    # e.g. the "1" in "Q1" or "FY2025" -- which are labels, not standalone
    # numeric claims. Found via a live memo generation: "(Q1: 20.43x
    # [[source: valuation.ev_ebitda.q1]], Q3: 22.88x [[source:
    # valuation.ev_ebitda.q3]])" -- both correctly cited -- had the bare "1"
    # in "Q1" match as its own token, land within the adjacency window of
    # the q1 citation (which the real "20.43x" also claims), and get flagged
    # as a mismatch before the correct token was even reached.
    r"(?<![A-Za-z])[-+]?\$?\d[\d,]*\.?\d*\s*(?:%|x|bn|billion|tn|trillion|mn|million)?",
    re.IGNORECASE,
)

# Order matters: checked via `endswith` in a loop that breaks on first hit,
# so a longer suffix that is itself a superstring of a shorter one (there
# are none currently, but keep this in mind when adding more) must come
# first. "trillion"/"tn" were missing entirely until a live memo generation
# on a mega-cap target (Alphabet, >$1tn enterprise value) surfaced it: the
# model correctly wrote "$3.25 trillion [[source: valuation.entry_ev]]" and
# the validator flagged it as mismatched because "trillion" parsed as scale
# 1.0 instead of 1e12 -- a false positive on a genuinely correct citation.
_SCALE_SUFFIXES = (
    ("trillion", 1e12),
    ("tn", 1e12),
    ("billion", 1e9),
    ("bn", 1e9),
    ("million", 1e6),
    ("mn", 1e6),
)

# How close (in characters) a numeric token must be to a citation tag to be
# considered "covered" by it for the loose uncited-number fallback check,
# without requiring the tag to sit at an exact fixed offset (prompts
# naturally vary in phrasing around the number).
CITATION_PROXIMITY_WINDOW = 40

# Tighter window used to decide whether a specific number is "claimed by" a
# specific citation tag for the mismatch check -- the prompt instruction
# asks for the tag to *immediately* follow the number, so this only needs
# to absorb minor punctuation/whitespace variance, not whole clauses.
CITATION_ADJACENCY_WINDOW = 20

# Tolerance for comparing a claimed number against a citation's actual
# bundle value -- generous enough to absorb normal rounding/formatting
# variance (e.g. a model writing "62%" for 0.624, or "12.4x" for
# 12.40000001) without flagging legitimate, correctly-cited claims.
_RELATIVE_TOLERANCE = 0.02
_ABSOLUTE_TOLERANCE = 0.05


@dataclass(frozen=True)
class ValidationReport:
    total_citations: int
    invalid_citations: List[str] = field(default_factory=list)
    mismatched_citations: List[str] = field(default_factory=list)
    uncited_numbers: List[str] = field(default_factory=list)
    status: str = "ok"  # "ok" | "warnings"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_citations": self.total_citations,
            "invalid_citations": list(self.invalid_citations),
            "mismatched_citations": list(self.mismatched_citations),
            "uncited_numbers": list(self.uncited_numbers),
            "status": self.status,
        }


def _resolve_path(bundle: Dict[str, Any], path: str) -> Any:
    """Dot-traversal into the bundle; returns None if any segment doesn't
    resolve (missing dict key, list index out of range, non-container
    encountered mid-path).
    """
    node: Any = bundle
    for part in path.split("."):
        if isinstance(node, dict):
            if part not in node:
                return None
            node = node[part]
        elif isinstance(node, list):
            if not part.isdigit():
                return None
            index = int(part)
            if index >= len(node):
                return None
            node = node[index]
        else:
            return None
    return node


def _flatten_numeric_strings(bundle: Any, out: List[str]) -> None:
    """Collect string representations of every numeric leaf in the bundle,
    at a couple of common roundings, for loose "does this number appear
    anywhere in the data" matching (used only by the fallback
    uncited-number check for numbers with no adjacent citation at all).
    """
    if isinstance(bundle, dict):
        for value in bundle.values():
            _flatten_numeric_strings(value, out)
    elif isinstance(bundle, list):
        for value in bundle:
            _flatten_numeric_strings(value, out)
    elif isinstance(bundle, bool):
        return  # bool is a subclass of int -- exclude explicitly
    elif isinstance(bundle, (int, float)):
        out.append(str(bundle))
        out.append(f"{bundle:.0f}")
        out.append(f"{bundle:.1f}")
        out.append(f"{bundle:.2f}")


def _parse_numeric_token(token: str) -> List[float]:
    """Parse a matched numeric token into candidate float interpretations.

    Returns multiple candidates for a percent token (e.g. "62%" -> [62.0,
    0.62]) since bundle fields store percentages inconsistently (a
    screening score is 0-100, an IRR is a 0-1 fraction) -- comparing against
    either interpretation is a deliberate, documented tolerance, not a bug.
    Returns an empty list if the token isn't parseable as a number at all.
    """
    raw = token.strip()
    if not raw:
        return []

    is_percent = raw.endswith("%")
    core = raw.rstrip("%")
    core = re.sub(r"[xX]\s*$", "", core).strip()
    core = core.lstrip("$").replace(",", "").strip()

    scale = 1.0
    lower_core = core.lower()
    for suffix, multiplier in _SCALE_SUFFIXES:
        if lower_core.endswith(suffix) and len(lower_core) > len(suffix):
            core = core[: -len(suffix)]
            scale = multiplier
            break

    core = core.strip()
    try:
        value = float(core) * scale
    except ValueError:
        return []

    candidates = [value]
    if is_percent:
        candidates.append(value / 100.0)
    return candidates


def _approximately_equal(a: float, b: float) -> bool:
    if b == 0:
        return abs(a) <= _ABSOLUTE_TOLERANCE
    return abs(a - b) <= max(_ABSOLUTE_TOLERANCE, _RELATIVE_TOLERANCE * abs(b))


def _nearest_citation_within(
    token_span: "tuple[int, int]", citation_matches: List["re.Match[str]"], window: int
) -> Optional["re.Match[str]"]:
    """The citation tag closest to a numeric token, on either side, within
    `window` characters -- or None if no citation tag is that close.
    """
    token_start, token_end = token_span
    nearest: Optional["re.Match[str]"] = None
    nearest_distance: Optional[int] = None

    for citation_match in citation_matches:
        c_start, c_end = citation_match.span()
        if token_end <= c_start:
            distance = c_start - token_end
        elif token_start >= c_end:
            distance = token_start - c_end
        else:
            continue  # overlapping -- shouldn't happen given the two patterns don't overlap

        if distance <= window and (nearest_distance is None or distance < nearest_distance):
            nearest_distance = distance
            nearest = citation_match

    return nearest


def validate_citations(text: str, bundle: Dict[str, Any]) -> ValidationReport:
    citation_matches = list(CITATION_PATTERN.finditer(text))
    citation_paths = [m.group(1) for m in citation_matches]

    invalid_citations: List[str] = []
    resolved_values: Dict[int, Any] = {}  # keyed by citation_matches index -- paths can repeat
    for i, citation_match in enumerate(citation_matches):
        value = _resolve_path(bundle, citation_match.group(1))
        if value is None:
            invalid_citations.append(citation_match.group(1))
        else:
            resolved_values[i] = value

    bundle_numeric_strings: List[str] = []
    _flatten_numeric_strings(bundle, bundle_numeric_strings)

    mismatched_citations: List[str] = []
    uncited_numbers: List[str] = []
    # A citation whose claimed number already mismatched -- avoid piling on
    # duplicate entries if more than one token in the text happens to sit
    # within the adjacency window of the same tag.
    flagged_citation_indices: set = set()

    for token_match in NUMERIC_TOKEN_PATTERN.finditer(text):
        token = token_match.group().strip()
        if not token or not any(ch.isdigit() for ch in token):
            continue

        span = token_match.span()
        nearest_citation = _nearest_citation_within(span, citation_matches, CITATION_ADJACENCY_WINDOW)

        if nearest_citation is not None:
            citation_index = citation_matches.index(nearest_citation)
            bundle_value = resolved_values.get(citation_index)

            if bundle_value is None or isinstance(bundle_value, bool) or not isinstance(bundle_value, (int, float)):
                # Path invalid (already in invalid_citations) or resolves to
                # something that isn't a meaningful number to compare
                # against (string/list/dict/bool) -- nothing more to check.
                continue

            candidates = _parse_numeric_token(token)
            if candidates and not any(_approximately_equal(c, float(bundle_value)) for c in candidates):
                if citation_index not in flagged_citation_indices:
                    flagged_citation_indices.add(citation_index)
                    mismatched_citations.append(
                        f"{nearest_citation.group(1)}: text states '{token}', bundle value is {bundle_value}"
                    )
            continue  # this token is accounted for either way -- never falls through to uncited_numbers

        # No citation tag close enough to "claim" this token -- fall back to
        # the loose heuristic: is a citation loosely nearby, or does this
        # number appear anywhere in the bundle's own values at all?
        start, end = span
        window = text[max(0, start - CITATION_PROXIMITY_WINDOW) : min(len(text), end + CITATION_PROXIMITY_WINDOW)]
        if "[[source:" in window:
            continue

        normalized = token.replace(",", "").rstrip("%xX").strip()
        if any(normalized == bv or normalized in bv for bv in bundle_numeric_strings):
            continue

        uncited_numbers.append(token)

    status = "warnings" if (invalid_citations or mismatched_citations or uncited_numbers) else "ok"

    return ValidationReport(
        total_citations=len(citation_paths),
        invalid_citations=invalid_citations,
        mismatched_citations=mismatched_citations,
        uncited_numbers=uncited_numbers,
        status=status,
    )

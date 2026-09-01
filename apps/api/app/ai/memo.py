"""generate_memo(bundle, client) -> sections + validation report.

One structured call, ten fixed sections (design doc section 7.1) -- unlike
the IC simulator there is no "debate" structure to preserve, so this is
cheaper and simpler to test as a single schema-forced call.
"""

import json
from typing import Any, Dict

from app.ai.citation_validation import validate_citations
from app.ai.client import ClaudeClient
from app.ai.prompts import memo_sections


def _build_user_prompt(bundle: Dict[str, Any]) -> str:
    return (
        "Here is the source bundle -- the only facts you may cite:\n\n"
        f"{json.dumps(bundle, indent=2)}\n\n"
        "Generate the 10 memo sections now."
    )


def generate_memo(bundle: Dict[str, Any], client: ClaudeClient) -> Dict[str, Any]:
    result = client.complete_structured(
        system=memo_sections.SYSTEM_PROMPT,
        user=_build_user_prompt(bundle),
        json_schema=memo_sections.JSON_SCHEMA,
    )
    sections = result["sections"]

    per_section_reports = []
    for section in sections:
        report = validate_citations(section["content"], bundle)
        per_section_reports.append({"section_key": section["section_key"], **report.to_dict()})

    aggregated_validation_report = {
        "total_citations": sum(r["total_citations"] for r in per_section_reports),
        "invalid_citations": [c for r in per_section_reports for c in r["invalid_citations"]],
        "mismatched_citations": [c for r in per_section_reports for c in r["mismatched_citations"]],
        "uncited_numbers": [n for r in per_section_reports for n in r["uncited_numbers"]],
        "status": "warnings" if any(r["status"] == "warnings" for r in per_section_reports) else "ok",
        "per_section": per_section_reports,
    }

    return {"sections": sections, "validation_report": aggregated_validation_report}

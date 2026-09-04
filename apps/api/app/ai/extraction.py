"""extract_financials(pdf_base64, client) -> candidate periods + notes.

Mirrors memo.py's shape: one structured call, Python-side validation of the
response contract (JSON schema can't enforce "at least one period" -- see
the NOTE in financial_extraction.JSON_SCHEMA), zero database writes. The
router that calls this only ever returns candidates for human review; the
existing POST /companies/{id}/financials endpoint remains the sole path from
"a number" to "a trusted FinancialPeriod row", whether that number was typed
by an analyst or extracted here (design doc section 8: "Never write
extracted values directly into the financial model without validation").
"""

from typing import Any, Dict

from app.ai.client import ClaudeApiError, ClaudeClient
from app.ai.prompts import financial_extraction

_INSTRUCTION = (
    "Extract every reporting period's financial data from the attached document "
    "now, following the schema and rules exactly."
)


def _validate_periods(periods: Any) -> None:
    if not isinstance(periods, list):
        raise ClaudeApiError(f"Claude API: expected 'periods' to be a list, got {type(periods).__name__}")
    if len(periods) == 0:
        raise ClaudeApiError(
            "Claude API: extraction found no reporting periods in the document -- it may not be "
            "a financial statement, or the figures may be in a format this could not parse"
        )
    for period in periods:
        missing = [key for key in financial_extraction.NUMERIC_FIELD_KEYS if key not in period]
        if missing or "citations" not in period:
            raise ClaudeApiError(
                f"Claude API: extracted period is missing expected fields: {missing or ['citations']}"
            )


def _citations_list_to_dict(citations: Any) -> Dict[str, Any]:
    """Claude returns citations as a variable-length [{field, quote}, ...]
    list (see the NOTE in financial_extraction.JSON_SCHEMA -- a fixed object
    with one nullable key per numeric field would push the schema over
    Anthropic's union-type budget). The rest of the app (schema, router, UI)
    wants a simple {field: quote} lookup, so that conversion happens here,
    the one place both shapes are in scope.
    """
    result: Dict[str, Any] = {key: None for key in financial_extraction.NUMERIC_FIELD_KEYS}
    for entry in citations:
        field = entry.get("field")
        if field in result:
            result[field] = entry.get("quote")
    return result


def extract_financials(pdf_base64: str, client: ClaudeClient) -> Dict[str, Any]:
    result = client.complete_structured_from_document(
        system=financial_extraction.SYSTEM_PROMPT,
        user=_INSTRUCTION,
        json_schema=financial_extraction.JSON_SCHEMA,
        document_base64=pdf_base64,
        media_type="application/pdf",
    )
    periods = result["periods"]
    _validate_periods(periods)
    for period in periods:
        period["citations"] = _citations_list_to_dict(period["citations"])
    return {"periods": periods, "notes": result.get("notes", "")}

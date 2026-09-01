"""Pure normalization helpers for ingested financial-period dicts.

No I/O here -- this module only reshapes/validates dicts already fetched by
edgar_client/market_data_client, per design doc section 5:
  - currency left as-reported for MVP (no live FX; USD-only demo companies)
  - accounting periods mapped to canonical fiscal_year + period_end_date + period_type
  - units already plain currency units (not millions) from both EDGAR and FMP
  - signs made consistent (capex/debt always positive magnitude)
  - source_ref and raw_payload always preserved for audit

Being pure functions with no network/DB dependency, everything here is
directly unit-tested (apps/api/tests/test_ingestion_normalize.py).
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

REQUIRED_FIELDS = ("fiscal_year", "period_type", "source")

NUMERIC_FIELDS = (
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
)

POSITIVE_MAGNITUDE_FIELDS = ("capex", "total_debt")


def to_positive_magnitude(value: Optional[float]) -> Optional[float]:
    """Sign convention: capex and total_debt are always stored as a
    positive magnitude, regardless of how the source reported the sign.
    """
    if value is None:
        return None
    return abs(float(value))


def parse_period_end_date(value: Any) -> Optional[date]:
    """Accepts a date, a datetime, or an ISO 'YYYY-MM-DD' string; returns a
    `date` or None if unparsable/missing.
    """
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def normalize_period(raw: Dict[str, Any], currency: str = "USD") -> Dict[str, Any]:
    """Normalize one source-fetched period dict into the shape the
    `financial_periods` table / finance_engine expects.

    Raises ValueError if a required field is missing -- callers should
    catch this per-period and surface it as an ingest warning rather than
    failing the whole ingest.
    """
    missing = [f for f in REQUIRED_FIELDS if raw.get(f) in (None, "")]
    if missing:
        raise ValueError(f"missing required field(s) for normalization: {missing}")

    period_end_date = parse_period_end_date(raw.get("period_end_date"))
    if period_end_date is None:
        raise ValueError("missing or unparsable period_end_date")

    normalized: Dict[str, Any] = {
        "fiscal_year": int(raw["fiscal_year"]),
        "period_end_date": period_end_date,
        "period_type": raw["period_type"],
        "currency": raw.get("currency") or currency,
        "source": raw["source"],
        "source_ref": raw.get("source_ref"),
        "raw_payload": raw.get("raw_payload"),
        "is_estimate": bool(raw.get("is_estimate", False)),
    }

    for field in NUMERIC_FIELDS:
        value = raw.get(field)
        if field in POSITIVE_MAGNITUDE_FIELDS:
            normalized[field] = to_positive_magnitude(value)
        else:
            normalized[field] = float(value) if value is not None else None

    return normalized


def normalize_periods(raw_periods: List[Dict[str, Any]], currency: str = "USD") -> tuple[List[Dict[str, Any]], List[str]]:
    """Normalize a batch, collecting per-period failures as warnings instead
    of aborting the whole batch.
    """
    normalized: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for raw in raw_periods:
        try:
            normalized.append(normalize_period(raw, currency=currency))
        except ValueError as exc:
            fy = raw.get("fiscal_year", "unknown")
            source = raw.get("source", "unknown")
            warnings.append(f"{source}: skipped FY{fy} during normalization ({exc})")
    return normalized, warnings


def merge_period_sources(
    primary: Optional[Dict[str, Any]], supplementary: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Fill any null numeric field on `primary` (e.g. SEC_EDGAR) from
    `supplementary` (e.g. FMP), without overwriting a value primary already
    has. Both inputs must already be normalize_period() output for the same
    fiscal year. Returns a new dict; does not mutate inputs.

    This is used only to backfill a single stored row's fields for display
    convenience -- it does NOT collapse the two source rows into one DB row
    (the unique constraint is (company_id, period_end_date, period_type,
    source), so both source rows are always persisted separately for
    provenance, per design doc section 2.2).
    """
    if primary is None:
        if supplementary is None:
            raise ValueError("both primary and supplementary are None")
        return dict(supplementary)
    if supplementary is None:
        return dict(primary)

    merged = dict(primary)
    for field in NUMERIC_FIELDS:
        if merged.get(field) is None and supplementary.get(field) is not None:
            merged[field] = supplementary[field]
    return merged

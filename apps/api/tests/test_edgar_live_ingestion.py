"""Live-network variant: actually hits real SEC EDGAR for Apple (CIK
0000320193) and checks the ingestion pipeline parses genuine data into the
DB schema correctly.

This is deliberately separate from the mocked test_ingest_to_score_smoke.py
(which is what CI/offline runs should rely on): SEC EDGAR is a real
third-party dependency outside this repo's control, so a failure here should
never be confused with a regression in our own code. The test skips itself
(rather than failing the suite) if EDGAR is unreachable, per that same
reasoning -- but when it does run, it is the strongest possible check that
edgar_client.py's parsing logic (tag aliasing, per-fiscal-year fallback,
EBITDA reconstruction, sign normalization) actually works against the real
world, not just against hand-crafted fixtures.

Run explicitly with: pytest tests/test_edgar_live_ingestion.py -v
"""

import httpx
import pytest

from app.ingestion import edgar_client, normalize
from app.models.financial_period import FinancialPeriod

APPLE_CIK = "0000320193"
USER_AGENT = "DealLens Test Suite (test@example.com)"


def _fetch_live_or_skip():
    try:
        return edgar_client.fetch_company_facts(APPLE_CIK, USER_AGENT, timeout_seconds=15.0)
    except edgar_client.EdgarClientError as exc:
        pytest.skip(f"SEC EDGAR unreachable, skipping live ingestion test: {exc}")
    except httpx.HTTPError as exc:  # pragma: no cover - network-dependent
        pytest.skip(f"SEC EDGAR unreachable, skipping live ingestion test: {exc}")


def test_live_edgar_parses_apple_financials_into_db_schema(db_session):
    facts = _fetch_live_or_skip()

    periods = edgar_client.extract_annual_periods(facts)
    assert len(periods) >= 2, "expected at least 2 fiscal years of real Apple data"

    normalized, warnings = normalize.normalize_periods(periods, currency="USD")
    assert len(normalized) == len(periods), f"unexpected normalization failures: {warnings}"

    # Persist into the real ORM model / DB schema (in-memory sqlite via the
    # shared conftest db_session fixture) -- this is the literal "parses into
    # the DB schema" check: every field must round-trip through the actual
    # SQLAlchemy Numeric/Date/String columns without error.
    company_id = "live-test-company-id"
    saved = []
    for row in normalized:
        fp = FinancialPeriod(company_id=company_id, **row)
        db_session.add(fp)
        saved.append(fp)
    db_session.commit()

    for fp in saved:
        db_session.refresh(fp)
        assert fp.id is not None
        assert fp.source == "SEC_EDGAR"
        assert fp.source_ref is not None, f"missing source_ref for FY{fp.fiscal_year}"
        assert fp.raw_payload is not None, f"missing raw_payload for FY{fp.fiscal_year}"
        assert fp.period_type == "FY"

    # Sanity-check the actual numbers are plausible for Apple, not just
    # non-null -- catches unit/scale bugs (e.g. accidentally parsing
    # thousands/millions instead of raw dollars). EDGAR returns Apple's full
    # filing history back to ~2009, so the bound only applies to the most
    # recent 3 fiscal years (Apple's revenue has been > $200B every year
    # since FY2018) rather than every historical period -- FY2009 revenue
    # really was ~$36.5B, that's correct data, not a parsing bug.
    with_revenue = [fp for fp in saved if fp.revenue is not None]
    assert with_revenue, "expected at least one period with parsed revenue"
    recent_years = sorted({fp.fiscal_year for fp in with_revenue})[-3:]
    for fp in with_revenue:
        if fp.fiscal_year not in recent_years:
            continue
        assert float(fp.revenue) > 200_000_000_000, (
            f"FY{fp.fiscal_year} revenue {fp.revenue} implausible for recent Apple -- "
            "possible unit/scale parsing bug"
        )

    # The exact bug this slice already found and fixed once (per-tag vs
    # per-fiscal-year alias fallback): confirm revenue is populated for a
    # recent fiscal year that could only come from the newer XBRL tag.
    by_fy = {fp.fiscal_year: fp for fp in saved}
    recent_years = [y for y in by_fy if y >= 2023]
    for y in recent_years:
        assert by_fy[y].revenue is not None, (
            f"FY{y} revenue is null -- regression of the per-fiscal-year "
            "tag-alias fallback fix in edgar_client.py"
        )

from datetime import date

import pytest

from app.ingestion.normalize import (
    merge_period_sources,
    normalize_period,
    normalize_periods,
    parse_period_end_date,
    to_positive_magnitude,
)


def test_to_positive_magnitude():
    assert to_positive_magnitude(-50.0) == 50.0
    assert to_positive_magnitude(50.0) == 50.0
    assert to_positive_magnitude(None) is None


def test_parse_period_end_date_from_string():
    assert parse_period_end_date("2023-12-31") == date(2023, 12, 31)


def test_parse_period_end_date_unparsable_returns_none():
    assert parse_period_end_date("not-a-date") is None
    assert parse_period_end_date(None) is None


def test_normalize_period_happy_path():
    raw = {
        "fiscal_year": 2023,
        "period_end_date": "2023-12-31",
        "period_type": "FY",
        "source": "SEC_EDGAR",
        "revenue": 1000.0,
        "capex": -50.0,  # source reported as an outflow (negative)
        "total_debt": 300.0,
    }
    normalized = normalize_period(raw)
    assert normalized["fiscal_year"] == 2023
    assert normalized["period_end_date"] == date(2023, 12, 31)
    assert normalized["capex"] == 50.0  # sign flipped to positive magnitude
    assert normalized["total_debt"] == 300.0
    assert normalized["currency"] == "USD"  # default applied


def test_normalize_period_missing_required_field_raises():
    with pytest.raises(ValueError):
        normalize_period({"period_end_date": "2023-12-31", "period_type": "FY"})


def test_normalize_period_missing_period_end_date_raises():
    with pytest.raises(ValueError):
        normalize_period({"fiscal_year": 2023, "period_type": "FY", "source": "FMP"})


def test_normalize_periods_batch_collects_warnings_without_aborting():
    raw_periods = [
        {"fiscal_year": 2022, "period_end_date": "2022-12-31", "period_type": "FY", "source": "FMP", "revenue": 100},
        {"fiscal_year": 2023, "period_type": "FY", "source": "FMP"},  # missing period_end_date
    ]
    normalized, warnings = normalize_periods(raw_periods)
    assert len(normalized) == 1
    assert len(warnings) == 1
    assert "FY2023" in warnings[0]


def test_merge_period_sources_fills_gaps_without_overwriting():
    primary = normalize_period(
        {
            "fiscal_year": 2023,
            "period_end_date": "2023-12-31",
            "period_type": "FY",
            "source": "SEC_EDGAR",
            "revenue": 1000.0,
            "ebitda": None,
        }
    )
    supplementary = normalize_period(
        {
            "fiscal_year": 2023,
            "period_end_date": "2023-12-31",
            "period_type": "FY",
            "source": "FMP",
            "revenue": 999.0,  # primary already has revenue -- should NOT overwrite
            "ebitda": 200.0,
        }
    )
    merged = merge_period_sources(primary, supplementary)
    assert merged["revenue"] == 1000.0
    assert merged["ebitda"] == 200.0


def test_merge_period_sources_both_none_raises():
    with pytest.raises(ValueError):
        merge_period_sources(None, None)

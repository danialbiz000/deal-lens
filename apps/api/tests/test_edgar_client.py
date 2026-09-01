"""Regression test for the SEC EDGAR per-fiscal-year alias fallback.

Real-world bug this guards against: Apple tagged revenue as `Revenues`
through ~2018, then switched to `RevenueFromContractWithCustomerExcluding
AssessedTax`. A tag-level (rather than year-level) alias fallback silently
drops revenue for recent years for any filer that has migrated tags,
because the higher-priority alias *has* data -- just not for the years we
need. This was caught by testing ingestion against real Apple EDGAR data
during implementation.
"""

from app.ingestion.edgar_client import extract_annual_periods


def _entry(fy: int, end: str, val: float, form: str = "10-K", fp: str = "FY"):
    return {"fy": fy, "fp": fp, "form": form, "end": end, "val": val, "accn": f"acc-{fy}"}


def test_revenue_alias_fallback_is_per_fiscal_year_not_per_tag():
    facts = {
        "facts": {
            "us-gaap": {
                # Old tag: only has data for FY2017-2018 (retired afterward).
                "Revenues": {
                    "units": {
                        "USD": [
                            _entry(2017, "2017-09-30", 229_234_000_000),
                            _entry(2018, "2018-09-30", 265_595_000_000),
                        ]
                    }
                },
                # New tag: only used from FY2019 onward.
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            _entry(2019, "2019-09-30", 260_174_000_000),
                            _entry(2023, "2023-09-30", 383_285_000_000),
                        ]
                    }
                },
            }
        }
    }

    periods = {p["fiscal_year"]: p for p in extract_annual_periods(facts)}

    # The bug: FY2019 and FY2023 revenue would come back None if the
    # extractor stopped trying aliases after `Revenues` returned any data.
    assert periods[2017]["revenue"] == 229_234_000_000
    assert periods[2018]["revenue"] == 265_595_000_000
    assert periods[2019]["revenue"] == 260_174_000_000
    assert periods[2023]["revenue"] == 383_285_000_000


def test_extract_annual_periods_skips_non_10k_and_non_fy_entries():
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            _entry(2023, "2023-09-30", 383_285_000_000),
                            _entry(2023, "2023-06-30", 90_000_000_000, form="10-Q", fp="Q3"),
                        ]
                    }
                }
            }
        }
    }
    periods = {p["fiscal_year"]: p for p in extract_annual_periods(facts)}
    assert periods[2023]["revenue"] == 383_285_000_000


def test_extract_annual_periods_reconstructs_ebitda_from_operating_income_and_da():
    facts = {
        "facts": {
            "us-gaap": {
                "OperatingIncomeLoss": {"units": {"USD": [_entry(2023, "2023-12-31", 100_000_000)]}},
                "DepreciationDepletionAndAmortization": {
                    "units": {"USD": [_entry(2023, "2023-12-31", 20_000_000)]}
                },
            }
        }
    }
    periods = {p["fiscal_year"]: p for p in extract_annual_periods(facts)}
    assert periods[2023]["ebitda"] == 120_000_000
    assert periods[2023]["ebit"] == 100_000_000


def test_extract_annual_periods_reconstructs_da_from_split_tags_when_no_combined_tag():
    """Regression test: Microsoft (and many other filers) tag Depreciation
    and AmortizationOfIntangibleAssets as two separate concepts with no
    combined DepreciationDepletionAndAmortization tag at all -- caught by
    testing ingestion against real Microsoft EDGAR data. A naive combined-
    tag-only lookup silently produces a null EBITDA for every such filer.
    """
    facts = {
        "facts": {
            "us-gaap": {
                "OperatingIncomeLoss": {"units": {"USD": [_entry(2023, "2023-06-30", 100_000_000)]}},
                "Depreciation": {"units": {"USD": [_entry(2023, "2023-06-30", 15_000_000)]}},
                "AmortizationOfIntangibleAssets": {"units": {"USD": [_entry(2023, "2023-06-30", 5_000_000)]}},
            }
        }
    }
    periods = {p["fiscal_year"]: p for p in extract_annual_periods(facts)}
    assert periods[2023]["ebitda"] == 120_000_000  # 100M operating income + (15M + 5M) split D&A


def test_extract_annual_periods_prefers_combined_da_tag_when_present():
    facts = {
        "facts": {
            "us-gaap": {
                "OperatingIncomeLoss": {"units": {"USD": [_entry(2023, "2023-09-30", 100_000_000)]}},
                "DepreciationDepletionAndAmortization": {
                    "units": {"USD": [_entry(2023, "2023-09-30", 25_000_000)]}
                },
                # Split tags present too, but should be ignored since the combined tag covers this year.
                "Depreciation": {"units": {"USD": [_entry(2023, "2023-09-30", 999_000_000)]}},
            }
        }
    }
    periods = {p["fiscal_year"]: p for p in extract_annual_periods(facts)}
    assert periods[2023]["ebitda"] == 125_000_000  # uses the combined 25M, not 999M+


def test_extract_annual_periods_capex_is_positive_magnitude():
    facts = {
        "facts": {
            "us-gaap": {
                "PaymentsToAcquirePropertyPlantAndEquipment": {
                    "units": {"USD": [_entry(2023, "2023-12-31", -50_000_000)]}
                },
            }
        }
    }
    periods = {p["fiscal_year"]: p for p in extract_annual_periods(facts)}
    assert periods[2023]["capex"] == 50_000_000

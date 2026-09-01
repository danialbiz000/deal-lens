"""SEC EDGAR `companyfacts` client + XBRL-to-annual-period extraction.

Primary (Tier 1) data source per design doc section 5. Free, no API key,
but SEC requires a descriptive User-Agent header identifying the requester
-- requests without one get throttled/blocked.

Endpoint: https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json
"""

from typing import Any, Dict, List, Optional

import httpx

EDGAR_BASE_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# us-gaap XBRL tags we look for, in priority order per logical field.
# EDGAR filers tag concepts inconsistently across companies/years, so each
# field tries several tag aliases and takes the first that has data for a
# given fiscal year.
TAG_ALIASES: Dict[str, List[str]] = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
    ],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsForCapitalImprovements",
    ],
    "total_debt_lt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "total_debt_st": ["LongTermDebtCurrent", "ShortTermBorrowings"],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "interest_expense": ["InterestExpense", "InterestExpenseDebt", "InterestIncomeExpenseNet"],
    "shares_outstanding": [
        "CommonStockSharesOutstanding",
        "EntityCommonStockSharesOutstanding",
    ],
}


class EdgarClientError(RuntimeError):
    """Raised when EDGAR is unreachable or returns an unexpected response."""


def fetch_company_facts(cik: str, user_agent: str, timeout_seconds: float = 30.0) -> Dict[str, Any]:
    """Fetch the raw companyfacts JSON payload for a zero-padded CIK."""
    padded_cik = str(cik).zfill(10)
    url = EDGAR_BASE_URL.format(cik=padded_cik)
    headers = {"User-Agent": user_agent, "Accept": "application/json"}
    try:
        response = httpx.get(url, headers=headers, timeout=timeout_seconds)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise EdgarClientError(f"SEC_EDGAR: request to {url} failed: {exc}") from exc
    return response.json()


def _annual_values_by_fy(facts: Dict[str, Any], tag_names: List[str]) -> Dict[int, Dict[str, Any]]:
    """For a logical field with several candidate us-gaap tag aliases,
    return {fiscal_year: unit_entry} for full-year (10-K, fp="FY") entries.

    Aliases are tried in priority order, but the fallback is PER FISCAL
    YEAR, not per tag: filers commonly retire one tag for a newer one
    partway through their filing history (e.g. Apple tagged revenue as
    `Revenues` through ~2018 and `RevenueFromContractWithCustomerExcluding
    AssessedTax` afterward), so a tag can have real data yet still be
    missing the specific years we need. Trying the whole alias list, then
    stopping at the first with ANY data, silently drops recent years for
    companies that migrated tags -- so instead we let a later alias fill in
    any fiscal year the earlier, higher-priority aliases didn't cover.
    """
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    by_fy: Dict[int, Dict[str, Any]] = {}

    for tag in tag_names:
        concept = us_gaap.get(tag)
        if not concept:
            continue
        units = concept.get("units", {})
        entries = units.get("USD") or next(iter(units.values()), [])

        tag_by_fy: Dict[int, Dict[str, Any]] = {}
        for entry in entries:
            if entry.get("form") != "10-K":
                continue
            if entry.get("fp") not in (None, "FY"):
                continue
            fy = entry.get("fy")
            if fy is None:
                continue
            existing = tag_by_fy.get(fy)
            if existing is None or entry.get("end", "") >= existing.get("end", ""):
                tag_by_fy[fy] = entry

        for fy, entry in tag_by_fy.items():
            by_fy.setdefault(fy, entry)  # first (highest-priority) alias to cover a year wins

    return by_fy


# D&A alias handling needs its own logic beyond the simple per-field alias
# list above: some filers (Apple) tag a single combined concept; many
# others (Microsoft, and XBRL filers generally) tag depreciation and
# intangible amortization as two SEPARATE concepts with no combined tag at
# all. Trying only combined-tag aliases silently produces a null EBITDA for
# every filer in the second group -- caught by testing ingestion against
# real Microsoft/Alphabet EDGAR data during Phase 2 implementation.
DA_COMBINED_TAGS = [
    "DepreciationDepletionAndAmortization",
    "DepreciationAmortizationAndAccretionNet",
    "DepreciationAndAmortization",
]
DEPRECIATION_ONLY_TAGS = ["Depreciation"]
AMORTIZATION_ONLY_TAGS = ["AmortizationOfIntangibleAssets", "FiniteLivedIntangibleAssetsAmortizationExpense"]


def _depreciation_and_amortization_by_fy(facts: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    """{fiscal_year: entry} for total D&A, preferring a combined tag where
    a filer reports one, and falling back to Depreciation +
    AmortizationOfIntangibleAssets (summed) for fiscal years where only the
    split tags are available.
    """
    combined = _annual_values_by_fy(facts, DA_COMBINED_TAGS)
    depreciation = _annual_values_by_fy(facts, DEPRECIATION_ONLY_TAGS)
    amortization = _annual_values_by_fy(facts, AMORTIZATION_ONLY_TAGS)

    result: Dict[int, Dict[str, Any]] = {}
    for fy in set(combined) | set(depreciation) | set(amortization):
        if fy in combined:
            result[fy] = combined[fy]
            continue
        dep_entry = depreciation.get(fy)
        amort_entry = amortization.get(fy)
        if dep_entry is None and amort_entry is None:
            continue  # neither split tag has this year either -- genuinely no data
        synthesized = dict(dep_entry or amort_entry)
        synthesized["val"] = (dep_entry["val"] if dep_entry else 0) + (amort_entry["val"] if amort_entry else 0)
        result[fy] = synthesized

    return result


def extract_annual_periods(facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turn a raw companyfacts payload into a list of per-fiscal-year dicts
    with the normalized field names `normalize.py`/the API layer expects.

    EBITDA is reconstructed as operating_income + depreciation_amortization
    when both are available (EDGAR does not tag EBITDA directly) -- this is
    a best-effort MVP reconstruction, flagged via the period's `is_estimate`
    at the caller's discretion, not asserted as GAAP EBITDA.
    """
    field_series = {field: _annual_values_by_fy(facts, tags) for field, tags in TAG_ALIASES.items()}
    field_series["depreciation_amortization"] = _depreciation_and_amortization_by_fy(facts)

    all_years = set()
    for series in field_series.values():
        all_years.update(series.keys())

    periods: List[Dict[str, Any]] = []
    for fy in sorted(all_years):
        def val(field: str) -> Optional[float]:
            entry = field_series[field].get(fy)
            return float(entry["val"]) if entry else None

        operating_income = val("operating_income")
        depreciation = val("depreciation_amortization")
        ebitda: Optional[float]
        if operating_income is not None and depreciation is not None:
            ebitda = operating_income + depreciation
        else:
            ebitda = None

        lt_debt = val("total_debt_lt") or 0.0
        st_debt = val("total_debt_st") or 0.0
        total_debt = lt_debt + st_debt if (val("total_debt_lt") or val("total_debt_st")) else None

        capex_raw = val("capex")
        capex = abs(capex_raw) if capex_raw is not None else None  # positive magnitude convention

        # Prefer whichever field's entry has period end-date metadata for this fy.
        period_end_date = None
        for field in ("revenue", "net_income", "operating_income"):
            entry = field_series[field].get(fy)
            if entry:
                period_end_date = entry.get("end")
                break

        source_ref = None
        for field in ("revenue", "net_income", "operating_income"):
            entry = field_series[field].get(fy)
            if entry:
                source_ref = entry.get("accn")
                break

        periods.append(
            {
                "fiscal_year": fy,
                "period_end_date": period_end_date,
                "period_type": "FY",
                "source": "SEC_EDGAR",
                "source_ref": source_ref,
                "revenue": val("revenue"),
                "gross_profit": val("gross_profit"),
                "ebitda": ebitda,
                "ebit": operating_income,
                "net_income": val("net_income"),
                "operating_cash_flow": val("operating_cash_flow"),
                "capex": capex,
                "total_debt": total_debt,
                "cash_and_equivalents": val("cash"),
                "interest_expense": val("interest_expense"),
                "shares_outstanding": val("shares_outstanding"),
                "raw_payload": {
                    field: field_series[field].get(fy) for field in field_series if field_series[field].get(fy)
                },
            }
        )

    return periods

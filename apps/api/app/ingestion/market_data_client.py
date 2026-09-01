"""Financial Modeling Prep (FMP) client -- supplementary (Tier 2) source.

Chosen over Alpha Vantage per design doc section 5: FMP's free tier exposes
a single consistent income-statement / balance-sheet / cash-flow-statement
endpoint set per ticker with a higher free-tier request volume (250/day vs
Alpha Vantage's 25/day), which matters when iterating during development.
"""

from typing import Any, Dict, List, Optional

import httpx

FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"


class FmpClientError(RuntimeError):
    """Raised when FMP is unreachable, misconfigured, or returns an error payload."""


def _get(path: str, api_key: str, params: Dict[str, Any], timeout_seconds: float = 30.0) -> Any:
    if not api_key:
        raise FmpClientError("FMP: no API key configured (set FMP_API_KEY in .env)")
    url = f"{FMP_BASE_URL}/{path}"
    query = {**params, "apikey": api_key}
    try:
        response = httpx.get(url, params=query, timeout=timeout_seconds)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise FmpClientError(f"FMP: request to {url} failed: {exc}") from exc
    data = response.json()
    if isinstance(data, dict) and data.get("Error Message"):
        raise FmpClientError(f"FMP: {data['Error Message']}")
    return data


def fetch_income_statement(ticker: str, api_key: str, years_back: int = 3) -> List[Dict[str, Any]]:
    return _get(
        f"income-statement/{ticker}",
        api_key,
        {"period": "annual", "limit": years_back},
    )


def fetch_balance_sheet(ticker: str, api_key: str, years_back: int = 3) -> List[Dict[str, Any]]:
    return _get(
        f"balance-sheet-statement/{ticker}",
        api_key,
        {"period": "annual", "limit": years_back},
    )


def fetch_cash_flow(ticker: str, api_key: str, years_back: int = 3) -> List[Dict[str, Any]]:
    return _get(
        f"cash-flow-statement/{ticker}",
        api_key,
        {"period": "annual", "limit": years_back},
    )


def fetch_profile(ticker: str, api_key: str) -> List[Dict[str, Any]]:
    """FMP's company profile endpoint -- carries `mktCap` and `price`
    (Phase 2 design doc section 1.1's market snapshot on `companies`).
    """
    return _get(f"profile/{ticker}", api_key, {})


def extract_market_snapshot(profile_response: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Pull {market_cap, share_price} out of FMP's profile response.
    Returns None if the response is empty/unusable (e.g. an invalid
    ticker) rather than raising -- market data is a best-effort backfill,
    not something that should fail the whole ingest.
    """
    if not profile_response:
        return None
    profile = profile_response[0]
    market_cap = profile.get("mktCap")
    share_price = profile.get("price")
    if market_cap is None and share_price is None:
        return None
    return {
        "market_cap": float(market_cap) if market_cap is not None else None,
        "share_price": float(share_price) if share_price is not None else None,
    }


def extract_annual_periods(
    income_statements: List[Dict[str, Any]],
    balance_sheets: List[Dict[str, Any]],
    cash_flows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge FMP's 3 statement responses (joined by fiscal year, from
    `calendarYear`) into the same per-fiscal-year normalized dict shape
    `edgar_client.extract_annual_periods` produces.
    """
    by_year: Dict[int, Dict[str, Any]] = {}

    for stmt in income_statements:
        fy = int(stmt.get("calendarYear"))
        by_year.setdefault(fy, {"fiscal_year": fy, "raw_payload": {}})
        entry = by_year[fy]
        entry["period_end_date"] = stmt.get("date")
        entry["source_ref"] = stmt.get("link") or stmt.get("finalLink")
        entry["revenue"] = stmt.get("revenue")
        entry["gross_profit"] = stmt.get("grossProfit")
        entry["ebitda"] = stmt.get("ebitda")
        entry["ebit"] = stmt.get("operatingIncome")
        entry["net_income"] = stmt.get("netIncome")
        entry["interest_expense"] = stmt.get("interestExpense")
        entry["shares_outstanding"] = stmt.get("weightedAverageShsOut")
        entry["raw_payload"]["income_statement"] = stmt

    for stmt in balance_sheets:
        fy = int(stmt.get("calendarYear"))
        by_year.setdefault(fy, {"fiscal_year": fy, "raw_payload": {}})
        entry = by_year[fy]
        total_debt = stmt.get("totalDebt")
        if total_debt is None:
            lt = stmt.get("longTermDebt") or 0
            st = stmt.get("shortTermDebt") or 0
            total_debt = lt + st if (stmt.get("longTermDebt") or stmt.get("shortTermDebt")) else None
        entry["total_debt"] = total_debt
        entry["cash_and_equivalents"] = stmt.get("cashAndCashEquivalents")
        entry.setdefault("raw_payload", {})["balance_sheet"] = stmt

    for stmt in cash_flows:
        fy = int(stmt.get("calendarYear"))
        by_year.setdefault(fy, {"fiscal_year": fy, "raw_payload": {}})
        entry = by_year[fy]
        entry["operating_cash_flow"] = stmt.get("operatingCashFlow")
        capex = stmt.get("capitalExpenditure")
        entry["capex"] = abs(capex) if capex is not None else None  # positive magnitude convention
        entry.setdefault("raw_payload", {})["cash_flow"] = stmt

    periods = []
    for fy, entry in sorted(by_year.items()):
        entry.setdefault("period_type", "FY")
        entry.setdefault("source", "FMP")
        entry.setdefault("shares_outstanding", None)
        entry.setdefault("gross_profit", None)
        periods.append(entry)

    return periods

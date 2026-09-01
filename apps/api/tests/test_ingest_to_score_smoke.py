"""End-to-end smoke test for the vertical slice's core deliverable path:

    ticker -> POST /companies -> POST /ingest (SEC_EDGAR) -> GET /financials
           -> GET /screening-score

The SEC EDGAR HTTP call is mocked (monkeypatching `edgar_client.
fetch_company_facts`) rather than hitting the network, per the test plan's
preference for a reliable, deterministic ingestion test. The mocked payload
is shaped exactly like a real EDGAR `companyfacts` response (same tag names,
same per-fiscal-year `units.USD` entry structure) covering 3 fiscal years so
every computable factor (growth, margins, cash_conversion, leverage_capacity)
gets real, non-default input -- this is what actually exercises "does
ingestion parse a real company's shape of data into the DB schema correctly"
without depending on network availability in CI.

A separate, genuinely live-network variant of this same scenario (real HTTP
call to data.sec.gov for Apple) lives in test_edgar_live_ingestion.py.
"""

from app.ingestion import edgar_client


def _entry(fy: int, end: str, val: float, form: str = "10-K", fp: str = "FY", accn: str = None):
    return {
        "fy": fy,
        "fp": fp,
        "form": form,
        "end": end,
        "val": val,
        "accn": accn or f"0000320193-{fy}-000010",
    }


def _series(*entries):
    return {"units": {"USD": list(entries)}}


def _make_mock_companyfacts_payload():
    """A synthetic-but-realistic 3-year companyfacts payload, modeled on
    Apple's actual XBRL tagging, covering every field the finance engine's
    4 computable factors need.
    """
    years = [
        # fy, revenue, op_income, d&a, net_income, ocf, capex(neg), lt_debt, st_debt, cash, interest_exp, shares
        (2021, 365_817_000_000, 108_949_000_000, 11_284_000_000, 94_680_000_000,
         104_038_000_000, -11_085_000_000, 109_106_000_000, 9_613_000_000,
         34_940_000_000, 2_645_000_000, 16_426_786_000),
        (2022, 394_328_000_000, 119_437_000_000, 11_104_000_000, 99_803_000_000,
         122_151_000_000, -10_708_000_000, 98_959_000_000, 11_128_000_000,
         23_646_000_000, 2_931_000_000, 15_943_425_000),
        (2023, 383_285_000_000, 114_301_000_000, 11_519_000_000, 96_995_000_000,
         110_543_000_000, -10_959_000_000, 95_281_000_000, 5_985_000_000,
         29_965_000_000, 3_933_000_000, 15_550_061_000),
    ]

    def col(idx):
        return {fy: row[idx] for fy, *row in [(y[0], *y[1:]) for y in years]}

    revenue = col(0)
    op_income = col(1)
    da = col(2)
    net_income = col(3)
    ocf = col(4)
    capex = col(5)
    lt_debt = col(6)
    st_debt = col(7)
    cash = col(8)
    interest = col(9)
    shares = col(10)

    end_dates = {2021: "2021-09-25", 2022: "2022-09-24", 2023: "2023-09-30"}

    def build_series(values: dict):
        return _series(*[_entry(fy, end_dates[fy], v) for fy, v in values.items()])

    return {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": build_series(revenue),
                "OperatingIncomeLoss": build_series(op_income),
                "DepreciationDepletionAndAmortization": build_series(da),
                "NetIncomeLoss": build_series(net_income),
                "NetCashProvidedByUsedInOperatingActivities": build_series(ocf),
                "PaymentsToAcquirePropertyPlantAndEquipment": build_series(capex),
                "LongTermDebtNoncurrent": build_series(lt_debt),
                "LongTermDebtCurrent": build_series(st_debt),
                "CashAndCashEquivalentsAtCarryingValue": build_series(cash),
                "InterestExpense": build_series(interest),
                "CommonStockSharesOutstanding": build_series(shares),
            }
        }
    }


def test_ingest_then_screening_score_smoke(client, monkeypatch):
    """The slice's headline flow: give it a ticker, get a valid score back."""
    mock_payload = _make_mock_companyfacts_payload()
    monkeypatch.setattr(
        edgar_client, "fetch_company_facts", lambda cik, user_agent, timeout_seconds=30.0: mock_payload
    )

    create_resp = client.post(
        "/companies",
        json={"ticker": "aapl", "name": "Apple Inc.", "cik": "0000320193", "sector": "Technology"},
    )
    assert create_resp.status_code == 201
    company = create_resp.json()

    ingest_resp = client.post(
        f"/companies/{company['id']}/ingest",
        json={"years_back": 3, "sources": ["SEC_EDGAR"]},
    )
    assert ingest_resp.status_code == 200
    ingest_body = ingest_resp.json()
    assert ingest_body["ingested_periods"] == 3

    # DB-schema-level parsing checks: source/source_ref/raw_payload populated
    # on every ingested period, per design doc section 6's acceptance criteria.
    for period in ingest_body["periods"]:
        assert period["source"] == "SEC_EDGAR"
        assert period["source_ref"] is not None
        assert period["raw_payload"] is not None
        assert period["currency"] == "USD"

    by_year = {p["fiscal_year"]: p for p in ingest_body["periods"]}
    assert set(by_year.keys()) == {2021, 2022, 2023}
    assert by_year[2023]["revenue"] == 383_285_000_000
    assert by_year[2023]["ebitda"] == 114_301_000_000 + 11_519_000_000  # op_income + D&A
    assert by_year[2023]["capex"] == 10_959_000_000  # positive magnitude, sign flipped
    assert by_year[2023]["total_debt"] == 95_281_000_000 + 5_985_000_000

    financials_resp = client.get(f"/companies/{company['id']}/financials", params={"period_type": "FY"})
    assert financials_resp.status_code == 200
    assert len(financials_resp.json()) == 3

    # The headline deliverable: ticker in, valid score + full 8-factor
    # breakdown out.
    score_resp = client.get(f"/companies/{company['id']}/screening-score")
    assert score_resp.status_code == 200
    score_body = score_resp.json()

    assert score_body["formula_version"] == "v0.1"
    assert isinstance(score_body["score"], (int, float))
    assert 0 <= score_body["score"] <= 100
    assert len(score_body["factors"]) == 8

    by_name = {f["name"]: f for f in score_body["factors"]}
    expected_weights = {
        "business_quality": 0.20,
        "growth": 0.15,
        "margins": 0.15,
        "cash_conversion": 0.15,
        "leverage_capacity": 0.10,
        "market_structure": 0.10,
        "exit_optionality": 0.10,
        "management_execution": 0.05,
    }
    assert set(by_name.keys()) == set(expected_weights.keys())
    for name, weight in expected_weights.items():
        assert by_name[name]["weight"] == weight

    # 3 full FY periods with complete data -> all 4 computable factors should
    # actually compute (not fall back to default).
    for name in ("growth", "margins", "cash_conversion", "leverage_capacity"):
        assert by_name[name]["source"] == "computed", name
        assert by_name[name]["notes"]

    # No Assumption rows yet -> all 4 qualitative factors are neutral defaults.
    for name in ("business_quality", "market_structure", "exit_optionality", "management_execution"):
        assert by_name[name]["source"] == "default"
        assert by_name[name]["normalized_score"] == 50

    # Determinism: same inputs, same score on repeat.
    repeat_resp = client.get(f"/companies/{company['id']}/screening-score")
    assert repeat_resp.json()["score"] == score_body["score"]


def test_ingest_duplicate_ticker_still_conflicts_before_ingest(client, monkeypatch):
    """Sanity check that the smoke-test flow's 409 behavior (already covered
    in test_companies_api.py) isn't accidentally bypassed by ingest."""
    monkeypatch.setattr(
        edgar_client,
        "fetch_company_facts",
        lambda cik, user_agent, timeout_seconds=30.0: _make_mock_companyfacts_payload(),
    )
    client.post("/companies", json={"ticker": "AAPL", "name": "Apple Inc.", "cik": "0000320193"})
    dup = client.post("/companies", json={"ticker": "AAPL", "name": "Apple Inc. Dup"})
    assert dup.status_code == 409

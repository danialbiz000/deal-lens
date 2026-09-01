"""Live-network end-to-end smoke test for the Phase 2 comps + LBO pipeline,
independent verification of the coder's reported live run against real SEC
EDGAR data for AAPL/MSFT/GOOGL.

Ingests two real companies (Apple + Microsoft, both real 10-K filers with
different EBITDA-tagging conventions -- see the DA split-tag regression
tests in test_edgar_client.py) via real HTTP calls to data.sec.gov, sets a
plausible market_cap manually (no FMP_API_KEY in this sandbox, same
limitation the coder noted), then drives the full chain: peers/generate ->
valuation -> scenarios/generate -> lbo/base/run -> lbo/base/sensitivity --
exactly the flow a real analyst would use.

Deliberately asserts only *plausibility* bounds, not exact hardcoded
figures: real EDGAR data changes as new filings land (Apple/Microsoft file
new 10-Ks every year), so a value that's correct today would go stale and
fail for the wrong reason later. Skips itself if EDGAR is unreachable, same
policy as test_edgar_live_ingestion.py.
"""

import httpx
import pytest

from app.ingestion import edgar_client

AAPL_CIK = "0000320193"
MSFT_CIK = "0000789019"
USER_AGENT = "DealLens Test Suite (test@example.com)"


def _ingest_real_company(client, ticker, cik, market_cap):
    create = client.post(
        "/companies",
        json={"ticker": ticker, "name": f"{ticker} Inc.", "cik": cik, "sector": "Technology", "industry": "Hardware"},
    )
    assert create.status_code == 201, create.text
    company = create.json()

    try:
        ingest = client.post(
            f"/companies/{company['id']}/ingest", json={"years_back": 3, "sources": ["SEC_EDGAR"]}
        )
    except (httpx.HTTPError, edgar_client.EdgarClientError) as exc:  # pragma: no cover - network-dependent
        pytest.skip(f"SEC EDGAR unreachable, skipping live comps/LBO smoke test: {exc}")

    if ingest.status_code == 502:
        pytest.skip(f"SEC EDGAR unreachable ({ingest.json()}), skipping live comps/LBO smoke test")
    assert ingest.status_code == 200, ingest.text
    assert ingest.json()["ingested_periods"] >= 2, f"expected real FY data for {ticker}"

    return company


def test_live_comps_and_lbo_pipeline_against_real_edgar_data(client, db_session):
    from app.models.company import Company

    aapl = _ingest_real_company(client, "AAPL", AAPL_CIK, market_cap=3_000_000_000_000)
    msft = _ingest_real_company(client, "MSFT", MSFT_CIK, market_cap=3_000_000_000_000)

    # No FMP_API_KEY in this sandbox (same limitation the coder hit) -- set
    # market_cap directly, same workaround they used, so comps math has real
    # peer EV inputs without needing a live FMP call.
    for company, cap in ((aapl, 3_000_000_000_000.0), (msft, 3_000_000_000_000.0)):
        row = db_session.get(Company, company["id"])
        row.market_cap = cap
        db_session.commit()

    # --- peers/generate: Microsoft becomes a candidate/selected peer of Apple ---
    peers_resp = client.post(f"/companies/{aapl['id']}/peers/generate")
    assert peers_resp.status_code == 200, peers_resp.text
    peers_body = peers_resp.json()
    by_ticker = {p["peer_ticker"]: p for p in peers_body["peers"]}
    assert "MSFT" in by_ticker
    # Both are real, similarly-scaled megacap tech companies -- should pass
    # hard filters and score reasonably (not asserting an exact score since
    # real revenue/EBITDA figures drift with each new filing).
    assert by_ticker["MSFT"]["reason_code"] is None
    assert by_ticker["MSFT"]["similarity_score"] is not None
    assert 0 <= by_ticker["MSFT"]["similarity_score"] <= 100

    # --- valuation: only 1 peer selected (MSFT) is below the 2-peer minimum ---
    valuation_resp = client.get(f"/companies/{aapl['id']}/valuation")
    if by_ticker["MSFT"]["status"] != "SELECTED":
        pytest.skip("MSFT did not auto-select as a peer in this data snapshot; valuation step not exercised")
    assert valuation_resp.status_code == 422  # correctly enforces >= 2 selected peers, real data has only 1 here
    assert "selected peers" in valuation_resp.json()["detail"].lower()

    # --- scenarios/generate: real historical CAGR from real Apple filings ---
    scenarios_resp = client.post(f"/companies/{aapl['id']}/scenarios/generate")
    assert scenarios_resp.status_code == 200, scenarios_resp.text
    by_case = {s["case_type"]: s for s in scenarios_resp.json()["scenarios"]}
    # Apple's revenue has neither collapsed nor 10x'd over any real 3-year
    # window -- a plausibility band, not an exact figure.
    assert -0.20 <= by_case["BASE"]["revenue_growth_rate"] <= 0.40
    assert by_case["BEAR"]["exit_multiple_delta"] == pytest.approx(-2.0)  # spec-literal, data-independent

    # --- lbo/base/run: explicit entry_ev override since valuation needs 2+ peers ---
    lbo_resp = client.post(f"/companies/{aapl['id']}/lbo/base/run", json={"entry_ev": 2_500_000_000_000.0})
    assert lbo_resp.status_code == 200, lbo_resp.text
    lbo_body = lbo_resp.json()
    assert lbo_body["sources_uses"]["reconciles"] is True
    assert lbo_body["moic"] > 0
    assert lbo_body["value_creation_bridge"]["total"] == pytest.approx(lbo_body["moic"], abs=1e-6)

    # --- sensitivity: same real inputs, full grid ---
    sens_resp = client.get(f"/companies/{aapl['id']}/lbo/base/sensitivity", params={"step": 1.0, "size": 4})
    assert sens_resp.status_code == 200, sens_resp.text
    irr_grid = sens_resp.json()["irr_grid"]
    assert len(irr_grid) == 4 and all(len(row) == 4 for row in irr_grid)
    for row in irr_grid:
        for a, b in zip(row, row[1:]):
            assert b > a  # monotonic even against real-data-derived inputs

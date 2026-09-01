"""Coverage for two POST /companies/{id}/ingest branches that the vertical
slice smoke test (test_ingest_to_score_smoke.py) doesn't exercise:

  - SEC_EDGAR upstream failure -> 502 (edgar_client.EdgarClientError bubbles
    up as an HTTPException, unlike the FMP path which downgrades its client
    error to a warning).
  - No CIK on file -> SEC_EDGAR is skipped with a warning instead of being
    attempted, so ingest still succeeds (200) with zero periods from that
    source.

Flagged as a non-blocking coverage gap during Phase 0 vertical slice review.
"""

from app.ingestion import edgar_client


def _create_company(client, ticker="ACME", cik=None):
    payload = {"ticker": ticker, "name": "Acme Corp"}
    if cik is not None:
        payload["cik"] = cik
    return client.post("/companies", json=payload).json()


def test_ingest_returns_502_on_edgar_client_error(client, monkeypatch):
    def _raise(cik, user_agent, timeout_seconds=30.0):
        raise edgar_client.EdgarClientError("SEC_EDGAR: request to data.sec.gov failed: timed out")

    monkeypatch.setattr(edgar_client, "fetch_company_facts", _raise)

    company = _create_company(client, cik="0000320193")

    response = client.post(
        f"/companies/{company['id']}/ingest",
        json={"years_back": 3, "sources": ["SEC_EDGAR"]},
    )
    assert response.status_code == 502
    assert "SEC_EDGAR" in response.json()["detail"]


def test_ingest_skips_sec_edgar_with_warning_when_no_cik(client):
    company = _create_company(client)
    assert company["cik"] is None

    response = client.post(
        f"/companies/{company['id']}/ingest",
        json={"years_back": 3, "sources": ["SEC_EDGAR"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ingested_periods"] == 0
    assert "SEC_EDGAR: skipped, company has no CIK on file" in body["warnings"]

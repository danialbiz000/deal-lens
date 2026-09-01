from datetime import date

from app.models.company import Company
from app.models.financial_period import FinancialPeriod
from app.models.peer import Peer


def _create_company(client, ticker, sector="Tech", industry="Software", **kwargs):
    payload = {"ticker": ticker, "name": f"{ticker} Inc.", "sector": sector, "industry": industry, **kwargs}
    return client.post("/companies", json=payload).json()


def _set_market_and_financials(
    db_session, company_id, fiscal_year=2023, revenue=100.0, ebitda=20.0,
    market_cap=500.0, total_debt=50.0, cash=20.0,
):
    company = db_session.get(Company, company_id)
    company.market_cap = market_cap
    period = FinancialPeriod(
        company_id=company_id,
        fiscal_year=fiscal_year,
        period_end_date=date(fiscal_year, 12, 31),
        period_type="FY",
        currency="USD",
        source="SEC_EDGAR",
        revenue=revenue,
        ebitda=ebitda,
        total_debt=total_debt,
        cash_and_equivalents=cash,
    )
    db_session.add(period)
    db_session.commit()


# --- generate_peers guardrails ---


def test_generate_peers_requires_sector(client):
    company = _create_company(client, "NOSEC", sector=None)
    response = client.post(f"/companies/{company['id']}/peers/generate")
    assert response.status_code == 422


def test_generate_peers_requires_target_financials(client):
    company = _create_company(client, "TGT1")  # has sector, but no FinancialPeriod
    response = client.post(f"/companies/{company['id']}/peers/generate")
    assert response.status_code == 422


def test_generate_peers_404_when_company_missing(client):
    response = client.post("/companies/does-not-exist/peers/generate")
    assert response.status_code == 404


# --- hard filters + scoring ---


def test_generate_peers_hard_filters_and_scoring(client, db_session):
    target = _create_company(client, "TGT2", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, target["id"], revenue=100.0, ebitda=20.0)

    good_peer = _create_company(client, "GOODP", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, good_peer["id"], revenue=110.0, ebitda=22.0, market_cap=550.0)

    scale_mismatch_peer = _create_company(client, "BIGP", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, scale_mismatch_peer["id"], revenue=500.0, ebitda=100.0, market_cap=2000.0)

    no_financials_peer = _create_company(client, "EMPTYP", sector="Tech", industry="Software")
    # deliberately no _set_market_and_financials call -- no FY period, no market_cap

    response = client.post(f"/companies/{target['id']}/peers/generate")
    assert response.status_code == 200
    body = response.json()

    by_ticker = {}
    for peer in body["peers"]:
        by_ticker[peer["peer_ticker"]] = peer

    assert by_ticker["GOODP"]["status"] == "SELECTED"
    assert by_ticker["GOODP"]["similarity_score"] is not None
    assert by_ticker["BIGP"]["status"] == "REJECTED"
    assert by_ticker["BIGP"]["reason_code"] == "REVENUE_SCALE_MISMATCH"
    assert by_ticker["EMPTYP"]["status"] == "REJECTED"
    assert by_ticker["EMPTYP"]["reason_code"] == "MISSING_FINANCIALS"
    assert body["selected_count"] >= 1


def test_generate_peers_is_idempotent_and_preserves_manual_override(client, db_session):
    target = _create_company(client, "TGT3", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, target["id"], revenue=100.0, ebitda=20.0)
    peer = _create_company(client, "PEERX", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, peer["id"], revenue=105.0, ebitda=21.0, market_cap=520.0)

    first = client.post(f"/companies/{target['id']}/peers/generate").json()
    peer_row = next(p for p in first["peers"] if p["peer_ticker"] == "PEERX")
    assert peer_row["status"] == "SELECTED"

    # Analyst manually overrides to REJECTED with a reason.
    patch_response = client.patch(
        f"/companies/{target['id']}/peers/{peer_row['id']}",
        json={"status": "REJECTED", "reason_notes": "Too different a business model despite the numbers."},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["source"] == "manual:analyst"

    # Regenerating must not clobber the manual override.
    second = client.post(f"/companies/{target['id']}/peers/generate").json()
    peer_row_after = next(p for p in second["peers"] if p["peer_ticker"] == "PEERX")
    assert peer_row_after["status"] == "REJECTED"
    assert peer_row_after["source"] == "manual:analyst"
    assert peer_row_after["reason_notes"] is not None


def test_patch_peer_requires_reason_notes(client, db_session):
    target = _create_company(client, "TGT4", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, target["id"], revenue=100.0, ebitda=20.0)
    peer = _create_company(client, "PEERY", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, peer["id"], revenue=105.0, ebitda=21.0, market_cap=520.0)

    generated = client.post(f"/companies/{target['id']}/peers/generate").json()
    peer_row = generated["peers"][0]

    response = client.patch(
        f"/companies/{target['id']}/peers/{peer_row['id']}", json={"status": "SELECTED", "reason_notes": ""}
    )
    assert response.status_code == 422


def test_list_peers_filter_by_status(client, db_session):
    target = _create_company(client, "TGT5", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, target["id"], revenue=100.0, ebitda=20.0)
    good_peer = _create_company(client, "PEERZ", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, good_peer["id"], revenue=100.0, ebitda=20.0, market_cap=500.0)
    bad_peer = _create_company(client, "PEERBAD", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, bad_peer["id"], revenue=1000.0, ebitda=200.0, market_cap=5000.0)

    client.post(f"/companies/{target['id']}/peers/generate")

    selected = client.get(f"/companies/{target['id']}/peers", params={"status": "SELECTED"}).json()
    rejected = client.get(f"/companies/{target['id']}/peers", params={"status": "REJECTED"}).json()
    assert all(p["status"] == "SELECTED" for p in selected)
    assert all(p["status"] == "REJECTED" for p in rejected)


# --- valuation ---


def test_valuation_requires_min_selected_peers(client, db_session):
    target = _create_company(client, "TGT6", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, target["id"], revenue=100.0, ebitda=20.0)
    response = client.get(f"/companies/{target['id']}/valuation")
    assert response.status_code == 422


def test_valuation_computes_correct_medians_and_entry_ev(client, db_session):
    target = _create_company(client, "TGT7", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, target["id"], revenue=100.0, ebitda=20.0, total_debt=50.0, cash=10.0)

    # Peer A: ev = 300+50-10=340; ev/rev=3.4; ev/ebitda=17.0
    peer_a = _create_company(client, "PEERA", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, peer_a["id"], revenue=100.0, ebitda=20.0, market_cap=300.0, total_debt=50.0, cash=10.0)

    # Peer B: ev = 380+60-20=420; ev/rev=4.2; ev/ebitda=21.0
    peer_b = _create_company(client, "PEERB", sector="Tech", industry="Software")
    _set_market_and_financials(db_session, peer_b["id"], revenue=100.0, ebitda=20.0, market_cap=380.0, total_debt=60.0, cash=20.0)

    client.post(f"/companies/{target['id']}/peers/generate")

    response = client.get(f"/companies/{target['id']}/valuation")
    assert response.status_code == 200
    body = response.json()

    assert body["peer_count"] == 2
    assert body["median_ev_ebitda"] == 19.0  # (17.0 + 21.0) / 2
    assert body["implied_ev_from_ebitda"] == 19.0 * 20.0
    assert body["entry_ev"] == body["implied_ev_from_ebitda"]
    assert body["entry_net_debt"] == 40.0  # target's own 50 - 10
    assert body["entry_equity_value"] == body["entry_ev"] - 40.0

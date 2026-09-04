"""POST /companies/{id}/financials -- manual entry for private companies
that have no CIK and no SEC/EDGAR filing, so /ingest can never work for
them. This is the only way their financials can enter DealLens at all;
everything downstream (screening, comps, LBO) is source-agnostic once a
FinancialPeriod row exists.
"""

from datetime import date

import pytest


def _create_company(client, ticker="PRIVCO", cik=None):
    return client.post(
        "/companies",
        json={"ticker": ticker, "name": f"{ticker} Inc.", "cik": cik, "sector": "Industrials"},
    ).json()


def _valid_payload(**overrides):
    payload = {
        "fiscal_year": 2025,
        "period_end_date": "2025-12-31",
        "period_type": "FY",
        "currency": "USD",
        "source_ref": "management-provided FY2025 draft P&L",
        "revenue": 50_000_000.0,
        "ebitda": 8_000_000.0,
        "total_debt": 15_000_000.0,
        "cash_and_equivalents": 2_000_000.0,
    }
    payload.update(overrides)
    return payload


def test_manual_entry_creates_a_financial_period_for_a_no_cik_company(client, db_session):
    company = _create_company(client)  # no CIK -- a genuinely private company
    response = client.post(f"/companies/{company['id']}/financials", json=_valid_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "MANUAL"
    assert body["is_estimate"] is True  # unaudited, always flagged as such
    assert body["source_ref"] == "management-provided FY2025 draft P&L"
    assert body["revenue"] == pytest.approx(50_000_000.0)
    assert body["ebitda"] == pytest.approx(8_000_000.0)


def test_manual_entry_appears_in_financials_list(client, db_session):
    company = _create_company(client)
    client.post(f"/companies/{company['id']}/financials", json=_valid_payload())

    response = client.get(f"/companies/{company['id']}/financials")
    assert response.status_code == 200
    periods = response.json()
    assert len(periods) == 1
    assert periods[0]["source"] == "MANUAL"


def test_manual_entry_unblocks_screening_score_for_a_private_company(client, db_session):
    # The whole point: once a manual FinancialPeriod exists, the exact same
    # deterministic screening engine that runs on EDGAR data works
    # identically -- the gap was only ever "getting data in".
    company = _create_company(client)
    client.post(f"/companies/{company['id']}/financials", json=_valid_payload())

    response = client.get(f"/companies/{company['id']}/screening-score")
    assert response.status_code == 200
    body = response.json()
    assert body["score"] > 0
    growth_factor = next(f for f in body["factors"] if f["name"] == "growth")
    assert growth_factor is not None


def test_manual_entry_requires_at_least_one_core_figure(client, db_session):
    company = _create_company(client)
    payload = _valid_payload(revenue=None, ebitda=None, operating_cash_flow=None)
    response = client.post(f"/companies/{company['id']}/financials", json=payload)
    assert response.status_code == 422


def test_manual_entry_normalizes_negative_capex_and_debt_to_positive_magnitude(client, db_session):
    company = _create_company(client)
    payload = _valid_payload(capex=-3_000_000.0, total_debt=-15_000_000.0)
    response = client.post(f"/companies/{company['id']}/financials", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["capex"] == pytest.approx(3_000_000.0)
    assert body["total_debt"] == pytest.approx(15_000_000.0)


def test_manual_entry_invalid_period_type_returns_422(client, db_session):
    company = _create_company(client)
    payload = _valid_payload(period_type="NONSENSE")
    response = client.post(f"/companies/{company['id']}/financials", json=payload)
    assert response.status_code == 422


def test_manual_entry_company_not_found_returns_404(client, db_session):
    response = client.post("/companies/does-not-exist/financials", json=_valid_payload())
    assert response.status_code == 404


def test_manual_entry_coexists_with_edgar_entry_for_the_same_period(client, db_session):
    # A company can have a CIK (so /ingest works) AND a manual override/
    # supplement for the same fiscal year from a different source -- the
    # unique constraint is (company_id, period_end_date, period_type,
    # source), so these must NOT collide or overwrite each other.
    from app.models.financial_period import FinancialPeriod

    company = _create_company(client, cik="0000320193")
    db_session.add(
        FinancialPeriod(
            company_id=company["id"], fiscal_year=2025, period_end_date=date(2025, 12, 31),
            period_type="FY", currency="USD", source="SEC_EDGAR", revenue=400_000_000_000.0,
        )
    )
    db_session.commit()

    response = client.post(f"/companies/{company['id']}/financials", json=_valid_payload())
    assert response.status_code == 201

    periods = client.get(f"/companies/{company['id']}/financials").json()
    assert len(periods) == 2
    assert {p["source"] for p in periods} == {"SEC_EDGAR", "MANUAL"}


def test_re_posting_the_same_manual_period_upserts_rather_than_duplicates(client, db_session):
    company = _create_company(client)
    client.post(f"/companies/{company['id']}/financials", json=_valid_payload())
    client.post(f"/companies/{company['id']}/financials", json=_valid_payload(revenue=55_000_000.0))

    periods = client.get(f"/companies/{company['id']}/financials").json()
    assert len(periods) == 1
    assert periods[0]["revenue"] == pytest.approx(55_000_000.0)

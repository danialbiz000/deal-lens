from datetime import date

import pytest

from app.models.company import Company
from app.models.financial_period import FinancialPeriod


def _create_company(client, ticker="ACME", sector="Tech", industry="Software"):
    return client.post(
        "/companies", json={"ticker": ticker, "name": f"{ticker} Inc.", "sector": sector, "industry": industry}
    ).json()


def _add_fy_period(db_session, company_id, fiscal_year=2023, **kwargs):
    defaults = dict(
        company_id=company_id,
        fiscal_year=fiscal_year,
        period_end_date=date(fiscal_year, 12, 31),
        period_type="FY",
        currency="USD",
        source="SEC_EDGAR",
        revenue=500.0,
        ebitda=100.0,
        operating_cash_flow=90.0,
        capex=15.0,
        total_debt=100.0,
        cash_and_equivalents=20.0,
    )
    defaults.update(kwargs)
    period = FinancialPeriod(**defaults)
    db_session.add(period)
    db_session.commit()


def _set_market_cap(db_session, company_id, market_cap):
    company = db_session.get(Company, company_id)
    company.market_cap = market_cap
    db_session.commit()


def test_run_lbo_requires_scenario(client, db_session):
    company = _create_company(client, "NOSCEN")
    _add_fy_period(db_session, company["id"])
    response = client.post(f"/companies/{company['id']}/lbo/base/run", json={"entry_ev": 1000.0})
    assert response.status_code == 422


def test_run_lbo_requires_target_financials(client):
    company = _create_company(client, "NOFIN")
    client.post(f"/companies/{company['id']}/scenarios/generate")
    response = client.post(f"/companies/{company['id']}/lbo/base/run", json={"entry_ev": 1000.0})
    assert response.status_code == 422


def test_run_lbo_requires_entry_ev_or_peers(client, db_session):
    company = _create_company(client, "NOPEERS")
    _add_fy_period(db_session, company["id"])
    client.post(f"/companies/{company['id']}/scenarios/generate")
    response = client.post(f"/companies/{company['id']}/lbo/base/run", json={})
    assert response.status_code == 422


def test_run_lbo_with_entry_ev_override_succeeds(client, db_session):
    company = _create_company(client, "OVERRIDE1")
    _add_fy_period(db_session, company["id"])
    client.post(f"/companies/{company['id']}/scenarios/generate")

    response = client.post(f"/companies/{company['id']}/lbo/base/run", json={"entry_ev": 1000.0})
    assert response.status_code == 200
    body = response.json()

    assert body["case_type"] == "BASE"
    assert body["formula_version"] == "lbo_v0.1"
    assert body["sources_uses"]["reconciles"] is True
    assert len(body["schedule"]) == 6  # year 0 + 5 hold years (default)
    assert body["value_creation_bridge"]["total"] == pytest.approx(body["moic"], abs=1e-6)


def test_run_lbo_via_full_comps_flow(client, db_session):
    target = _create_company(client, "TGTLBO")
    _add_fy_period(db_session, target["id"], revenue=500.0, ebitda=100.0, total_debt=100.0, cash_and_equivalents=20.0)
    _set_market_cap(db_session, target["id"], 800.0)

    peer = _create_company(client, "PEERLBO")
    _add_fy_period(db_session, peer["id"], revenue=520.0, ebitda=105.0, total_debt=90.0, cash_and_equivalents=25.0)
    _set_market_cap(db_session, peer["id"], 900.0)

    peer2 = _create_company(client, "PEERLBO2")
    _add_fy_period(db_session, peer2["id"], revenue=480.0, ebitda=95.0, total_debt=95.0, cash_and_equivalents=15.0)
    _set_market_cap(db_session, peer2["id"], 850.0)

    client.post(f"/companies/{target['id']}/peers/generate")
    valuation = client.get(f"/companies/{target['id']}/valuation")
    assert valuation.status_code == 200

    client.post(f"/companies/{target['id']}/scenarios/generate")
    response = client.post(f"/companies/{target['id']}/lbo/base/run", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["entry_ev"] == pytest.approx(valuation.json()["entry_ev"])


def test_run_lbo_is_deterministic_across_repeated_calls(client, db_session):
    company = _create_company(client, "DETERM")
    _add_fy_period(db_session, company["id"])
    client.post(f"/companies/{company['id']}/scenarios/generate")

    first = client.post(f"/companies/{company['id']}/lbo/base/run", json={"entry_ev": 1000.0}).json()
    second = client.post(f"/companies/{company['id']}/lbo/base/run", json={"entry_ev": 1000.0}).json()

    assert first["moic"] == second["moic"]
    assert first["irr"] == second["irr"]
    assert first["schedule"] == second["schedule"]


def test_run_lbo_respects_assumption_override(client, db_session):
    company = _create_company(client, "ASSUME")
    _add_fy_period(db_session, company["id"])
    client.post(f"/companies/{company['id']}/scenarios/generate")

    baseline = client.post(f"/companies/{company['id']}/lbo/base/run", json={"entry_ev": 1000.0}).json()

    client.post(
        f"/companies/{company['id']}/assumptions",
        json={"name": "lbo_leverage_multiple", "value_numeric": 3.0, "source": "manual:analyst"},
    )
    overridden = client.post(f"/companies/{company['id']}/lbo/base/run", json={"entry_ev": 1000.0}).json()

    assert overridden["entry_leverage"] == pytest.approx(3.0)
    assert overridden["entry_leverage"] != baseline["entry_leverage"]
    assert overridden["moic"] != baseline["moic"]


def test_get_lbo_case_404_before_run(client, db_session):
    company = _create_company(client, "NORUN")
    _add_fy_period(db_session, company["id"])
    client.post(f"/companies/{company['id']}/scenarios/generate")
    response = client.get(f"/companies/{company['id']}/lbo/base")
    assert response.status_code == 404


def test_get_lbo_case_fetches_last_computed_without_recompute(client, db_session):
    company = _create_company(client, "FETCHIT")
    _add_fy_period(db_session, company["id"])
    client.post(f"/companies/{company['id']}/scenarios/generate")
    run_result = client.post(f"/companies/{company['id']}/lbo/base/run", json={"entry_ev": 1000.0}).json()

    fetched = client.get(f"/companies/{company['id']}/lbo/base").json()
    # moic/irr round-trip through Numeric(10, 4) columns, so compare at that precision.
    assert fetched["moic"] == pytest.approx(run_result["moic"], abs=1e-4)
    assert fetched["irr"] == pytest.approx(run_result["irr"], abs=1e-4)
    assert fetched["value_creation_bridge"]["total"] == pytest.approx(fetched["moic"], abs=1e-4)


def test_lbo_sensitivity_grid_shape_and_monotonicity(client, db_session):
    company = _create_company(client, "SENS")
    _add_fy_period(db_session, company["id"])
    client.post(f"/companies/{company['id']}/scenarios/generate")
    client.post(f"/companies/{company['id']}/lbo/base/run", json={"entry_ev": 1000.0})

    response = client.get(f"/companies/{company['id']}/lbo/base/sensitivity", params={"step": 1.0, "size": 4})
    assert response.status_code == 200
    body = response.json()
    assert len(body["entry_multiples"]) == 4
    assert len(body["irr_grid"]) == 4
    assert all(len(row) == 4 for row in body["irr_grid"])

    for row in body["irr_grid"]:
        for a, b in zip(row, row[1:]):
            assert b > a  # IRR increases with exit multiple at fixed entry multiple


def test_lbo_invalid_case_type_returns_422(client, db_session):
    company = _create_company(client, "BADLBO")
    _add_fy_period(db_session, company["id"])
    response = client.post(f"/companies/{company['id']}/lbo/nonsense/run", json={"entry_ev": 1000.0})
    assert response.status_code == 422

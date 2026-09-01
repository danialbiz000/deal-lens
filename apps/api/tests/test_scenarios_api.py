from datetime import date

import pytest

from app.models.financial_period import FinancialPeriod


def _create_company(client, ticker="ACME"):
    return client.post("/companies", json={"ticker": ticker, "name": "Acme Corp"}).json()


def _add_fy_period(db_session, company_id, fiscal_year, revenue):
    period = FinancialPeriod(
        company_id=company_id,
        fiscal_year=fiscal_year,
        period_end_date=date(fiscal_year, 12, 31),
        period_type="FY",
        currency="USD",
        source="SEC_EDGAR",
        revenue=revenue,
    )
    db_session.add(period)
    db_session.commit()


def test_generate_scenarios_404_when_company_missing(client):
    response = client.post("/companies/does-not-exist/scenarios/generate")
    assert response.status_code == 404


def test_generate_scenarios_defaults_to_flat_growth_without_history(client):
    company = _create_company(client, "NOHIST")
    response = client.post(f"/companies/{company['id']}/scenarios/generate")
    assert response.status_code == 200
    body = response.json()
    by_case = {s["case_type"]: s for s in body["scenarios"]}
    assert by_case["BASE"]["revenue_growth_rate"] == pytest.approx(0.0)
    assert len(body["warnings"]) == 1


def test_generate_scenarios_uses_real_cagr_and_spec_deltas(client, db_session):
    company = _create_company(client, "GROW")
    _add_fy_period(db_session, company["id"], 2021, revenue=100.0)
    _add_fy_period(db_session, company["id"], 2023, revenue=121.0)  # 10% CAGR over 2 years

    response = client.post(f"/companies/{company['id']}/scenarios/generate")
    assert response.status_code == 200
    by_case = {s["case_type"]: s for s in response.json()["scenarios"]}

    base_growth = by_case["BASE"]["revenue_growth_rate"]
    assert base_growth == pytest.approx(0.10, abs=1e-6)

    assert by_case["BULL"]["revenue_growth_rate"] == pytest.approx(base_growth + 0.05, abs=1e-6)
    assert by_case["BULL"]["ebitda_margin_delta"] == pytest.approx(0.02)
    assert by_case["BULL"]["exit_multiple_delta"] == pytest.approx(1.0)

    assert by_case["BEAR"]["revenue_growth_rate"] == pytest.approx(base_growth - 0.05, abs=1e-6)
    assert by_case["BEAR"]["ebitda_margin_delta"] == pytest.approx(-0.02)
    assert by_case["BEAR"]["exit_multiple_delta"] == pytest.approx(-2.0)  # spec-literal value


def test_bear_growth_is_floored_at_negative_five_percent(client, db_session):
    company = _create_company(client, "DECLINE")
    # Steep historical decline: CAGR well below -5% on its own.
    _add_fy_period(db_session, company["id"], 2021, revenue=1000.0)
    _add_fy_period(db_session, company["id"], 2023, revenue=250.0)  # -50% CAGR

    response = client.post(f"/companies/{company['id']}/scenarios/generate")
    by_case = {s["case_type"]: s for s in response.json()["scenarios"]}
    assert by_case["BEAR"]["revenue_growth_rate"] == pytest.approx(-0.05, abs=1e-6)


def test_patch_scenario_sets_manual_override_and_survives_regeneration(client, db_session):
    company = _create_company(client, "OVERRIDE")
    _add_fy_period(db_session, company["id"], 2021, revenue=100.0)
    _add_fy_period(db_session, company["id"], 2023, revenue=121.0)
    client.post(f"/companies/{company['id']}/scenarios/generate")

    patch_response = client.patch(
        f"/companies/{company['id']}/scenarios/bull",
        json={"exit_multiple_delta": 3.5, "notes": "Analyst thinks bull case is understated"},
    )
    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["exit_multiple_delta"] == pytest.approx(3.5)
    assert body["source"] == "manual:analyst"

    regenerated = client.post(f"/companies/{company['id']}/scenarios/generate").json()
    bull = next(s for s in regenerated["scenarios"] if s["case_type"] == "BULL")
    assert bull["exit_multiple_delta"] == pytest.approx(3.5)  # override preserved
    assert bull["source"] == "manual:analyst"


def test_patch_scenario_invalid_case_type_returns_422(client):
    company = _create_company(client, "BADCASE")
    response = client.patch(f"/companies/{company['id']}/scenarios/nope", json={"exit_multiple_delta": 1.0})
    assert response.status_code == 422


def test_patch_scenario_before_generate_returns_404(client):
    company = _create_company(client, "NOSCEN")
    response = client.patch(f"/companies/{company['id']}/scenarios/base", json={"exit_multiple_delta": 1.0})
    assert response.status_code == 404

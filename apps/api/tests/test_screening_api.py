from datetime import date

from app.models.financial_period import FinancialPeriod


def _create_company(client, ticker="ACME"):
    return client.post("/companies", json={"ticker": ticker, "name": "Acme Corp"}).json()


def _add_financial_period(db_session, company_id, fiscal_year, **kwargs):
    defaults = dict(
        company_id=company_id,
        fiscal_year=fiscal_year,
        period_end_date=date(fiscal_year, 12, 31),
        period_type="FY",
        currency="USD",
        source="SEC_EDGAR",
    )
    defaults.update(kwargs)
    period = FinancialPeriod(**defaults)
    db_session.add(period)
    db_session.commit()
    return period


def test_screening_score_404_when_company_missing(client):
    response = client.get("/companies/does-not-exist/screening-score")
    assert response.status_code == 404


def test_screening_score_422_when_no_financial_periods(client):
    company = _create_company(client)
    response = client.get(f"/companies/{company['id']}/screening-score")
    assert response.status_code == 422
    assert "ingest" in response.json()["detail"].lower()


def test_screening_score_all_defaults_without_assumptions(client, db_session):
    company = _create_company(client)
    _add_financial_period(
        db_session,
        company["id"],
        2023,
        revenue=1000,
        ebitda=200,
        operating_cash_flow=180,
        capex=50,
        total_debt=400,
        cash_and_equivalents=100,
        interest_expense=20,
    )

    response = client.get(f"/companies/{company['id']}/screening-score")
    assert response.status_code == 200
    body = response.json()
    assert body["formula_version"] == "v0.1"
    assert 0 <= body["score"] <= 100
    assert len(body["factors"]) == 8

    by_name = {f["name"]: f for f in body["factors"]}
    assert by_name["growth"]["source"] == "default"  # only 1 FY period -> insufficient
    assert by_name["margins"]["source"] == "computed"
    for placeholder in ("business_quality", "market_structure", "exit_optionality", "management_execution"):
        assert by_name[placeholder]["source"] == "default"
        assert by_name[placeholder]["normalized_score"] == 50


def test_assumption_override_reflected_in_screening_score(client, db_session):
    company = _create_company(client)
    _add_financial_period(
        db_session,
        company["id"],
        2022,
        revenue=1000,
        ebitda=200,
        operating_cash_flow=180,
        capex=50,
        total_debt=400,
        cash_and_equivalents=100,
        interest_expense=20,
    )
    _add_financial_period(
        db_session,
        company["id"],
        2023,
        revenue=1200,
        ebitda=260,
        operating_cash_flow=220,
        capex=60,
        total_debt=380,
        cash_and_equivalents=120,
        interest_expense=18,
    )

    baseline = client.get(f"/companies/{company['id']}/screening-score").json()

    assumption_response = client.post(
        f"/companies/{company['id']}/assumptions",
        json={
            "name": "business_quality_score",
            "value_numeric": 95,
            "unit": "score_0_100",
            "source": "manual:analyst",
        },
    )
    assert assumption_response.status_code == 200

    overridden = client.get(f"/companies/{company['id']}/screening-score").json()
    assert overridden["score"] != baseline["score"]

    by_name = {f["name"]: f for f in overridden["factors"]}
    assert by_name["business_quality"]["normalized_score"] == 95
    assert by_name["business_quality"]["source"] == "assumption"

    # Determinism: calling twice with unchanged inputs returns identical score
    repeat = client.get(f"/companies/{company['id']}/screening-score").json()
    assert repeat["score"] == overridden["score"]


def test_assumption_score_out_of_range_returns_422(client):
    company = _create_company(client)
    response = client.post(
        f"/companies/{company['id']}/assumptions",
        json={"name": "business_quality_score", "value_numeric": 150, "source": "manual:analyst"},
    )
    assert response.status_code == 422


def test_assumption_upsert_is_idempotent_by_name(client):
    company = _create_company(client)
    client.post(
        f"/companies/{company['id']}/assumptions",
        json={"name": "management_execution_score", "value_numeric": 40, "source": "manual:analyst"},
    )
    client.post(
        f"/companies/{company['id']}/assumptions",
        json={"name": "management_execution_score", "value_numeric": 70, "source": "manual:analyst"},
    )
    response = client.get(f"/companies/{company['id']}/assumptions")
    matching = [a for a in response.json() if a["name"] == "management_execution_score"]
    assert len(matching) == 1
    assert matching[0]["value_numeric"] == 70

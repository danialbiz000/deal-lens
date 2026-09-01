from datetime import date

import pytest

from app.ai.client import ClaudeApiError
from app.ai.prompts.memo_sections import SECTION_KEYS
from app.models.financial_period import FinancialPeriod
from app.models.lbo_case import LboCase
from app.models.peer import Peer
from app.models.scenario import Scenario


def _create_company(client, ticker="ACME"):
    return client.post(
        "/companies", json={"ticker": ticker, "name": f"{ticker} Inc.", "sector": "Tech", "industry": "Software"}
    ).json()


def _add_fy_period(db_session, company_id):
    period = FinancialPeriod(
        company_id=company_id, fiscal_year=2023, period_end_date=date(2023, 12, 31),
        period_type="FY", currency="USD", source="SEC_EDGAR",
        revenue=500.0, ebitda=100.0, total_debt=100.0, cash_and_equivalents=20.0,
    )
    db_session.add(period)
    db_session.commit()


def _add_two_selected_peers(client, db_session, target_id):
    for i, (rev, ebitda) in enumerate([(520.0, 105.0), (480.0, 95.0)]):
        peer = _create_company(client, f"PEER{i}")
        db_session.add(
            FinancialPeriod(
                company_id=peer["id"], fiscal_year=2023, period_end_date=date(2023, 12, 31),
                period_type="FY", currency="USD", source="SEC_EDGAR", revenue=rev, ebitda=ebitda,
            )
        )
        db_session.add(
            Peer(
                target_company_id=target_id, peer_company_id=peer["id"], status="SELECTED",
                similarity_score=80.0, ev_revenue_multiple=3.0, ev_ebitda_multiple=10.0,
                source="auto:top_k_similarity",
            )
        )
    db_session.commit()


def _add_lbo_case(db_session, company_id, case_type="BASE"):
    scenario = Scenario(
        company_id=company_id, case_type=case_type, revenue_growth_rate=0.05,
        ebitda_margin_delta=0.0, exit_multiple_delta=0.0, source="default:spec_calibration",
    )
    db_session.add(scenario)
    db_session.flush()
    db_session.add(
        LboCase(
            company_id=company_id, scenario_id=scenario.id, formula_version="lbo_v0.1",
            inputs_json={}, sources_uses_json={},
            schedule_json=[{"year": 0, "ebitda": 100.0, "interest": None}],
            value_creation_bridge_json={"total": 1.2},
            entry_ev=1000.0, exit_ev=1100.0, exit_equity_value=600.0,
            moic=1.2, irr=0.1, entry_leverage=5.0, exit_leverage=3.0,
        )
    )
    db_session.commit()


def _canned_memo_response(with_invalid_citation=False):
    sections = []
    for key in SECTION_KEYS:
        content = f"This section discusses {key}."
        if key == "financial_performance":
            content = "Screening score is 62.4 [[source: screening.score]]."
        if with_invalid_citation and key == "recommendation":
            content = "Revenue will 10x [[source: made.up.path]]."
        sections.append({"section_key": key, "title": key.replace("_", " ").title(), "content": content})
    return {"sections": sections}


def _full_prereqs_company(client, db_session, ticker="TARGET"):
    company = _create_company(client, ticker)
    _add_fy_period(db_session, company["id"])
    _add_two_selected_peers(client, db_session, company["id"])
    _add_lbo_case(db_session, company["id"], "BASE")
    return company


def test_memo_requires_screening(client, db_session):
    company = _create_company(client)
    response = client.post(f"/companies/{company['id']}/memo")
    assert response.status_code == 422


def test_memo_requires_valuation(client, db_session):
    company = _create_company(client)
    _add_fy_period(db_session, company["id"])
    response = client.post(f"/companies/{company['id']}/memo")
    assert response.status_code == 422


def test_memo_requires_base_lbo_case(client, db_session):
    company = _create_company(client)
    _add_fy_period(db_session, company["id"])
    _add_two_selected_peers(client, db_session, company["id"])
    response = client.post(f"/companies/{company['id']}/memo")
    assert response.status_code == 422


def test_memo_generates_ten_sections_with_fake_client(client, db_session, fake_claude_client):
    company = _full_prereqs_company(client, db_session)
    fake_claude_client([_canned_memo_response()])

    response = client.post(f"/companies/{company['id']}/memo")
    assert response.status_code == 200
    body = response.json()
    assert len(body["sections"]) == 10
    assert {s["section_key"] for s in body["sections"]} == set(SECTION_KEYS)
    assert body["version"] == 1
    assert body["prompt_version"] == "memo_prompt_v0.1"
    assert body["model"] == "fake-claude-test"


def test_memo_validation_report_flags_invalid_citation(client, db_session, fake_claude_client):
    company = _full_prereqs_company(client, db_session)
    fake_claude_client([_canned_memo_response(with_invalid_citation=True)])

    response = client.post(f"/companies/{company['id']}/memo")
    body = response.json()
    assert body["validation_report"]["status"] == "warnings"
    assert "made.up.path" in body["validation_report"]["invalid_citations"]


def test_memo_regeneration_creates_new_version(client, db_session, fake_claude_client):
    company = _full_prereqs_company(client, db_session)
    fake_claude_client([_canned_memo_response(), _canned_memo_response()])

    first = client.post(f"/companies/{company['id']}/memo").json()
    second = client.post(f"/companies/{company['id']}/memo").json()

    assert first["version"] == 1
    assert second["version"] == 2

    fetched_v1 = client.get(f"/companies/{company['id']}/memo/1")
    fetched_v2 = client.get(f"/companies/{company['id']}/memo/2")
    assert fetched_v1.status_code == 200
    assert fetched_v2.status_code == 200


def test_memo_list_endpoint(client, db_session, fake_claude_client):
    company = _full_prereqs_company(client, db_session)
    fake_claude_client([_canned_memo_response()])
    client.post(f"/companies/{company['id']}/memo")

    response = client.get(f"/companies/{company['id']}/memo")
    assert response.status_code == 200
    summaries = response.json()
    assert len(summaries) == 1
    assert summaries[0]["version"] == 1


def test_memo_version_not_found_returns_404(client, db_session):
    company = _create_company(client)
    response = client.get(f"/companies/{company['id']}/memo/1")
    assert response.status_code == 404


def test_memo_claude_api_error_returns_503(client, db_session):
    class BrokenClient:
        model_name = "broken"

        def complete_structured(self, system, user, json_schema):
            raise ClaudeApiError("Claude API: simulated outage")

    from app.ai.client import get_claude_client
    from app.main import app

    company = _full_prereqs_company(client, db_session)
    app.dependency_overrides[get_claude_client] = lambda: BrokenClient()
    try:
        response = client.post(f"/companies/{company['id']}/memo")
        assert response.status_code == 503
        assert "simulated outage" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_claude_client, None)

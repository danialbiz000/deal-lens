from datetime import date

import pytest

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


def _add_lbo_case(db_session, company_id, case_type, irr=0.10, moic=1.2, exit_leverage=3.0):
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
            schedule_json=[
                {"year": 0, "ebitda": 100.0, "interest": None},
                {"year": 1, "ebitda": 95.0, "interest": 30.0},
            ],
            value_creation_bridge_json={"total": moic},
            entry_ev=1000.0, exit_ev=1100.0, exit_equity_value=600.0,
            moic=moic, irr=irr, entry_leverage=5.0, exit_leverage=exit_leverage,
        )
    )
    db_session.commit()


def _full_prereqs_company(client, db_session, ticker="TARGET", bear_irr=0.10, bear_moic=1.2, bear_exit_leverage=3.0):
    company = _create_company(client, ticker)
    _add_fy_period(db_session, company["id"])
    _add_two_selected_peers(client, db_session, company["id"])
    _add_lbo_case(db_session, company["id"], "BASE")
    _add_lbo_case(db_session, company["id"], "BULL", irr=0.20, moic=2.0)
    _add_lbo_case(db_session, company["id"], "BEAR", irr=bear_irr, moic=bear_moic, exit_leverage=bear_exit_leverage)
    return company


def _canned_ic_responses(chair_recommendation="PROCEED_TO_DD"):
    return [
        {"case_summary": "Solid growth story.", "key_points": ["Point A", "Point B"]},
        {"market_challenges": ["Competitive pressure from incumbents."]},
        {"credit_concerns": ["Bear case leverage is elevated [[source: lbo.bear.exit_leverage]]."]},
        {"risk_flags": ["Customer concentration risk."]},
        {
            "llm_recommendation": chair_recommendation,
            "key_strengths": ["Cash conversion"],
            "key_risks": ["Multiple risk"],
            "unanswered_dd": ["Management depth"],
        },
    ]


def test_ic_simulation_requires_all_three_lbo_cases(client, db_session):
    company = _create_company(client)
    _add_fy_period(db_session, company["id"])
    _add_two_selected_peers(client, db_session, company["id"])
    _add_lbo_case(db_session, company["id"], "BASE")
    # BULL and BEAR deliberately missing
    response = client.post(f"/companies/{company['id']}/ic-simulation")
    assert response.status_code == 422
    assert "bull" in response.json()["detail"]
    assert "bear" in response.json()["detail"]


def test_ic_simulation_runs_five_roles_sequentially(client, db_session, fake_claude_client):
    company = _full_prereqs_company(client, db_session)
    fake = fake_claude_client(_canned_ic_responses())

    response = client.post(f"/companies/{company['id']}/ic-simulation")
    assert response.status_code == 200
    assert len(fake.calls) == 5

    # Sequential: the Industry call's prompt must contain the Analyst's output.
    industry_call = fake.calls[1]
    assert "Solid growth story" in industry_call["user"]

    # The IC Chair call's prompt must contain all 4 prior roles' output.
    chair_call = fake.calls[4]
    assert "Solid growth story" in chair_call["user"]
    assert "Competitive pressure" in chair_call["user"]
    assert "Bear case leverage" in chair_call["user"]
    assert "Customer concentration" in chair_call["user"]

    body = response.json()
    assert len(body["transcript"]) == 5
    assert [r["role"] for r in body["transcript"]] == ["analyst", "industry", "credit", "risk", "ic_chair"]


def test_ic_simulation_no_override_when_bear_case_passes(client, db_session, fake_claude_client):
    company = _full_prereqs_company(client, db_session, bear_irr=0.10, bear_moic=1.2, bear_exit_leverage=3.0)
    fake_claude_client(_canned_ic_responses(chair_recommendation="PROCEED_TO_DD"))

    response = client.post(f"/companies/{company['id']}/ic-simulation")
    body = response.json()
    assert body["llm_recommendation"] == "PROCEED_TO_DD"
    assert body["recommendation"] == "PROCEED_TO_DD"
    assert body["override_fired"] is False
    assert body["override_reason"] is None


def test_ic_simulation_override_fires_when_bear_case_fails_and_llm_says_proceed(
    client, db_session, fake_claude_client
):
    """THE critical test (design doc section 9/10): mock the IC Chair to say
    PROCEED_TO_DD while feeding a bear case that fails a threshold (IRR
    5% < 8% floor). Assert the persisted recommendation is HOLD,
    override_fired is true, and llm_recommendation still shows the
    original PROCEED_TO_DD -- the override must be visible, never silent.
    """
    company = _full_prereqs_company(client, db_session, bear_irr=0.05, bear_moic=1.2, bear_exit_leverage=3.0)
    fake_claude_client(_canned_ic_responses(chair_recommendation="PROCEED_TO_DD"))

    response = client.post(f"/companies/{company['id']}/ic-simulation")
    assert response.status_code == 200
    body = response.json()

    assert body["llm_recommendation"] == "PROCEED_TO_DD"  # what the model actually said, preserved
    assert body["recommendation"] == "HOLD"  # forced by the deterministic gate
    assert body["override_fired"] is True
    assert body["override_reason"] is not None
    assert "IRR" in body["override_reason"]


def test_ic_simulation_override_never_fires_for_hold_or_pass(client, db_session, fake_claude_client):
    # Bear case fails a threshold, but the LLM already said HOLD -- the
    # override only ever pushes toward more conservative, never re-decides
    # an already-conservative call.
    company = _full_prereqs_company(client, db_session, bear_irr=0.05)
    fake_claude_client(_canned_ic_responses(chair_recommendation="HOLD"))

    response = client.post(f"/companies/{company['id']}/ic-simulation")
    body = response.json()
    assert body["llm_recommendation"] == "HOLD"
    assert body["recommendation"] == "HOLD"
    assert body["override_fired"] is False


def test_ic_simulation_regeneration_creates_new_version(client, db_session, fake_claude_client):
    company = _full_prereqs_company(client, db_session)
    fake_claude_client(_canned_ic_responses() + _canned_ic_responses())

    first = client.post(f"/companies/{company['id']}/ic-simulation").json()
    second = client.post(f"/companies/{company['id']}/ic-simulation").json()
    assert first["version"] == 1
    assert second["version"] == 2

    assert client.get(f"/companies/{company['id']}/ic-simulation/1").status_code == 200
    assert client.get(f"/companies/{company['id']}/ic-simulation/2").status_code == 200


def test_ic_simulation_list_endpoint_summary(client, db_session, fake_claude_client):
    company = _full_prereqs_company(client, db_session, bear_irr=0.05)
    fake_claude_client(_canned_ic_responses(chair_recommendation="PROCEED_TO_DD"))
    client.post(f"/companies/{company['id']}/ic-simulation")

    response = client.get(f"/companies/{company['id']}/ic-simulation")
    assert response.status_code == 200
    summaries = response.json()
    assert len(summaries) == 1
    assert summaries[0]["recommendation"] == "HOLD"
    assert summaries[0]["override_fired"] is True


def test_ic_simulation_version_not_found_returns_404(client, db_session):
    company = _create_company(client)
    response = client.get(f"/companies/{company['id']}/ic-simulation/1")
    assert response.status_code == 404

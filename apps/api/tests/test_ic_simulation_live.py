"""Optional live integration test for the IC simulator.

Skips gracefully without ANTHROPIC_API_KEY (design doc section 9). Asserts
basic shape and enum validity rather than exact content -- 5 role outputs
present, recommendation is one of the 3 valid enum values -- since LLM
output isn't byte-reproducible.
"""

import os
from datetime import date

import pytest

from app.models.financial_period import FinancialPeriod
from app.models.lbo_case import LboCase
from app.models.peer import Peer
from app.models.scenario import Scenario

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set -- skipping live Claude API test",
)


def _create_company(client, ticker):
    return client.post(
        "/companies", json={"ticker": ticker, "name": f"{ticker} Inc.", "sector": "Tech", "industry": "Software"}
    ).json()


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
            schedule_json=[{"year": 0, "ebitda": 100.0, "interest": None}, {"year": 1, "ebitda": 95.0, "interest": 30.0}],
            value_creation_bridge_json={"total": moic},
            entry_ev=1000.0, exit_ev=1100.0, exit_equity_value=600.0,
            moic=moic, irr=irr, entry_leverage=5.0, exit_leverage=exit_leverage,
        )
    )
    db_session.commit()


def test_ic_simulation_against_real_claude_api(client, db_session):
    company = _create_company(client, "LIVEIC")
    db_session.add(
        FinancialPeriod(
            company_id=company["id"], fiscal_year=2023, period_end_date=date(2023, 12, 31),
            period_type="FY", currency="USD", source="SEC_EDGAR",
            revenue=500.0, ebitda=100.0, total_debt=100.0, cash_and_equivalents=20.0,
        )
    )
    for i, (rev, ebitda) in enumerate([(520.0, 105.0), (480.0, 95.0)]):
        peer = _create_company(client, f"LIVEICPEER{i}")
        db_session.add(
            FinancialPeriod(
                company_id=peer["id"], fiscal_year=2023, period_end_date=date(2023, 12, 31),
                period_type="FY", currency="USD", source="SEC_EDGAR", revenue=rev, ebitda=ebitda,
            )
        )
        db_session.add(
            Peer(
                target_company_id=company["id"], peer_company_id=peer["id"], status="SELECTED",
                similarity_score=80.0, ev_revenue_multiple=3.0, ev_ebitda_multiple=10.0,
                source="auto:top_k_similarity",
            )
        )
    db_session.commit()

    _add_lbo_case(db_session, company["id"], "BASE")
    _add_lbo_case(db_session, company["id"], "BULL", irr=0.20, moic=2.0)
    _add_lbo_case(db_session, company["id"], "BEAR", irr=0.05, moic=0.9, exit_leverage=7.0)  # deliberately fails gate

    response = client.post(f"/companies/{company['id']}/ic-simulation")
    assert response.status_code == 200
    body = response.json()

    assert len(body["transcript"]) == 5
    assert [r["role"] for r in body["transcript"]] == ["analyst", "industry", "credit", "risk", "ic_chair"]
    assert body["llm_recommendation"] in ("PROCEED_TO_DD", "HOLD", "PASS")
    assert body["recommendation"] in ("PROCEED_TO_DD", "HOLD", "PASS")
    # The constructed bear case fails 3 thresholds -- a PROCEED_TO_DD from
    # the model here MUST be overridden to HOLD, regardless of what the
    # live model actually says.
    if body["llm_recommendation"] == "PROCEED_TO_DD":
        assert body["recommendation"] == "HOLD"
        assert body["override_fired"] is True

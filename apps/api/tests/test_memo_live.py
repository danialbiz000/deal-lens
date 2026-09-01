"""Optional live integration test for memo generation.

Skips gracefully without ANTHROPIC_API_KEY (design doc section 9), same
pattern as Phase 2's FMP-key-optional market-data tests. Not part of the
default offline test suite's coverage claims -- asserts basic shape (10
sections present) rather than exact content, since LLM output isn't
byte-reproducible the way the rest of this project deliberately is.
"""

import os
from datetime import date

import pytest

from app.ai.prompts.memo_sections import SECTION_KEYS
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


def test_memo_generation_against_real_claude_api(client, db_session):
    company = _create_company(client, "LIVEMEMO")
    db_session.add(
        FinancialPeriod(
            company_id=company["id"], fiscal_year=2023, period_end_date=date(2023, 12, 31),
            period_type="FY", currency="USD", source="SEC_EDGAR",
            revenue=500.0, ebitda=100.0, total_debt=100.0, cash_and_equivalents=20.0,
        )
    )
    for i, (rev, ebitda) in enumerate([(520.0, 105.0), (480.0, 95.0)]):
        peer = _create_company(client, f"LIVEPEER{i}")
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
    scenario = Scenario(
        company_id=company["id"], case_type="BASE", revenue_growth_rate=0.05,
        ebitda_margin_delta=0.0, exit_multiple_delta=0.0, source="default:spec_calibration",
    )
    db_session.add(scenario)
    db_session.flush()
    db_session.add(
        LboCase(
            company_id=company["id"], scenario_id=scenario.id, formula_version="lbo_v0.1",
            inputs_json={}, sources_uses_json={},
            schedule_json=[{"year": 0, "ebitda": 100.0, "interest": None}],
            value_creation_bridge_json={"total": 1.2},
            entry_ev=1000.0, exit_ev=1100.0, exit_equity_value=600.0,
            moic=1.2, irr=0.1, entry_leverage=5.0, exit_leverage=3.0,
        )
    )
    db_session.commit()

    response = client.post(f"/companies/{company['id']}/memo")
    assert response.status_code == 200
    body = response.json()
    assert len(body["sections"]) == 10
    assert {s["section_key"] for s in body["sections"]} == set(SECTION_KEYS)
    assert body["validation_report"]["status"] in ("ok", "warnings")

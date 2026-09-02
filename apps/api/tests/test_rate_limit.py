"""Dedicated rate-limit tests -- the ONLY tests in this suite that enable
the real in-memory limiter (docs/phase4-ai-layer-design.md section 12.6).
Every other test relies on RATE_LIMIT_ENABLED=false (set in conftest.py)
so slowapi never interferes with the many other calls the rest of the
suite makes to these same endpoints.
"""

from datetime import date

from app.ai.prompts.memo_sections import SECTION_KEYS
from app.models.financial_period import FinancialPeriod
from app.models.lbo_case import LboCase
from app.models.peer import Peer
from app.models.scenario import Scenario


def _create_company(client, ticker):
    return client.post(
        "/companies", json={"ticker": ticker, "name": f"{ticker} Inc.", "sector": "Tech", "industry": "Software"}
    ).json()


def _fully_seed_company_for_memo(client, db_session, ticker):
    """A company with everything /memo requires as a prerequisite:
    financials, >=2 SELECTED peers, and a BASE LBO case."""
    company = _create_company(client, ticker)
    db_session.add(
        FinancialPeriod(
            company_id=company["id"], fiscal_year=2023, period_end_date=date(2023, 12, 31),
            period_type="FY", currency="USD", source="SEC_EDGAR",
            revenue=500.0, ebitda=100.0, total_debt=100.0, cash_and_equivalents=20.0,
        )
    )
    for i, (rev, ebitda) in enumerate([(520.0, 105.0), (480.0, 95.0)]):
        peer = _create_company(client, f"{ticker}P{i}")
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
    return company


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


def _fully_seed_company_for_both_ai_endpoints(client, db_session, ticker):
    """A company with everything BOTH /memo and /ic-simulation require:
    financials, >=2 SELECTED peers, and BASE+BULL+BEAR LBO cases. The bear
    case is set to pass every gate threshold so this test isn't entangled
    with override behavior (covered separately in test_ai_ic_simulation_api.py).
    """
    company = _create_company(client, ticker)
    db_session.add(
        FinancialPeriod(
            company_id=company["id"], fiscal_year=2023, period_end_date=date(2023, 12, 31),
            period_type="FY", currency="USD", source="SEC_EDGAR",
            revenue=500.0, ebitda=100.0, total_debt=100.0, cash_and_equivalents=20.0,
        )
    )
    for i, (rev, ebitda) in enumerate([(520.0, 105.0), (480.0, 95.0)]):
        peer = _create_company(client, f"{ticker}P{i}")
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

    _add_lbo_case(db_session, company["id"], "BASE", irr=0.10, moic=1.2, exit_leverage=3.0)
    _add_lbo_case(db_session, company["id"], "BULL", irr=0.20, moic=2.0, exit_leverage=2.0)
    _add_lbo_case(db_session, company["id"], "BEAR", irr=0.10, moic=1.2, exit_leverage=3.0)  # passes every threshold
    return company


def _canned_memo_response():
    return {"sections": [{"section_key": k, "title": k, "content": "n/a"} for k in SECTION_KEYS]}


def _canned_ic_responses():
    """5 canned role outputs, in order, for one full IC simulation run."""
    return [
        {"case_summary": "Solid growth story.", "key_points": ["Point A"]},
        {"market_challenges": ["Competitive pressure."]},
        {"credit_concerns": ["Leverage note [[source: lbo.bear.exit_leverage]]."]},
        {"risk_flags": ["Concentration risk."]},
        {
            "llm_recommendation": "PROCEED_TO_DD",
            "key_strengths": ["Cash conversion"],
            "key_risks": ["Multiple risk"],
            "unanswered_dd": ["Management depth"],
        },
    ]


def test_ai_per_ip_limit_combines_across_memo_and_ic_simulation(
    client, db_session, fake_claude_client, rate_limiting_enabled, override_setting
):
    """Regression test for the exact gap tester found: the per-IP AI limit
    must combine usage across /memo AND /ic-simulation into one shared
    counter (design doc section 12.2: "10/minute across both AI endpoints
    combined"), not enforce the full limit independently per route. Before
    the `shared_limit(scope=...)` fix, `key_style="endpoint"` alone still
    differentiated the two routes by function name, so alternating calls
    between them never tripped the limit at all.
    """
    override_setting("rate_limit_ai_per_company", "1000/hour;1000/day")  # keep company dimension out of the way
    override_setting("rate_limit_ai_per_ip", "2/minute")

    company = _fully_seed_company_for_both_ai_endpoints(client, db_session, "RLSHARE")
    # Only 2 calls will actually reach the fake client -- the 3rd is
    # rejected by the rate limiter before the route body ever executes.
    fake_claude_client([_canned_memo_response(), *_canned_ic_responses()])

    first = client.post(f"/companies/{company['id']}/memo")
    second = client.post(f"/companies/{company['id']}/ic-simulation")
    third = client.post(f"/companies/{company['id']}/memo")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["scope"] == "ai_per_ip"


def test_ai_per_company_limit_still_separate_per_endpoint_after_shared_ip_fix(
    client, db_session, fake_claude_client, rate_limiting_enabled, override_setting
):
    """The fix for the per-IP sharing gap must NOT accidentally start
    sharing the per-company dimension too -- design doc section 12.2
    specifies per-company limits are "per company, per endpoint"
    deliberately. Exhausting /memo's per-company budget must not affect
    /ic-simulation's separate per-company budget for the same company.
    """
    override_setting("rate_limit_ai_per_company", "1/hour;1/day")  # exhausted after a single memo call
    override_setting("rate_limit_ai_per_ip", "1000/minute")  # keep the IP dimension out of the way

    company = _fully_seed_company_for_both_ai_endpoints(client, db_session, "RLSEPARATE")
    fake_claude_client([_canned_memo_response(), *_canned_ic_responses()])

    memo_first = client.post(f"/companies/{company['id']}/memo")
    memo_second = client.post(f"/companies/{company['id']}/memo")  # same company, same endpoint -- exhausted
    ic_first = client.post(f"/companies/{company['id']}/ic-simulation")  # same company, DIFFERENT endpoint -- fresh budget

    assert memo_first.status_code == 200
    assert memo_second.status_code == 429
    assert memo_second.json()["scope"] == "ai_per_company"
    assert ic_first.status_code == 200


def test_ai_per_company_limit_fires_on_third_call(
    client, db_session, fake_claude_client, rate_limiting_enabled, override_setting
):
    override_setting("rate_limit_ai_per_company", "2/minute")
    override_setting("rate_limit_ai_per_ip", "1000/minute")  # keep the other dimension out of the way

    company = _fully_seed_company_for_memo(client, db_session, "RLCOMP")
    fake_claude_client([_canned_memo_response(), _canned_memo_response(), _canned_memo_response()])

    first = client.post(f"/companies/{company['id']}/memo")
    second = client.post(f"/companies/{company['id']}/memo")
    third = client.post(f"/companies/{company['id']}/memo")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429

    body = third.json()
    assert body["error"] == "rate_limit_exceeded"
    assert body["scope"] == "ai_per_company"
    assert "for this company" in body["message"]
    assert body["retry_after_seconds"] is not None
    assert body["retry_after_seconds"] > 0
    assert "Retry-After" in third.headers


def test_ai_per_ip_limit_fires_independently_of_company(
    client, db_session, fake_claude_client, rate_limiting_enabled, override_setting
):
    # Company dimension deliberately out of the way -- this test proves the
    # per-IP backstop trips even when no single company is anywhere near
    # its own limit, per design doc section 12.2: "a per-company limit
    # alone doesn't stop one client hammering many different companies."
    override_setting("rate_limit_ai_per_company", "1000/hour;1000/day")
    override_setting("rate_limit_ai_per_ip", "2/minute")

    company_a = _fully_seed_company_for_memo(client, db_session, "RLIPA")
    company_b = _fully_seed_company_for_memo(client, db_session, "RLIPB")
    fake_claude_client([_canned_memo_response(), _canned_memo_response(), _canned_memo_response()])

    first = client.post(f"/companies/{company_a['id']}/memo")
    second = client.post(f"/companies/{company_b['id']}/memo")  # different company, same "IP"
    third = client.post(f"/companies/{company_a['id']}/memo")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["scope"] == "ai_per_ip"


def test_rate_limit_disabled_bypasses_enforcement(client, db_session, fake_claude_client, override_setting):
    from app.rate_limit import limiter

    limiter.reset()
    limiter.enabled = False  # explicit -- matches the suite-wide default, asserted here directly
    override_setting("rate_limit_ai_per_company", "1/minute")  # would fail the 2nd call if enforced

    company = _fully_seed_company_for_memo(client, db_session, "RLOFF")
    fake_claude_client([_canned_memo_response(), _canned_memo_response()])

    first = client.post(f"/companies/{company['id']}/memo")
    second = client.post(f"/companies/{company['id']}/memo")

    assert first.status_code == 200
    assert second.status_code == 200  # would be 429 if enforcement were live


def test_ingest_per_company_limit_fires(client, db_session, rate_limiting_enabled, override_setting):
    override_setting("rate_limit_ingest_per_company", "2/minute")
    override_setting("rate_limit_ingest_per_ip", "1000/minute")

    company = _create_company(client, "RLING")
    # No CIK and no FMP_API_KEY in the test environment -- both ingest
    # source blocks skip themselves with a warning, no real network calls.
    payload = {"years_back": 1}

    first = client.post(f"/companies/{company['id']}/ingest", json=payload)
    second = client.post(f"/companies/{company['id']}/ingest", json=payload)
    third = client.post(f"/companies/{company['id']}/ingest", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["scope"] == "ingest_per_company"


def test_ingest_per_ip_limit_fires_independently_of_company(client, db_session, rate_limiting_enabled, override_setting):
    override_setting("rate_limit_ingest_per_company", "1000/hour")
    override_setting("rate_limit_ingest_per_ip", "2/minute")

    company_a = _create_company(client, "RLINGIPA")
    company_b = _create_company(client, "RLINGIPB")
    payload = {"years_back": 1}

    first = client.post(f"/companies/{company_a['id']}/ingest", json=payload)
    second = client.post(f"/companies/{company_b['id']}/ingest", json=payload)
    third = client.post(f"/companies/{company_a['id']}/ingest", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["scope"] == "ingest_per_ip"

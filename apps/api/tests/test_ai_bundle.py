"""build_source_bundle unit tests against a seeded demo company
(docs/phase4-ai-layer-design.md section 10's acceptance checklist)."""

from datetime import date

import pytest

from app.ai.bundle import build_source_bundle
from app.models.company import Company
from app.models.financial_period import FinancialPeriod
from app.models.lbo_case import LboCase
from app.models.peer import Peer
from app.models.scenario import Scenario


def _create_company(client, ticker="ACME", sector="Technology", industry="Software"):
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


def test_bundle_company_section_always_present(client, db_session):
    company = _create_company(client)
    bundle = build_source_bundle(company["id"], db_session)
    assert bundle["company"]["ticker"] == "ACME"
    assert bundle["company"]["sector"] == "Technology"


def test_bundle_screening_is_none_without_financials(client, db_session):
    company = _create_company(client)
    bundle = build_source_bundle(company["id"], db_session)
    assert bundle["screening"] is None
    assert bundle["valuation"] is None
    assert bundle["lbo"] == {}


def test_bundle_screening_populated_once_financials_exist(client, db_session):
    company = _create_company(client)
    _add_fy_period(db_session, company["id"])
    bundle = build_source_bundle(company["id"], db_session)
    assert bundle["screening"] is not None
    assert 0 <= bundle["screening"]["score"] <= 100
    assert "growth" in bundle["screening"]["factors"]
    assert bundle["screening"]["formula_version"] == "v0.1"


def test_bundle_raises_for_unknown_company(db_session):
    with pytest.raises(ValueError):
        build_source_bundle("does-not-exist", db_session)


def test_bundle_full_nested_structure_against_seeded_company(client, db_session):
    """The full acceptance-checklist scenario: a company with financials,
    2 SELECTED peers, and all 3 LBO cases present -- every section of the
    bundle should be populated.
    """
    target = _create_company(client, "TARGET")
    _add_fy_period(db_session, target["id"])

    peer1 = _create_company(client, "PEER1")
    peer2 = _create_company(client, "PEER2")

    db_session.add(
        Peer(
            target_company_id=target["id"], peer_company_id=peer1["id"], status="SELECTED",
            similarity_score=80.0, ev_revenue_multiple=3.0, ev_ebitda_multiple=10.0, source="auto:top_k_similarity",
        )
    )
    db_session.add(
        Peer(
            target_company_id=target["id"], peer_company_id=peer2["id"], status="SELECTED",
            similarity_score=75.0, ev_revenue_multiple=3.5, ev_ebitda_multiple=11.0, source="auto:top_k_similarity",
        )
    )
    db_session.commit()

    for case_type in ("BASE", "BULL", "BEAR"):
        scenario = Scenario(
            company_id=target["id"], case_type=case_type,
            revenue_growth_rate=0.05, ebitda_margin_delta=0.0, exit_multiple_delta=0.0,
            source="default:spec_calibration",
        )
        db_session.add(scenario)
        db_session.flush()
        db_session.add(
            LboCase(
                company_id=target["id"], scenario_id=scenario.id, formula_version="lbo_v0.1",
                inputs_json={}, sources_uses_json={}, schedule_json=[{"year": 0, "ebitda": 100.0, "interest": None}],
                value_creation_bridge_json={"total": 1.2},
                entry_ev=1000.0, exit_ev=1100.0, exit_equity_value=600.0,
                moic=1.2, irr=0.1, entry_leverage=5.0, exit_leverage=3.0,
            )
        )
    db_session.commit()

    bundle = build_source_bundle(target["id"], db_session)

    assert bundle["screening"] is not None
    assert bundle["valuation"] is not None
    assert bundle["valuation"]["entry_ev"] == pytest.approx(bundle["valuation"]["ev_ebitda"]["median"] * 100.0)
    assert len(bundle["valuation"]["selected_peers"]) == 2
    assert set(bundle["lbo"].keys()) == {"base", "bull", "bear"}
    assert bundle["lbo"]["bear"]["moic"] == 1.2

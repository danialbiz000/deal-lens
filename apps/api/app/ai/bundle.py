"""build_source_bundle(company_id, db) -> dict -- the ONLY thing the model
is allowed to treat as fact (design doc section 3).

Calls the same underlying finance_engine functions Phases 0/2 already use
(score_company, compute_valuation) -- never a new calculation -- and reads
already-persisted LboCase rows directly (LBO results are computed
artifacts, unlike screening/valuation which are computed on demand and
never stored, which is exactly why this bundle needs to exist at all: it's
the only stable, reproducible record of "the figures a given memo/IC run
was based on").
"""

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.assumption import Assumption
from app.models.company import Company
from app.models.financial_period import FinancialPeriod
from app.models.lbo_case import LboCase
from app.models.peer import Peer
from app.models.scenario import Scenario
from finance_engine import AssumptionInput, FinancialPeriodInput, compute_valuation, score_company
from finance_engine.constants import COMPS_MIN_PEERS_FOR_VALUATION


def _latest_fy_period(db: Session, company_id: str) -> Optional[FinancialPeriod]:
    return (
        db.query(FinancialPeriod)
        .filter(FinancialPeriod.company_id == company_id, FinancialPeriod.period_type == "FY")
        .order_by(FinancialPeriod.fiscal_year.desc())
        .first()
    )


def _build_screening(db: Session, company_id: str) -> Optional[Dict[str, Any]]:
    period_rows = db.query(FinancialPeriod).filter(FinancialPeriod.company_id == company_id).all()
    if not period_rows:
        return None

    assumption_rows = db.query(Assumption).filter(Assumption.company_id == company_id).all()

    periods = [
        FinancialPeriodInput(
            fiscal_year=p.fiscal_year,
            period_end_date=p.period_end_date,
            period_type=p.period_type,
            source=p.source,
            revenue=float(p.revenue) if p.revenue is not None else None,
            ebitda=float(p.ebitda) if p.ebitda is not None else None,
            operating_cash_flow=float(p.operating_cash_flow) if p.operating_cash_flow is not None else None,
            capex=float(p.capex) if p.capex is not None else None,
            total_debt=float(p.total_debt) if p.total_debt is not None else None,
            cash_and_equivalents=float(p.cash_and_equivalents) if p.cash_and_equivalents is not None else None,
            interest_expense=float(p.interest_expense) if p.interest_expense is not None else None,
        )
        for p in period_rows
    ]
    assumptions = [
        AssumptionInput(name=a.name, value_numeric=float(a.value_numeric) if a.value_numeric is not None else None)
        for a in assumption_rows
    ]

    result = score_company(periods=periods, assumptions=assumptions)
    return {
        "score": result.score,
        "formula_version": result.formula_version,
        "factors": {
            f.name: {"normalized_score": f.normalized_score, "source": f.source, "weight": f.weight}
            for f in result.factors
        },
    }


def _build_valuation(db: Session, company: Company) -> Optional[Dict[str, Any]]:
    latest = _latest_fy_period(db, company.id)
    if latest is None or latest.revenue is None or latest.ebitda is None:
        return None

    selected_peers = db.query(Peer).filter(Peer.target_company_id == company.id, Peer.status == "SELECTED").all()
    multiples = [
        (float(p.ev_revenue_multiple), float(p.ev_ebitda_multiple))
        for p in selected_peers
        if p.ev_revenue_multiple is not None and p.ev_ebitda_multiple is not None
    ]
    if len(multiples) < COMPS_MIN_PEERS_FOR_VALUATION:
        return None

    result = compute_valuation(
        multiples,
        target_revenue=float(latest.revenue),
        target_ebitda=float(latest.ebitda),
        target_total_debt=float(latest.total_debt) if latest.total_debt is not None else 0.0,
        target_cash_and_equivalents=(
            float(latest.cash_and_equivalents) if latest.cash_and_equivalents is not None else 0.0
        ),
    )

    peer_company_ids = [p.peer_company_id for p in selected_peers]
    peer_companies = (
        {c.id: c for c in db.query(Company).filter(Company.id.in_(peer_company_ids)).all()}
        if peer_company_ids
        else {}
    )
    selected_peer_summaries = [
        {
            "ticker": peer_companies[p.peer_company_id].ticker if p.peer_company_id in peer_companies else None,
            "ev_ebitda_multiple": float(p.ev_ebitda_multiple) if p.ev_ebitda_multiple is not None else None,
            "similarity_score": float(p.similarity_score) if p.similarity_score is not None else None,
        }
        for p in selected_peers
    ]

    return {
        "entry_ev": result.entry_ev,
        "entry_equity_value": result.entry_equity_value,
        "ev_ebitda": {"median": result.median_ev_ebitda, "q1": result.q1_ev_ebitda, "q3": result.q3_ev_ebitda},
        "selected_peers": selected_peer_summaries,
    }


def _build_lbo(db: Session, company_id: str) -> Dict[str, Any]:
    lbo: Dict[str, Any] = {}
    for case_type in ("BASE", "BULL", "BEAR"):
        scenario = (
            db.query(Scenario)
            .filter(Scenario.company_id == company_id, Scenario.case_type == case_type)
            .first()
        )
        if scenario is None:
            continue
        case = (
            db.query(LboCase)
            .filter(LboCase.company_id == company_id, LboCase.scenario_id == scenario.id)
            .first()
        )
        if case is None:
            continue
        lbo[case_type.lower()] = {
            "moic": float(case.moic),
            "irr": float(case.irr),
            "entry_leverage": float(case.entry_leverage),
            "exit_leverage": float(case.exit_leverage),
            "value_creation_bridge": case.value_creation_bridge_json,
        }
    return lbo


def build_source_bundle(company_id: str, db: Session) -> Dict[str, Any]:
    """Assemble the full nested bundle from design doc section 3.

    Any section that cannot yet be computed (no financials ingested, fewer
    than 2 SELECTED peers, an LBO case not yet run) is `None`/absent rather
    than raising -- prerequisite validation (naming exactly what's missing)
    is the caller's responsibility (the memo/ic-simulation routers), so this
    function stays a pure best-effort assembler.
    """
    company = db.get(Company, company_id)
    if company is None:
        raise ValueError(f"company {company_id} not found")

    return {
        "company": {
            "ticker": company.ticker,
            "name": company.name,
            "sector": company.sector,
            "industry": company.industry,
        },
        "screening": _build_screening(db, company_id),
        "valuation": _build_valuation(db, company),
        "lbo": _build_lbo(db, company_id),
    }

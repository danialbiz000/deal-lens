"""LBO run/fetch + entry x exit multiple sensitivity grid.

Design doc: docs/phase2-comps-lbo-design.md sections 4-6.
"""

from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.assumption import Assumption
from app.models.company import Company
from app.models.financial_period import FinancialPeriod
from app.models.lbo_case import LboCase
from app.models.peer import Peer
from app.models.scenario import Scenario
from app.schemas.lbo import (
    LboCaseResponse,
    LboRunRequest,
    ScheduleYearOut,
    SensitivityResponse,
    SourcesUsesOut,
    ValueCreationBridgeOut,
)
from finance_engine import LboInputs, compute_valuation, run_lbo, run_sensitivity_grid
from finance_engine.constants import (
    COMPS_MIN_PEERS_FOR_VALUATION,
    LBO_DEFAULT_CAPEX_PCT_REVENUE,
    LBO_DEFAULT_CASH_SWEEP_PCT,
    LBO_DEFAULT_HOLD_PERIOD_YEARS,
    LBO_DEFAULT_INTEREST_RATE,
    LBO_DEFAULT_LEVERAGE_MULTIPLE,
    LBO_DEFAULT_MANDATORY_AMORT_PCT,
    LBO_DEFAULT_NWC_PCT_REVENUE_CHANGE,
    LBO_DEFAULT_TAX_RATE,
    LBO_DEFAULT_TRANSACTION_FEES_PCT,
    SENSITIVITY_DEFAULT_SIZE,
    SENSITIVITY_DEFAULT_STEP,
)

router = APIRouter(prefix="/companies", tags=["lbo"])

VALID_CASE_TYPES = {"BASE", "BULL", "BEAR"}


def _latest_fy_period(db: Session, company_id: str) -> Optional[FinancialPeriod]:
    return (
        db.query(FinancialPeriod)
        .filter(FinancialPeriod.company_id == company_id, FinancialPeriod.period_type == "FY")
        .order_by(FinancialPeriod.fiscal_year.desc())
        .first()
    )


def _historical_capex_pct_revenue(db: Session, company_id: str) -> Optional[float]:
    periods = (
        db.query(FinancialPeriod)
        .filter(FinancialPeriod.company_id == company_id, FinancialPeriod.period_type == "FY")
        .all()
    )
    ratios = [
        float(p.capex) / float(p.revenue)
        for p in periods
        if p.capex is not None and p.revenue is not None and p.revenue > 0
    ]
    return (sum(ratios) / len(ratios)) if ratios else None


def _assumption_value(rows: List[Assumption], name: str, default: float) -> float:
    match = next((r for r in rows if r.name == name and r.value_numeric is not None), None)
    return float(match.value_numeric) if match is not None else default


def _resolve_lbo_inputs(
    db: Session, company: Company, scenario: Scenario, entry_ev_override: Optional[float]
) -> LboInputs:
    latest = _latest_fy_period(db, company.id)
    if latest is None or latest.revenue is None or latest.ebitda is None:
        raise HTTPException(
            status_code=422, detail="target has no FY FinancialPeriod with revenue/ebitda -- run /ingest first"
        )
    entry_revenue = float(latest.revenue)
    entry_ebitda = float(latest.ebitda)
    if entry_ebitda <= 0:
        raise HTTPException(status_code=422, detail="target's latest FY EBITDA must be > 0 to run an LBO")

    if entry_ev_override is not None:
        entry_ev = entry_ev_override
    else:
        selected_peers = (
            db.query(Peer).filter(Peer.target_company_id == company.id, Peer.status == "SELECTED").all()
        )
        multiples = [
            (float(p.ev_revenue_multiple), float(p.ev_ebitda_multiple))
            for p in selected_peers
            if p.ev_revenue_multiple is not None and p.ev_ebitda_multiple is not None
        ]
        if len(multiples) < COMPS_MIN_PEERS_FOR_VALUATION:
            raise HTTPException(
                status_code=422,
                detail=(
                    "no entry_ev provided and insufficient SELECTED peers for a comps-derived entry_ev -- "
                    "run /peers/generate + check /valuation, or pass an explicit entry_ev override"
                ),
            )
        valuation = compute_valuation(
            multiples,
            target_revenue=entry_revenue,
            target_ebitda=entry_ebitda,
            target_total_debt=float(latest.total_debt) if latest.total_debt is not None else 0.0,
            target_cash_and_equivalents=(
                float(latest.cash_and_equivalents) if latest.cash_and_equivalents is not None else 0.0
            ),
        )
        entry_ev = valuation.entry_ev

    assumption_rows = db.query(Assumption).filter(Assumption.company_id == company.id).all()
    capex_default = _historical_capex_pct_revenue(db, company.id)
    if capex_default is None:
        capex_default = LBO_DEFAULT_CAPEX_PCT_REVENUE

    return LboInputs(
        entry_ev=entry_ev,
        entry_ebitda=entry_ebitda,
        entry_revenue=entry_revenue,
        revenue_growth_rate=float(scenario.revenue_growth_rate),
        ebitda_margin_delta=float(scenario.ebitda_margin_delta),
        exit_multiple_delta=float(scenario.exit_multiple_delta),
        lbo_leverage_multiple=_assumption_value(assumption_rows, "lbo_leverage_multiple", LBO_DEFAULT_LEVERAGE_MULTIPLE),
        lbo_interest_rate=_assumption_value(assumption_rows, "lbo_interest_rate", LBO_DEFAULT_INTEREST_RATE),
        lbo_cash_sweep_pct=_assumption_value(assumption_rows, "lbo_cash_sweep_pct", LBO_DEFAULT_CASH_SWEEP_PCT),
        lbo_mandatory_amort_pct=_assumption_value(
            assumption_rows, "lbo_mandatory_amort_pct", LBO_DEFAULT_MANDATORY_AMORT_PCT
        ),
        lbo_tax_rate=_assumption_value(assumption_rows, "lbo_tax_rate", LBO_DEFAULT_TAX_RATE),
        lbo_capex_pct_revenue=_assumption_value(assumption_rows, "lbo_capex_pct_revenue", capex_default),
        lbo_nwc_pct_revenue_change=_assumption_value(
            assumption_rows, "lbo_nwc_pct_revenue_change", LBO_DEFAULT_NWC_PCT_REVENUE_CHANGE
        ),
        lbo_transaction_fees_pct=_assumption_value(
            assumption_rows, "lbo_transaction_fees_pct", LBO_DEFAULT_TRANSACTION_FEES_PCT
        ),
        hold_period_years=int(
            _assumption_value(assumption_rows, "lbo_hold_period_years", LBO_DEFAULT_HOLD_PERIOD_YEARS)
        ),
    )


def _get_company_and_scenario(db: Session, company_id: str, case_type: str) -> tuple[Company, Scenario]:
    case_type_upper = case_type.upper()
    if case_type_upper not in VALID_CASE_TYPES:
        raise HTTPException(status_code=422, detail=f"invalid case_type: {case_type}")

    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    scenario = (
        db.query(Scenario)
        .filter(Scenario.company_id == company_id, Scenario.case_type == case_type_upper)
        .first()
    )
    if scenario is None:
        raise HTTPException(
            status_code=422, detail=f"no {case_type_upper} scenario on file -- run /scenarios/generate first"
        )
    return company, scenario


def _response_from_fresh_result(company_id: str, case_type: str, scenario_id: str, result) -> LboCaseResponse:
    return LboCaseResponse(
        company_id=company_id,
        scenario_id=scenario_id,
        case_type=case_type,
        formula_version=result.formula_version,
        inputs=result.inputs,
        sources_uses=SourcesUsesOut(**asdict(result.sources_uses)),
        schedule=[ScheduleYearOut(**asdict(y)) for y in result.schedule],
        entry_ev=result.entry_ev,
        exit_ev=result.exit_ev,
        exit_equity_value=result.exit_equity_value,
        moic=result.moic,
        irr=result.irr,
        entry_leverage=result.entry_leverage,
        exit_leverage=result.exit_leverage,
        entry_multiple=result.entry_multiple,
        exit_multiple=result.exit_multiple,
        value_creation_bridge=ValueCreationBridgeOut(**asdict(result.value_creation_bridge)),
        warnings=result.warnings,
        computed_at=result.computed_at,
    )


def _response_from_stored_case(case: LboCase) -> LboCaseResponse:
    inputs = case.inputs_json
    schedule = case.schedule_json
    entry_multiple = inputs.get("entry_multiple")
    exit_ebitda = schedule[-1]["ebitda"] if schedule else None
    exit_multiple = (float(case.exit_ev) / exit_ebitda) if exit_ebitda else None

    warnings = [
        f"year {y['year']}: ending cash is negative ({y['ending_cash']:,.0f}) -- the case as specified "
        f"would need incremental financing not modeled here (no revolver in this slice)"
        for y in schedule
        if y.get("year", 0) > 0 and y.get("ending_cash") is not None and y["ending_cash"] < 0
    ]

    computed_at = case.computed_at.isoformat() if hasattr(case.computed_at, "isoformat") else str(case.computed_at)

    return LboCaseResponse(
        company_id=case.company_id,
        scenario_id=case.scenario_id,
        case_type=case.scenario.case_type,
        formula_version=case.formula_version,
        inputs=inputs,
        sources_uses=SourcesUsesOut(**case.sources_uses_json),
        schedule=[ScheduleYearOut(**y) for y in schedule],
        entry_ev=float(case.entry_ev),
        exit_ev=float(case.exit_ev),
        exit_equity_value=float(case.exit_equity_value),
        moic=float(case.moic),
        irr=float(case.irr),
        entry_leverage=float(case.entry_leverage),
        exit_leverage=float(case.exit_leverage),
        entry_multiple=entry_multiple,
        exit_multiple=exit_multiple,
        value_creation_bridge=ValueCreationBridgeOut(**case.value_creation_bridge_json),
        warnings=warnings,
        computed_at=computed_at,
    )


@router.post("/{company_id}/lbo/{case_type}/run", response_model=LboCaseResponse)
def run_lbo_case(
    company_id: str, case_type: str, payload: LboRunRequest, db: Session = Depends(get_db)
) -> LboCaseResponse:
    company, scenario = _get_company_and_scenario(db, company_id, case_type)
    inputs = _resolve_lbo_inputs(db, company, scenario, payload.entry_ev)
    result = run_lbo(inputs)

    existing = (
        db.query(LboCase)
        .filter(LboCase.company_id == company_id, LboCase.scenario_id == scenario.id)
        .first()
    )
    if existing is None:
        existing = LboCase(company_id=company_id, scenario_id=scenario.id)
        db.add(existing)

    existing.formula_version = result.formula_version
    existing.inputs_json = result.inputs
    existing.sources_uses_json = asdict(result.sources_uses)
    existing.schedule_json = [asdict(y) for y in result.schedule]
    existing.value_creation_bridge_json = asdict(result.value_creation_bridge)
    existing.entry_ev = result.entry_ev
    existing.exit_ev = result.exit_ev
    existing.exit_equity_value = result.exit_equity_value
    existing.moic = result.moic
    existing.irr = result.irr
    existing.entry_leverage = result.entry_leverage
    existing.exit_leverage = result.exit_leverage
    existing.computed_at = datetime.now(timezone.utc)

    db.commit()

    return _response_from_fresh_result(company_id, scenario.case_type, scenario.id, result)


@router.get("/{company_id}/lbo/{case_type}", response_model=LboCaseResponse)
def get_lbo_case(company_id: str, case_type: str, db: Session = Depends(get_db)) -> LboCaseResponse:
    _, scenario = _get_company_and_scenario(db, company_id, case_type)

    case = (
        db.query(LboCase)
        .filter(LboCase.company_id == company_id, LboCase.scenario_id == scenario.id)
        .first()
    )
    if case is None:
        raise HTTPException(
            status_code=404, detail=f"no LBO case computed yet for {scenario.case_type} -- POST /run first"
        )
    return _response_from_stored_case(case)


@router.get("/{company_id}/lbo/{case_type}/sensitivity", response_model=SensitivityResponse)
def get_lbo_sensitivity(
    company_id: str,
    case_type: str,
    step: float = Query(default=SENSITIVITY_DEFAULT_STEP, gt=0),
    size: int = Query(default=SENSITIVITY_DEFAULT_SIZE, ge=2, le=10),
    db: Session = Depends(get_db),
) -> SensitivityResponse:
    company, scenario = _get_company_and_scenario(db, company_id, case_type)

    # Center the grid on the same resolved inputs as "the main run" (design
    # doc section 6), including any entry_ev override that run used --
    # not a fresh comps-derived entry_ev every time, which would silently
    # diverge from what /run actually used whenever an override was passed.
    existing_case = (
        db.query(LboCase)
        .filter(LboCase.company_id == company_id, LboCase.scenario_id == scenario.id)
        .first()
    )
    if existing_case is not None:
        stored_inputs = dict(existing_case.inputs_json)
        stored_inputs.pop("entry_multiple", None)  # derived field, not an LboInputs constructor arg
        inputs = LboInputs(**stored_inputs)
    else:
        inputs = _resolve_lbo_inputs(db, company, scenario, entry_ev_override=None)

    grid = run_sensitivity_grid(inputs, step=step, size=size)

    return SensitivityResponse(
        company_id=company_id,
        case_type=scenario.case_type,
        entry_multiples=grid["entry_multiples"],
        exit_multiples=grid["exit_multiples"],
        irr_grid=grid["irr_grid"],
        moic_grid=grid["moic_grid"],
    )

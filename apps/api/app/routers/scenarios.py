"""Base/Bull/Bear scenario generation and analyst overrides.

Design doc: docs/phase2-comps-lbo-design.md section 3.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.company import Company
from app.models.financial_period import FinancialPeriod
from app.models.scenario import Scenario
from app.schemas.scenario import ScenarioGenerateResponse, ScenarioPatch, ScenarioRead
from finance_engine.constants import (
    BEAR_EXIT_MULTIPLE_DELTA,
    BEAR_GROWTH_DELTA,
    BEAR_GROWTH_RATE_FLOOR,
    BEAR_MARGIN_DELTA,
    BULL_EXIT_MULTIPLE_DELTA,
    BULL_GROWTH_DELTA,
    BULL_MARGIN_DELTA,
)
from finance_engine.factors import select_fy_periods
from finance_engine.types import FinancialPeriodInput

router = APIRouter(prefix="/companies", tags=["scenarios"])

VALID_CASE_TYPES = {"BASE", "BULL", "BEAR"}


def _compute_base_growth(db: Session, company_id: str) -> float:
    """Reuse Phase 0's own CAGR calculation (finance_engine.factors) rather
    than reimplementing it -- one growth formula in the whole codebase, per
    design doc section 3. Returns 0.0 (flat) if there isn't enough FY
    history yet; that's a best-effort default for scenario generation, not
    an error -- an analyst can always override via PATCH.
    """
    rows = db.query(FinancialPeriod).filter(FinancialPeriod.company_id == company_id).all()
    period_inputs = [
        FinancialPeriodInput(
            fiscal_year=r.fiscal_year,
            period_end_date=r.period_end_date,
            period_type=r.period_type,
            source=r.source,
            revenue=float(r.revenue) if r.revenue is not None else None,
        )
        for r in rows
    ]
    fy_periods = select_fy_periods(period_inputs)
    usable = [p for p in fy_periods if p.revenue is not None]
    if len(usable) < 2:
        return 0.0

    earliest, latest = usable[0], usable[-1]
    n_years = latest.fiscal_year - earliest.fiscal_year
    if n_years <= 0 or earliest.revenue is None or earliest.revenue <= 0:
        return 0.0
    return (float(latest.revenue) / float(earliest.revenue)) ** (1.0 / n_years) - 1.0


@router.post("/{company_id}/scenarios/generate", response_model=ScenarioGenerateResponse)
def generate_scenarios(company_id: str, db: Session = Depends(get_db)) -> ScenarioGenerateResponse:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    base_growth = _compute_base_growth(db, company_id)
    bull_growth = base_growth + BULL_GROWTH_DELTA
    bear_growth = max(base_growth + BEAR_GROWTH_DELTA, BEAR_GROWTH_RATE_FLOOR)

    case_definitions = {
        "BASE": (base_growth, 0.0, 0.0),
        "BULL": (bull_growth, BULL_MARGIN_DELTA, BULL_EXIT_MULTIPLE_DELTA),
        "BEAR": (bear_growth, BEAR_MARGIN_DELTA, BEAR_EXIT_MULTIPLE_DELTA),
    }

    existing_rows = {
        s.case_type: s for s in db.query(Scenario).filter(Scenario.company_id == company_id).all()
    }

    saved: List[Scenario] = []
    for case_type, (growth, margin_delta, exit_delta) in case_definitions.items():
        existing = existing_rows.get(case_type)
        if existing is not None and existing.source == "manual:analyst":
            # Idempotent: regenerating must not clobber an analyst override.
            saved.append(existing)
            continue
        if existing is None:
            existing = Scenario(company_id=company_id, case_type=case_type)
            db.add(existing)
        existing.revenue_growth_rate = growth
        existing.ebitda_margin_delta = margin_delta
        existing.exit_multiple_delta = exit_delta
        existing.source = "default:spec_calibration"
        saved.append(existing)

    db.commit()
    for row in saved:
        db.refresh(row)

    warnings: List[str] = []
    fy_count = (
        db.query(FinancialPeriod)
        .filter(FinancialPeriod.company_id == company_id, FinancialPeriod.period_type == "FY")
        .count()
    )
    if fy_count < 2:
        warnings.append(
            "BASE case growth defaulted to 0.0%: fewer than 2 FY periods available to compute a CAGR"
        )

    return ScenarioGenerateResponse(
        company_id=company_id,
        scenarios=[ScenarioRead.model_validate(s) for s in saved],
        warnings=warnings,
    )


@router.patch("/{company_id}/scenarios/{case_type}", response_model=ScenarioRead)
def patch_scenario(
    company_id: str, case_type: str, payload: ScenarioPatch, db: Session = Depends(get_db)
) -> Scenario:
    case_type_upper = case_type.upper()
    if case_type_upper not in VALID_CASE_TYPES:
        raise HTTPException(status_code=422, detail=f"invalid case_type: {case_type}")

    scenario = (
        db.query(Scenario)
        .filter(Scenario.company_id == company_id, Scenario.case_type == case_type_upper)
        .first()
    )
    if scenario is None:
        raise HTTPException(status_code=404, detail="scenario not found -- run /scenarios/generate first")

    if payload.revenue_growth_rate is not None:
        scenario.revenue_growth_rate = payload.revenue_growth_rate
    if payload.ebitda_margin_delta is not None:
        scenario.ebitda_margin_delta = payload.ebitda_margin_delta
    if payload.exit_multiple_delta is not None:
        scenario.exit_multiple_delta = payload.exit_multiple_delta
    if payload.notes is not None:
        scenario.notes = payload.notes
    scenario.source = "manual:analyst"

    db.commit()
    db.refresh(scenario)
    return scenario

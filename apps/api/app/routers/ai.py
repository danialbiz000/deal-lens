"""Memo generation + IC simulation endpoints.

These POST endpoints are the only two in the whole codebase that make
outbound network calls to a third-party API (design doc section 8). Both
are documented plainly: a Claude API error/timeout is surfaced as 503 with
a clear message, never a raw stack trace. Both also carry the two stacked
rate-limit dimensions from design doc section 12 (per-company cost control
+ per-IP abuse backstop) -- the most expensive actions in the whole app.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.ai.bundle import build_source_bundle
from app.ai.client import ClaudeApiError, ClaudeClient, get_claude_client
from app.ai.ic_simulation import run_ic_simulation
from app.ai.memo import generate_memo
from app.ai.prompts.memo_sections import PROMPT_VERSION as MEMO_PROMPT_VERSION
from app.config import settings
from app.db import get_db
from app.models.company import Company
from app.models.ic_simulation import IcSimulation
from app.models.lbo_case import LboCase
from app.models.memo import Memo
from app.models.scenario import Scenario
from app.rate_limit import SCOPE_AI_PER_COMPANY, SCOPE_AI_PER_IP, company_id_key, limiter
from app.schemas.ic_simulation import IcSimulationResponse, IcSimulationSummary
from app.schemas.memo import MemoResponse, MemoSummary
from finance_engine.ic_gate import BearCaseInput, BearCaseYear

router = APIRouter(prefix="/companies", tags=["ai"])


def _next_version(db: Session, model, company_id: str) -> int:
    existing = (
        db.query(model).filter(model.company_id == company_id).order_by(model.version.desc()).first()
    )
    return (existing.version + 1) if existing else 1


def _get_lbo_case(db: Session, company_id: str, case_type: str) -> Optional[LboCase]:
    scenario = (
        db.query(Scenario)
        .filter(Scenario.company_id == company_id, Scenario.case_type == case_type)
        .first()
    )
    if scenario is None:
        return None
    return (
        db.query(LboCase)
        .filter(LboCase.company_id == company_id, LboCase.scenario_id == scenario.id)
        .first()
    )


def _check_common_prerequisites(bundle: dict, require_lbo_cases: List[str]) -> None:
    if bundle["screening"] is None:
        raise HTTPException(status_code=422, detail="screening score not computable -- run /ingest first")
    if bundle["valuation"] is None:
        raise HTTPException(
            status_code=422,
            detail="valuation requires >=2 SELECTED peers -- run /peers/generate then check /valuation",
        )
    missing = [ct for ct in require_lbo_cases if ct not in bundle["lbo"]]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"LBO case(s) missing: {', '.join(missing)} -- run POST /lbo/{{case_type}}/run first",
        )


def _memo_to_response(memo: Memo) -> MemoResponse:
    return MemoResponse(
        id=memo.id,
        company_id=memo.company_id,
        version=memo.version,
        prompt_version=memo.prompt_version,
        model=memo.model,
        sections=memo.sections_json,
        validation_report=memo.validation_report_json,
        generated_at=memo.generated_at,
    )


def _ic_simulation_to_response(sim: IcSimulation) -> IcSimulationResponse:
    return IcSimulationResponse(
        id=sim.id,
        company_id=sim.company_id,
        version=sim.version,
        model=sim.model,
        transcript=sim.transcript_json,
        llm_recommendation=sim.llm_recommendation,
        recommendation=sim.recommendation,
        override_fired=sim.override_fired,
        override_reason=sim.override_reason,
        key_strengths=sim.key_strengths_json,
        key_risks=sim.key_risks_json,
        unanswered_dd=sim.unanswered_dd_json,
        generated_at=sim.generated_at,
    )


def _bear_case_gate_input(bear_case: LboCase) -> BearCaseInput:
    years = [
        BearCaseYear(year=y["year"], ebitda=y["ebitda"], interest=y.get("interest"))
        for y in bear_case.schedule_json
    ]
    return BearCaseInput(
        irr=float(bear_case.irr),
        moic=float(bear_case.moic),
        exit_leverage=float(bear_case.exit_leverage),
        schedule=years,
    )


@router.post("/{company_id}/memo", response_model=MemoResponse)
@limiter.shared_limit(lambda: settings.rate_limit_ai_per_ip, scope=SCOPE_AI_PER_IP, error_message=SCOPE_AI_PER_IP)
@limiter.limit(lambda: settings.rate_limit_ai_per_company, key_func=company_id_key, error_message=SCOPE_AI_PER_COMPANY)
def create_memo(
    request: Request,
    company_id: str,
    db: Session = Depends(get_db),
    client: ClaudeClient = Depends(get_claude_client),
) -> MemoResponse:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    bundle = build_source_bundle(company_id, db)
    _check_common_prerequisites(bundle, require_lbo_cases=["base"])

    try:
        result = generate_memo(bundle, client)
    except ClaudeApiError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    version = _next_version(db, Memo, company_id)
    memo = Memo(
        company_id=company_id,
        version=version,
        prompt_version=MEMO_PROMPT_VERSION,
        model=getattr(client, "model_name", "unknown"),
        source_bundle_json=bundle,
        sections_json=result["sections"],
        validation_report_json=result["validation_report"],
        generated_at=datetime.now(timezone.utc),
    )
    db.add(memo)
    db.commit()
    db.refresh(memo)

    return _memo_to_response(memo)


@router.get("/{company_id}/memo", response_model=List[MemoSummary])
def list_memos(company_id: str, db: Session = Depends(get_db)) -> List[MemoSummary]:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    memos = db.query(Memo).filter(Memo.company_id == company_id).order_by(Memo.version.desc()).all()
    return [
        MemoSummary(
            id=m.id,
            version=m.version,
            generated_at=m.generated_at,
            validation_status=m.validation_report_json.get("status", "unknown"),
        )
        for m in memos
    ]


@router.get("/{company_id}/memo/{version}", response_model=MemoResponse)
def get_memo(company_id: str, version: int, db: Session = Depends(get_db)) -> MemoResponse:
    memo = db.query(Memo).filter(Memo.company_id == company_id, Memo.version == version).first()
    if memo is None:
        raise HTTPException(status_code=404, detail="memo version not found")
    return _memo_to_response(memo)


@router.post("/{company_id}/ic-simulation", response_model=IcSimulationResponse)
@limiter.shared_limit(lambda: settings.rate_limit_ai_per_ip, scope=SCOPE_AI_PER_IP, error_message=SCOPE_AI_PER_IP)
@limiter.limit(lambda: settings.rate_limit_ai_per_company, key_func=company_id_key, error_message=SCOPE_AI_PER_COMPANY)
def create_ic_simulation(
    request: Request,
    company_id: str,
    db: Session = Depends(get_db),
    client: ClaudeClient = Depends(get_claude_client),
) -> IcSimulationResponse:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    bundle = build_source_bundle(company_id, db)
    _check_common_prerequisites(bundle, require_lbo_cases=["base", "bull", "bear"])

    bear_case_row = _get_lbo_case(db, company_id, "BEAR")
    gate_input = _bear_case_gate_input(bear_case_row)  # non-None: prerequisites already checked "bear" is present

    try:
        result = run_ic_simulation(bundle, gate_input, client)
    except ClaudeApiError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    version = _next_version(db, IcSimulation, company_id)
    sim = IcSimulation(
        company_id=company_id,
        version=version,
        model=getattr(client, "model_name", "unknown"),
        source_bundle_json=bundle,
        transcript_json=result["transcript"],
        llm_recommendation=result["llm_recommendation"],
        recommendation=result["recommendation"],
        override_fired=result["override_fired"],
        override_reason=result["override_reason"],
        key_strengths_json=result["key_strengths"],
        key_risks_json=result["key_risks"],
        unanswered_dd_json=result["unanswered_dd"],
        generated_at=datetime.now(timezone.utc),
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)

    return _ic_simulation_to_response(sim)


@router.get("/{company_id}/ic-simulation", response_model=List[IcSimulationSummary])
def list_ic_simulations(company_id: str, db: Session = Depends(get_db)) -> List[IcSimulationSummary]:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    sims = (
        db.query(IcSimulation)
        .filter(IcSimulation.company_id == company_id)
        .order_by(IcSimulation.version.desc())
        .all()
    )
    return [
        IcSimulationSummary(
            id=s.id, version=s.version, generated_at=s.generated_at,
            recommendation=s.recommendation, override_fired=s.override_fired,
        )
        for s in sims
    ]


@router.get("/{company_id}/ic-simulation/{version}", response_model=IcSimulationResponse)
def get_ic_simulation(company_id: str, version: int, db: Session = Depends(get_db)) -> IcSimulationResponse:
    sim = (
        db.query(IcSimulation)
        .filter(IcSimulation.company_id == company_id, IcSimulation.version == version)
        .first()
    )
    if sim is None:
        raise HTTPException(status_code=404, detail="ic-simulation version not found")
    return _ic_simulation_to_response(sim)

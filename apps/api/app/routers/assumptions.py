from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.assumption import Assumption
from app.models.company import Company
from app.schemas.assumption import AssumptionRead, AssumptionUpsert

router = APIRouter(prefix="/companies", tags=["assumptions"])


@router.post("/{company_id}/assumptions", response_model=AssumptionRead)
def upsert_assumption(
    company_id: str, payload: AssumptionUpsert, db: Session = Depends(get_db)
) -> Assumption:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    existing = (
        db.query(Assumption)
        .filter(Assumption.company_id == company_id, Assumption.name == payload.name)
        .first()
    )
    if existing is None:
        existing = Assumption(company_id=company_id, name=payload.name)
        db.add(existing)

    existing.value_numeric = payload.value_numeric
    existing.value_text = payload.value_text
    existing.unit = payload.unit
    existing.source = payload.source
    existing.confidence = payload.confidence
    existing.notes = payload.notes

    db.commit()
    db.refresh(existing)
    return existing


@router.get("/{company_id}/assumptions", response_model=List[AssumptionRead])
def list_assumptions(company_id: str, db: Session = Depends(get_db)) -> List[Assumption]:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    return (
        db.query(Assumption)
        .filter(Assumption.company_id == company_id)
        .order_by(Assumption.name)
        .all()
    )

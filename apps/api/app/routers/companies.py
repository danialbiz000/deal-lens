from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.company import Company
from app.models.financial_period import FinancialPeriod
from app.schemas.company import CompanyCreate, CompanyDetail, CompanyRead
from app.schemas.financial_period import FinancialPeriodRead

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyRead, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> Company:
    ticker = payload.ticker.upper()

    conflict_filters = [Company.ticker == ticker]
    if payload.cik:
        conflict_filters.append(Company.cik == payload.cik)
    existing = db.query(Company).filter(or_(*conflict_filters)).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="a company with this ticker or cik already exists")

    company = Company(
        ticker=ticker,
        cik=payload.cik,
        name=payload.name,
        sector=payload.sector,
        industry=payload.industry,
        country=payload.country,
        reporting_currency=payload.reporting_currency.upper(),
        description=payload.description,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("", response_model=list[CompanyRead])
def list_companies(db: Session = Depends(get_db)) -> list[Company]:
    return db.query(Company).order_by(Company.ticker).all()


@router.get("/{company_id}", response_model=CompanyDetail)
def get_company(company_id: str, db: Session = Depends(get_db)) -> CompanyDetail:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    latest_period = (
        db.query(FinancialPeriod)
        .filter(FinancialPeriod.company_id == company_id, FinancialPeriod.period_type == "FY")
        .order_by(FinancialPeriod.fiscal_year.desc())
        .first()
    )

    detail = CompanyDetail.model_validate(company)
    detail.latest_financial_period = (
        FinancialPeriodRead.model_validate(latest_period) if latest_period is not None else None
    )
    return detail

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class LboRunRequest(BaseModel):
    entry_ev: Optional[float] = None  # override the comps-derived entry_ev if provided


class SourcesUsesOut(BaseModel):
    new_debt: float
    sponsor_equity: float
    purchase_ev: float
    fees: float
    reconciles: bool


class ScheduleYearOut(BaseModel):
    year: int
    revenue: float
    ebitda: float
    beginning_debt: float
    ending_debt: float
    beginning_cash: float
    ending_cash: float
    margin: Optional[float] = None
    capex: Optional[float] = None
    nwc_investment: Optional[float] = None
    interest: Optional[float] = None
    taxes: Optional[float] = None
    cfads: Optional[float] = None
    mandatory_amort: Optional[float] = None
    sweep: Optional[float] = None


class ValueCreationBridgeOut(BaseModel):
    entry_equity: float
    ebitda_growth: float
    margin_expansion: float
    debt_paydown: float
    multiple_expansion: float
    transaction_fees: float
    total: float
    exit_multiple_dependent: bool
    value_destructive: bool


class LboCaseResponse(BaseModel):
    company_id: str
    scenario_id: str
    case_type: str
    formula_version: str
    inputs: Dict[str, Any]
    sources_uses: SourcesUsesOut
    schedule: List[ScheduleYearOut]
    entry_ev: float
    exit_ev: float
    exit_equity_value: float
    moic: float
    irr: float
    entry_leverage: float
    exit_leverage: float
    entry_multiple: float
    exit_multiple: float
    value_creation_bridge: ValueCreationBridgeOut
    warnings: List[str]
    computed_at: str


class SensitivityResponse(BaseModel):
    company_id: str
    case_type: str
    entry_multiples: List[float]
    exit_multiples: List[float]
    irr_grid: List[List[float]]
    moic_grid: List[List[float]]

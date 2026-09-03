from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DebtTrancheIn(BaseModel):
    """One tranche of the debt stack (v1.0 debt sculpting). Omitting
    `debt_tranches` entirely on LboRunRequest preserves the MVP's single
    blended-tranche behavior -- this is purely opt-in.
    """

    name: str
    leverage_multiple: float = Field(gt=0, description="this tranche's own share of entry EBITDA")
    interest_rate: float = Field(ge=0)
    mandatory_amort_pct: float = Field(default=0.0, ge=0, le=1)
    priority: int = Field(default=1, description="lower = swept first with excess cash; does not affect interest/mandatory amort")


class LboRunRequest(BaseModel):
    entry_ev: Optional[float] = None  # override the comps-derived entry_ev if provided
    debt_tranches: Optional[List[DebtTrancheIn]] = None  # opt into multi-tranche debt sculpting


class SourcesUsesOut(BaseModel):
    new_debt: float
    sponsor_equity: float
    purchase_ev: float
    fees: float
    reconciles: bool


class TrancheYearOut(BaseModel):
    name: str
    beginning_balance: float
    ending_balance: float
    interest: Optional[float] = None
    mandatory_amort: Optional[float] = None
    sweep: Optional[float] = None


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
    tranches: Optional[List[TrancheYearOut]] = None


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

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ScenarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    case_type: str  # BASE | BULL | BEAR
    revenue_growth_rate: float
    ebitda_margin_delta: float
    exit_multiple_delta: float
    source: str  # default:spec_calibration | manual:analyst
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ScenarioPatch(BaseModel):
    revenue_growth_rate: Optional[float] = None
    ebitda_margin_delta: Optional[float] = None
    exit_multiple_delta: Optional[float] = None
    notes: Optional[str] = None


class ScenarioGenerateResponse(BaseModel):
    company_id: str
    scenarios: List[ScenarioRead]
    warnings: List[str] = []

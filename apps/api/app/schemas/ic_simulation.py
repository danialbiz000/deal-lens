from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class IcRoleOutput(BaseModel):
    role: str
    output: Dict[str, Any]
    validation_report: Dict[str, Any]


class IcSimulationResponse(BaseModel):
    id: str
    company_id: str
    version: int
    model: str
    transcript: List[IcRoleOutput]
    llm_recommendation: str
    recommendation: str
    override_fired: bool
    override_reason: Optional[str] = None
    key_strengths: List[str]
    key_risks: List[str]
    unanswered_dd: List[str]
    generated_at: datetime


class IcSimulationSummary(BaseModel):
    id: str
    version: int
    generated_at: datetime
    recommendation: str
    override_fired: bool

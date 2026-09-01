from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Assumption keys that feed the screening score's 4 placeholder factors
# (design doc section 3.1/3.3) and therefore must be a 0-100 score.
SCORE_ASSUMPTION_NAMES = {
    "business_quality_score",
    "market_structure_score",
    "exit_optionality_score",
    "management_execution_score",
}


class AssumptionUpsert(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    value_numeric: Optional[float] = None
    value_text: Optional[str] = Field(default=None, max_length=500)
    unit: Optional[str] = Field(default=None, max_length=30)
    source: str = Field(..., min_length=1, max_length=100)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _validate_score_range(self) -> "AssumptionUpsert":
        if self.name in SCORE_ASSUMPTION_NAMES and self.value_numeric is not None:
            if not (0 <= self.value_numeric <= 100):
                raise ValueError(
                    f"value_numeric for '{self.name}' must be in [0, 100] (score_0_100 unit), "
                    f"got {self.value_numeric}"
                )
        return self


class AssumptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    name: str
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    source: str
    confidence: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

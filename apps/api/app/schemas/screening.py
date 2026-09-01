from typing import List

from pydantic import BaseModel


class ScreeningFactorOut(BaseModel):
    name: str
    weight: float
    normalized_score: float
    source: str  # "computed" | "default" | "assumption"
    contribution: float
    notes: str


class ScreeningScoreResponse(BaseModel):
    company_id: str
    formula_version: str
    score: float
    factors: List[ScreeningFactorOut]
    warnings: List[str]
    computed_at: str

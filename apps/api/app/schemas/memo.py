from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel


class MemoSectionOut(BaseModel):
    section_key: str
    title: str
    content: str


class MemoValidationReportOut(BaseModel):
    total_citations: int
    invalid_citations: List[str]
    mismatched_citations: List[str] = []
    uncited_numbers: List[str]
    status: str  # "ok" | "warnings"
    per_section: List[Dict[str, Any]] = []


class MemoResponse(BaseModel):
    id: str
    company_id: str
    version: int
    prompt_version: str
    model: str
    sections: List[MemoSectionOut]
    validation_report: MemoValidationReportOut
    generated_at: datetime


class MemoSummary(BaseModel):
    id: str
    version: int
    generated_at: datetime
    validation_status: str

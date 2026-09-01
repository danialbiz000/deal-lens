from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PeerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target_company_id: str
    peer_company_id: str
    peer_ticker: Optional[str] = None  # enriched at the API layer for convenience
    peer_name: Optional[str] = None
    status: str  # CANDIDATE | SELECTED | REJECTED
    reason_code: Optional[str] = None
    reason_notes: Optional[str] = None
    similarity_score: Optional[float] = None
    ev_revenue_multiple: Optional[float] = None
    ev_ebitda_multiple: Optional[float] = None
    source: str
    computed_at: datetime
    created_at: datetime
    updated_at: datetime


class PeerPatch(BaseModel):
    status: str = Field(..., pattern="^(CANDIDATE|SELECTED|REJECTED)$")
    reason_notes: str = Field(..., min_length=1, description="required when an analyst overrides status")


class PeerGenerateResponse(BaseModel):
    target_company_id: str
    peers: List[PeerRead]
    selected_count: int
    warnings: List[str] = []


class ValuationResponse(BaseModel):
    company_id: str
    peer_count: int
    median_ev_revenue: float
    q1_ev_revenue: float
    q3_ev_revenue: float
    median_ev_ebitda: float
    q1_ev_ebitda: float
    q3_ev_ebitda: float
    implied_ev_from_revenue: float
    implied_ev_from_ebitda: float
    entry_ev: float
    entry_net_debt: float
    entry_equity_value: float
    computed_at: str

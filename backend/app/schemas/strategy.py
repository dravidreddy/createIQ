"""
Strategy Schemas (V4)

Pydantic schemas for the growth/series planning layer.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class StrategyPlanCreate(BaseModel):
    title: str = Field(..., min_length=1)
    focus_niche: str = Field(..., min_length=1)

class StrategyPlanResponse(BaseModel):
    id: str
    user_id: str
    title: str
    focus_niche: str
    series_plan: List[Dict[str, Any]]
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StrategyPlanInstantiateRequest(BaseModel):
    # Only instantiate selected indices from the series plan
    series_indices: Optional[List[int]] = None

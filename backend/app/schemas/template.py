"""
Template Schemas (V4)

Pydantic schemas for the structured content templates.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ContentTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    structure_json: Dict[str, Any]
    prompt_injection: str

class ContentTemplateResponse(BaseModel):
    id: str
    name: str
    type: str # system | user
    user_id: Optional[str] = None
    description: Optional[str] = None
    structure_json: Dict[str, Any]
    prompt_injection: str
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

"""
Version Schemas (V4)

Pydantic schemas for the versioned pipeline outputs.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class ProjectVersionResponse(BaseModel):
    """Schema for ProjectVersion API responses."""
    id: str
    project_id: str
    version_number: int
    is_saved: bool
    
    # Pipeline contents
    ideas: Optional[List[Dict[str, Any]]] = None
    selected_idea: Optional[Dict[str, Any]] = None
    hook: Optional[Dict[str, Any]] = None
    script: Optional[str] = None
    screenplay_guidance: Optional[Dict[str, Any]] = None
    
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

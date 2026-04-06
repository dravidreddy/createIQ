"""
Project Schemas (V4)

Pydantic schemas for the hierarchical project container.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.models.project import ProjectStatus, CollaboratorRole

class CollaboratorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str
    role: CollaboratorRole

class CollaboratorResponse(BaseModel):
    user_id: str
    role: CollaboratorRole
    added_at: datetime

class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., min_length=1, max_length=255)
    topic: str = Field(..., min_length=1, max_length=500)
    niche: Optional[str] = None
    parent_project_id: Optional[str] = None
    strategy_plan_id: Optional[str] = None
    platform: Optional[str] = None
    goal: Optional[str] = None

class ProjectUpdate(BaseModel):
    """Schema for updating project."""
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    topic: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[ProjectStatus] = None
    platform: Optional[str] = None
    goal: Optional[str] = None

class ProjectResponse(BaseModel):
    """Schema for project API responses."""
    id: str          # MongoDB ObjectId string
    user_id: str     # MongoDB ObjectId string
    title: str
    topic: str
    niche: Optional[str] = None
    status: ProjectStatus
    
    parent_project_id: Optional[str] = None
    strategy_plan_id: Optional[str] = None
    platform: Optional[str] = None
    goal: Optional[str] = None
    
    collaborators: List[CollaboratorResponse] = []

    # Execution metadata
    # Execution metadata
    current_agent: Optional[str] = None
    error_message: Optional[str] = None
    completed_stages: List[str] = []

    # Timestamps
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ProjectList(BaseModel):
    """Schema for paginated project list."""
    projects: List[ProjectResponse]
    total: int
    page: int
    per_page: int

"""
Project Document — MongoDB / Beanie

Hierarchical content project.  Lives inside a workspace.
Supports collaborators, parent/child projects, and strategy linkage.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from beanie import Document, Indexed
from pymongo import IndexModel, ASCENDING
from pydantic import BaseModel, Field


# ─── Enums ──────────────────────────────────────────────────────

class ProjectStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    FAILED = "failed"


class ProjectType(str, Enum):
    SERIES = "series"
    VIDEO = "video"


class CollaboratorRole(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


# ─── Sub-documents ──────────────────────────────────────────────

class Collaborator(BaseModel):
    user_id: str
    role: CollaboratorRole = CollaboratorRole.EDITOR
    added_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Document ───────────────────────────────────────────────────

class Project(Document):
    """Content project — the central work unit."""

    user_id: str  # creator / owner ID
    workspace_id: Optional[str] = None  # ref → workspaces

    title: str
    topic: str
    niche: Optional[str] = None
    platform: Optional[str] = None  # youtube | tiktok | instagram | ...
    goal: Optional[str] = None

    status: ProjectStatus = ProjectStatus.DRAFT
    project_type: ProjectType = ProjectType.VIDEO

    # Hierarchy
    parent_project_id: Optional[str] = None
    requires_continuity: bool = False
    strategy_plan_id: Optional[str] = None

    # Collaboration
    collaborators: List[Collaborator] = []

    # Execution state (legacy — new code should use content_blocks)
    selected_idea: Optional[dict] = None
    current_agent: Optional[str] = None
    error_message: Optional[str] = None
    completed_stages: List[str] = []

    # Soft delete
    is_deleted: bool = False

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Settings:
        name = "projects"
        use_state_management = True
        indexes = [
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("user_id", ASCENDING), ("is_deleted", ASCENDING)]),
            IndexModel([("user_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("workspace_id", ASCENDING)]),
            IndexModel([("created_at", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("parent_project_id", ASCENDING)]),
            IndexModel([("strategy_plan_id", ASCENDING)]),
        ]

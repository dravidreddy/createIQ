"""
Project Version — DEPRECATED

Legacy versioning model.  New code should use ContentBlock + ContentVersion.
Kept for backward compatibility with existing version service routes.
"""

from app.utils.datetime_utils import utc_now
from datetime import datetime
from typing import Optional, List, Dict, Any

from beanie import Document, Indexed
from pymongo import IndexModel, ASCENDING
from pydantic import Field


class ProjectVersion(Document):
    """DEPRECATED — Use ContentBlock + ContentVersion instead."""

    project_id: Indexed(str)  # type: ignore[valid-type]
    version_number: int = 1

    is_saved: bool = False
    expires_at: Optional[datetime] = None  # TTL for unsaved versions

    # Legacy pipeline content fields
    ideas: Optional[List[Dict[str, Any]]] = None
    selected_idea: Optional[Dict[str, Any]] = None
    hook: Optional[Dict[str, Any]] = None
    script: Optional[str] = None
    screenplay_guidance: Optional[Dict[str, Any]] = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "project_versions"
        use_state_management = True
        indexes = [
            IndexModel([("project_id", ASCENDING)]),
            IndexModel(
                [("project_id", ASCENDING), ("version_number", ASCENDING)],
                unique=True,
            ),
        ]

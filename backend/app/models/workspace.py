"""
Workspace Document — MongoDB / Beanie

Multi-tenant workspace container.  Users belong to one or more workspaces.
Projects live inside workspaces.
"""

from app.utils.datetime_utils import utc_now
from datetime import datetime
from typing import List, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field


class WorkspaceMember(BaseModel):
    """Embedded sub-document: a user's role within a workspace."""

    user_id: str
    role: str = "editor"  # owner | editor | viewer
    added_at: datetime = Field(default_factory=utc_now)


class Workspace(Document):
    """Workspace — top-level organisational container."""

    name: str
    owner_id: Indexed(str)  # type: ignore[valid-type]

    members: List[WorkspaceMember] = []

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "workspaces"
        use_state_management = True
        indexes = [
            "owner_id",
            "members.user_id",
        ]

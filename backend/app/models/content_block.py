"""
Content Block Document — MongoDB / Beanie

Block-based content entities (Notion-style).  Each block has a type and
points to its current active version in the `content_versions` collection.
Content is NEVER stored directly here — always via versions.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document, Indexed
from pymongo import IndexModel, ASCENDING
from pydantic import Field


class BlockType(str, Enum):
    IDEA = "idea"
    HOOK = "hook"
    SCRIPT = "script"
    OUTLINE = "outline"
    ANALYSIS = "analysis"
    STRATEGY = "strategy"


class ContentBlock(Document):
    """A logical content unit within a project."""

    project_id: Indexed(str)  # type: ignore[valid-type]
    type: BlockType

    # Points to the active ContentVersion._id
    current_version_id: Optional[str] = None

    created_by: str  # user_id
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "content_blocks"
        use_state_management = True
        indexes = [
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("project_id", ASCENDING), ("type", ASCENDING)]),
            IndexModel([("created_by", ASCENDING)]),
        ]

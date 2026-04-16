"""
Content Version Document — MongoDB / Beanie

Append-only version history for content blocks.
Rules:
  - NEVER overwrite an existing version.
  - ALWAYS create a new version document.
  - `is_active` marks the current head.
  - `parent_version_id` supports future branching.
"""

from app.utils.datetime_utils import utc_now
from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pymongo import IndexModel, ASCENDING
from pydantic import Field


class ContentVersion(Document):
    """Immutable snapshot of a content block's content at a point in time."""

    block_id: Indexed(str)  # type: ignore[valid-type]  — ref → content_blocks
    version_number: int = 1

    # The actual content payload — schema varies by block type
    content: dict = Field(default_factory=dict)

    created_by: str  # user_id
    created_at: datetime = Field(default_factory=utc_now)

    is_active: bool = True

    # For future branching (e.g. "try a different hook" without losing original)
    parent_version_id: Optional[str] = None

    class Settings:
        name = "content_versions"
        use_state_management = True
        indexes = [
            IndexModel([("block_id", ASCENDING)]),
            IndexModel(
                [("block_id", ASCENDING), ("version_number", ASCENDING)],
                unique=True,
            ),
            IndexModel([("block_id", ASCENDING), ("is_active", ASCENDING)]),
        ]

"""
Conversation Document — MongoDB / Beanie

AI chat sessions scoped to a project and user.
"""

from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pymongo import IndexModel, ASCENDING
from pydantic import Field


class Conversation(Document):
    """An AI conversation session."""

    project_id: Indexed(str)  # type: ignore[valid-type]
    user_id: Indexed(str)  # type: ignore[valid-type]

    title: Optional[str] = None  # auto-generated or user-set

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "conversations"
        use_state_management = True
        indexes = [
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("user_id", ASCENDING)]),
        ]

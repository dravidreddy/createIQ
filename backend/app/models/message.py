"""
Message Document — MongoDB / Beanie

Individual messages within a conversation (user ↔ assistant).
"""

from app.utils.datetime_utils import utc_now
from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pymongo import IndexModel, ASCENDING
from pydantic import Field


class Message(Document):
    """A single message in a conversation."""

    conversation_id: Indexed(str)  # type: ignore[valid-type]

    role: str = "user"  # user | assistant | system
    content: str = ""
    metadata: dict = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "messages"
        use_state_management = True
        indexes = [
            IndexModel([("conversation_id", ASCENDING)]),
            IndexModel([("conversation_id", ASCENDING), ("created_at", ASCENDING)]),
        ]

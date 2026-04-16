"""
Agent Session — DEPRECATED

Legacy model kept for backward compatibility with existing `agent_sessions` collection.
New code should use AIGeneration instead.
"""

from app.utils.datetime_utils import utc_now
from datetime import datetime
from typing import Optional, List

from beanie import Document, Indexed
from pymongo import IndexModel, ASCENDING
from pydantic import Field


class AgentSession(Document):
    """DEPRECATED — Use AIGeneration instead."""

    project_id: Indexed(str)  # type: ignore[valid-type]
    agent_name: str = ""
    status: str = "pending"  # pending | running | completed | failed

    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    execution_logs: List[dict] = Field(default_factory=list)

    input_tokens: int = 0
    output_tokens: int = 0
    execution_time_seconds: Optional[float] = None
    error_message: Optional[str] = None

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "agent_sessions"
        use_state_management = True
        indexes = [
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("project_id", ASCENDING), ("agent_name", ASCENDING)]),
        ]

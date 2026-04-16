"""
Project Agent State Document — MongoDB / Beanie

Versioned JSON state blob for the V3.3 adaptive engine.
Uses optimistic locking (version field) for concurrent writes.
"""

from app.utils.datetime_utils import utc_now
from datetime import datetime
from typing import Optional, Set

from beanie import Document, Indexed
from pydantic import Field


class ProjectAgentState(Document):
    """Per-project agent execution state with optimistic locking."""

    project_id: Indexed(str, unique=True)  # type: ignore[valid-type]

    version: int = 0
    state: dict = Field(default_factory=dict)

    compressed_until: Optional[datetime] = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Allowed top-level keys in the state dict (for validation)
    ALLOWED_DOMAINS: Set[str] = {
        "execution_state",
        "research_context",
        "user_preferences",
        "generation_history",
        "evaluation_results",
    }

    class Settings:
        name = "project_agent_states"
        use_state_management = True

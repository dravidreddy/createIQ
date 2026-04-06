"""
AI Generation Document — MongoDB / Beanie

Tracks every AI generation request: prompt, response, model, cost, latency.
Replaces the legacy `agent_sessions` collection with a cleaner, cost-aware design.
"""

from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pymongo import IndexModel, ASCENDING
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Sub-document for token accounting."""
    input: int = 0
    output: int = 0
    total: int = 0


class AIGeneration(Document):
    """Record of a single AI generation call."""

    project_id: Indexed(str)  # type: ignore[valid-type]
    block_id: Optional[str] = None  # ref → content_blocks (nullable for free-form generations)

    agent_name: str = ""  # research_script | idea_discovery | ...
    prompt: str = ""
    response: dict = Field(default_factory=dict)

    model: str = ""  # e.g. "llama-3.1-8b-instant"
    tokens_used: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: int = 0
    cost_cents: float = 0.0

    created_by: str = ""  # user_id
    trace_id: Optional[str] = None  # observability linkage
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "ai_generations"
        use_state_management = True
        indexes = [
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("block_id", ASCENDING)]),
            IndexModel([("created_by", ASCENDING)]),
            IndexModel([("created_at", ASCENDING)]),
            IndexModel([("agent_name", ASCENDING)]),
            IndexModel([("trace_id", ASCENDING)]),
        ]

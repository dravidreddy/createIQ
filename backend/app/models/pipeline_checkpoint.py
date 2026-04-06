"""
PipelineCheckpoint Beanie Document

MongoDB storage for LangGraph checkpoints. Enables the pipeline to
survive server restarts and resume from any interrupt point.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed
from pymongo import IndexModel, ASCENDING
from pydantic import Field, field_validator


class PipelineCheckpoint(Document):
    """LangGraph checkpoint persisted to MongoDB."""

    thread_id: Indexed(str)
    checkpoint_id: Optional[str] = Field(default="", validate_default=True)
    parent_checkpoint_id: Optional[str] = None
    checkpoint_data: Any = {}  # Can be dict or compressed bytes
    metadata: Dict[str, Any] = {}
    is_compressed: bool = False
    trace_id: Optional[str] = None  # observability linkage
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("checkpoint_id", "parent_checkpoint_id", mode="before")
    @classmethod
    def validate_ids(cls, v):
        if v is None:
            return ""
        return str(v)

    class Settings:
        name = "pipeline_checkpoints"
        indexes = [
            IndexModel(
                [("thread_id", ASCENDING), ("checkpoint_id", ASCENDING)],
                unique=True,
            ),
            # TTL index: automatically delete checkpoints older than 7 days
            IndexModel(
                [("created_at", ASCENDING)],
                expireAfterSeconds=7 * 86400,
            ),
            IndexModel([("trace_id", ASCENDING)]),
        ]

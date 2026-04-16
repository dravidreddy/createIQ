"""
Project Artifact — DEPRECATED

This model is kept as a stub for backward compatibility.
New code should use ContentBlock + ContentVersion instead.
"""

from app.utils.datetime_utils import utc_now
from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pymongo import IndexModel, ASCENDING
from pydantic import Field


class ProjectArtifact(Document):
    """DEPRECATED — Use ContentBlock + ContentVersion instead."""

    project_id: Indexed(str)  # type: ignore[valid-type]
    artifact_type: str = ""
    content: dict = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "project_artifacts"
        use_state_management = True
        indexes = [
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("artifact_type", ASCENDING)]),
            IndexModel([("project_id", ASCENDING), ("artifact_type", ASCENDING)]),
        ]

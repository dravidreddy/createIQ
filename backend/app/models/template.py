"""
Content Template Document — MongoDB / Beanie

Reusable content structure templates (system-provided or user-created).
"""

from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class ContentTemplate(Document):
    """A reusable content structure template."""

    name: str
    type: str = "system"  # system | user
    user_id: Optional[str] = None  # null for system templates

    description: Optional[str] = None
    structure_json: dict = Field(default_factory=dict)
    prompt_injection: str = ""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "content_templates"
        use_state_management = True
        indexes = [
            "type",
            "user_id",
        ]

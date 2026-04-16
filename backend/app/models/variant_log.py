"""
Variant Log Document — MongoDB / Beanie

Logs generated variants for audit trail and analytics.
"""

from app.utils.datetime_utils import utc_now
from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class VariantLog(Document):
    """Record of a generated variant and its scores."""

    job_id: Indexed(str)  # type: ignore[valid-type]
    variant_id: str = ""

    content_preview: str = ""  # first 500 chars
    scores: dict = Field(default_factory=dict)  # {engagement: 0.8, ...}
    total_score: float = 0.0
    was_selected: bool = False

    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "variant_logs"
        use_state_management = True

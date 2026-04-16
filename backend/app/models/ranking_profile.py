"""
Ranking Profile Document — MongoDB / Beanie

Per-user adaptive ranking weights for the V3.3 multi-signal scorer.
"""

from app.utils.datetime_utils import utc_now
from datetime import datetime

from beanie import Document, Indexed
from pydantic import Field


class RankingProfile(Document):
    """Per-user ranking weights — adapted via micro-updates."""

    user_id: Indexed(str, unique=True)  # type: ignore[valid-type]

    w_engagement: float = 0.40
    w_persona: float = 0.30
    w_novelty: float = 0.15
    w_trend: float = 0.15

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "ranking_profiles"
        use_state_management = True

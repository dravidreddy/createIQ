"""
Profile Models — MongoDB / Beanie

Two models:
  - ProfileEmbed: Pydantic sub-model for legacy embedded reads
  - UserProfile: Standalone Beanie Document in `user_profiles` collection
"""

from datetime import datetime
from typing import List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field


# ─── Legacy Embedded Profile (read-only compat) ─────────────────

class ProfileEmbed(BaseModel):
    """Sub-document for backward-compatible embedded profile reads."""

    content_niche: str = ""
    custom_niche: Optional[str] = None
    primary_platforms: List[str] = []
    content_style: str = ""
    target_audience: Optional[str] = None
    typical_video_length: str = ""
    preferred_language: str = "English"
    additional_context: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Standalone Profile Document ────────────────────────────────

class UserProfile(Document):
    """Creator profile — one per user, stored separately for scalability."""

    user_id: Indexed(PydanticObjectId, unique=True)  # type: ignore[valid-type]

    # Content preferences
    content_niche: str = ""
    custom_niche: Optional[str] = None
    primary_platforms: List[str] = []
    content_style: str = ""
    target_audience: Optional[str] = None
    typical_video_length: str = ""
    preferred_language: str = "English"
    additional_context: Optional[str] = None

    # Extended personalisation
    default_tone: Optional[str] = None
    preferences: dict = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "user_profiles"
        use_state_management = True

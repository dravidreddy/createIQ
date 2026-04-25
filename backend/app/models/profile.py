"""
Profile Models — MongoDB / Beanie

Two models:
  - ProfileEmbed: Pydantic sub-model for legacy embedded reads
  - UserProfile: Standalone Beanie Document in `user_profiles` collection
"""

from app.utils.datetime_utils import utc_now
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
    vocabulary: Optional[str] = None
    avoid_words: Optional[str] = None
    formality_level: Optional[str] = None
    hook_framework: Optional[str] = None
    default_cta: Optional[str] = None
    pacing_style: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


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
    vocabulary: Optional[str] = None
    avoid_words: Optional[str] = None
    formality_level: Optional[str] = None
    hook_framework: Optional[str] = None
    default_cta: Optional[str] = None
    pacing_style: Optional[str] = None
    preferences: dict = Field(default_factory=dict)

    # Voice profile — learned from creator's uploaded scripts
    voice_profile: Optional[dict] = Field(default=None)
    # Structure: {
    #   "tone": "casual_energetic",
    #   "avg_sentence_length": 12,
    #   "hook_style": "question_based",
    #   "vocabulary_level": "simple",
    #   "signature_phrases": ["here's the thing", "let me tell you"],
    #   "pacing": "fast_start_slow_middle",
    #   "formality": "informal",
    #   "analyzed_at": "2026-04-17T..."
    # }
    voice_sample_count: int = Field(default=0)


    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "user_profiles"
        use_state_management = True

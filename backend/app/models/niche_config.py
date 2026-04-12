"""
NicheConfig Beanie Document — NAPOS Niche Configuration Store.

Stores niche-specific domain knowledge (vocabulary, tone guidelines,
content patterns) used by the Prompt Orchestrator for context injection.

Hybrid model: JSON seed files on disk → MongoDB at runtime.
Seeded on app startup from app/niche_configs/*.json.
"""

from datetime import datetime
from typing import Dict, List, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field


class PlatformHints(BaseModel):
    """Platform-specific content guidance within a niche."""
    youtube: str = ""
    tiktok: str = ""
    instagram: str = ""
    linkedin: str = ""
    podcast: str = ""
    blog: str = ""
    twitter: str = ""


class NicheConfigModel(Document):
    """Niche configuration document — one per niche, stored in MongoDB.

    Seeded from JSON files at startup, editable at runtime via admin API.
    """

    niche: Indexed(str, unique=True)  # type: ignore[valid-type]
    version: str = "v1"
    display_name: str = ""

    # Domain Knowledge
    tone_guidelines: str = ""
    vocabulary: List[str] = Field(default_factory=list)
    avoid_vocabulary: List[str] = Field(default_factory=list)
    content_patterns: List[str] = Field(default_factory=list)
    audience_archetype: str = ""

    # Platform-specific hints
    platform_hints: PlatformHints = Field(default_factory=PlatformHints)

    # Engagement rules
    engagement_rules: List[str] = Field(default_factory=list)

    # Metadata
    is_custom: bool = False  # True if user-created (not from seed files)
    created_by: Optional[str] = None  # user_id if custom
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "niche_configs"
        use_state_management = True

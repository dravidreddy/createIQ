"""
Profile Schemas

Pydantic schemas for creator profile management.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ContentNiche(str, Enum):
    """Predefined content niches."""
    TECH = "Tech"
    FITNESS = "Fitness"
    FINANCE = "Finance"
    EDUCATION = "Education"
    ENTERTAINMENT = "Entertainment"
    GAMING = "Gaming"
    LIFESTYLE = "Lifestyle"
    TRAVEL = "Travel"
    FOOD = "Food"
    BEAUTY = "Beauty"
    OTHER = "Other"


class Platform(str, Enum):
    """Supported content platforms."""
    YOUTUBE = "YouTube"
    INSTAGRAM_REELS = "Instagram Reels"
    TIKTOK = "TikTok"
    LINKEDIN = "LinkedIn"
    PODCAST = "Podcast"
    BLOG = "Blog"
    TWITTER = "Twitter/X"


class ContentStyle(str, Enum):
    """Content style/tone options."""
    EDUCATIONAL = "Educational"
    ENTERTAINING = "Entertaining"
    INSPIRATIONAL = "Inspirational"
    CASUAL = "Casual"
    PROFESSIONAL = "Professional"
    STORYTELLING = "Storytelling"
    TUTORIAL = "Tutorial"


class VideoLength(str, Enum):
    """Typical video length categories."""
    SHORT = "Short-form (<60s)"
    MEDIUM = "Medium (1-10 min)"
    LONG = "Long-form (10+ min)"
    MIXED = "Mixed"


class ProfileBase(BaseModel):
    """Base profile schema with common fields."""
    content_niche: ContentNiche
    custom_niche: Optional[str] = Field(None, max_length=200)
    primary_platforms: List[Platform] = Field(..., min_length=1)
    content_style: ContentStyle
    target_audience: Optional[str] = Field(None, max_length=500)
    typical_video_length: VideoLength
    preferred_language: str = Field(default="English", max_length=50)
    additional_context: Optional[str] = Field(None, max_length=1000)
    # Advanced Persona Fields
    vocabulary: Optional[str] = Field(None, max_length=1000)
    avoid_words: Optional[str] = Field(None, max_length=1000)
    formality_level: Optional[str] = Field(None, max_length=100)
    hook_framework: Optional[str] = Field(None, max_length=100)
    default_cta: Optional[str] = Field(None, max_length=500)
    pacing_style: Optional[str] = Field(None, max_length=100)


class ProfileCreate(ProfileBase):
    """Schema for creating a new profile."""
    pass


class ProfileUpdate(BaseModel):
    """Schema for updating profile (all fields optional)."""
    content_niche: Optional[ContentNiche] = None
    custom_niche: Optional[str] = Field(None, max_length=200)
    primary_platforms: Optional[List[Platform]] = None
    content_style: Optional[ContentStyle] = None
    target_audience: Optional[str] = Field(None, max_length=500)
    typical_video_length: Optional[VideoLength] = None
    preferred_language: Optional[str] = Field(None, max_length=50)
    additional_context: Optional[str] = Field(None, max_length=1000)
    vocabulary: Optional[str] = Field(None, max_length=1000)
    avoid_words: Optional[str] = Field(None, max_length=1000)
    formality_level: Optional[str] = Field(None, max_length=100)
    hook_framework: Optional[str] = Field(None, max_length=100)
    default_cta: Optional[str] = Field(None, max_length=500)
    pacing_style: Optional[str] = Field(None, max_length=100)


class ProfileResponse(ProfileBase):
    """Schema for profile API responses."""
    id: str          # MongoDB ObjectId string (same as user_id — profile is embedded)
    user_id: str     # MongoDB ObjectId string
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileContext(BaseModel):
    """
    Profile context for AI agent injection.
    
    This is the format passed to agents for personalization.
    """
    content_niche: str
    platforms: List[str]
    content_style: str
    target_audience: str
    video_length: str
    language: str
    additional_context: str
    vocabulary: Optional[str] = None
    avoid_words: Optional[str] = None
    formality_level: Optional[str] = None
    hook_framework: Optional[str] = None
    default_cta: Optional[str] = None
    pacing_style: Optional[str] = None

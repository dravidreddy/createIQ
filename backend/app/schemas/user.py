"""
User Schemas

Pydantic schemas for User API requests and responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    display_name: str = Field(..., min_length=2, max_length=100)


class UserCreate(UserBase):
    """Schema for user registration via Firebase."""
    model_config = ConfigDict(extra="forbid")
    firebase_uid: str = Field(..., description="Firebase UID — the canonical auth link")


class UserUpdate(BaseModel):
    """Schema for updating user details."""
    model_config = ConfigDict(extra="forbid")
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None


class UserInDB(UserBase):
    """Schema for user in database."""
    id: str   # MongoDB ObjectId string
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    """Schema for user API responses."""
    id: str   # MongoDB ObjectId string
    is_active: bool
    is_verified: bool
    created_at: datetime
    has_profile: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserWithProfile(UserResponse):
    """Schema for user with profile data."""
    profile: Optional["ProfileResponse"] = None

    model_config = ConfigDict(from_attributes=True)


# Import at end to avoid circular imports
from app.schemas.profile import ProfileResponse
UserWithProfile.model_rebuild()

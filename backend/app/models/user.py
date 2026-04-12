"""
User Document — MongoDB / Beanie

Core user identity. Profile is stored in a separate `user_profiles` collection.
The legacy embedded `profile` field is kept as Optional for backward compatibility
but new code should use the `user_profiles` collection instead.
"""

from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pydantic import EmailStr, Field


class User(Document):
    """Registered user of CreatorIQ."""

    email: Indexed(EmailStr, unique=True)  # type: ignore[valid-type]
    display_name: str
    hashed_password: Optional[str] = None
    
    auth_provider: str = "local"
    firebase_uid: Optional[str] = None

    is_active: bool = True
    is_verified: bool = False

    last_login: Optional[datetime] = None

    # Legacy embedded profile — kept for backward compat reads.
    # New writes should go to the `user_profiles` collection.
    profile: Optional[dict] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        use_state_management = True

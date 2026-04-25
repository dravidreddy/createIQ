"""
User Document — MongoDB / Beanie

Core user identity linked to Firebase via firebase_uid.
Profile is stored in a separate `user_profiles` collection.
"""

from app.utils.datetime_utils import utc_now
from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pydantic import EmailStr, Field


class User(Document):
    """Registered user of CreatorIQ."""

    email: Indexed(EmailStr, unique=True)  # type: ignore[valid-type]
    display_name: str

    # Firebase is the sole auth provider — this is the canonical link
    # Made Optional temporarily for migration compatibility.
    firebase_uid: Optional[str] = None

    is_active: bool = True
    is_verified: bool = False

    # Monetization — credits consumed per pipeline run
    credits: int = Field(default=50)

    last_login: Optional[datetime] = None

    # Legacy embedded profile — kept for backward compat reads.
    # New writes should go to the `user_profiles` collection.
    profile: Optional[dict] = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "users"
        use_state_management = True
        indexes = [
            # Use a sparse index so multiple users missing the field don't cause duplicate key errors
            __import__('pymongo').IndexModel(
                [("firebase_uid", __import__('pymongo').ASCENDING)], 
                unique=True, 
                sparse=True
            )
        ]

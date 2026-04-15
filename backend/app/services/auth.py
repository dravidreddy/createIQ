"""
Authentication Service — Firebase-Native

Handles user authentication via Firebase Admin SDK.
No password hashing, no JWT minting — Firebase owns the credential lifecycle.
"""

from datetime import datetime
from typing import Optional
from app.models.user import User
from app.utils.firebase_auth import verify_firebase_token
import logging
from firebase_admin import auth as firebase_auth
from app.utils.firebase import init_firebase  # Ensures initialized

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service — stateless, no db session required."""

    async def authenticate_firebase_user(self, firebase_token: str) -> Optional[User]:
        """Authenticate or register a user using a Firebase ID Token.

        This is the single entry point for all logins (Google, email/password).
        Firebase owns the credentials; we just maintain a User document in MongoDB
        for business data (profiles, projects, preferences).
        """
        try:
            # Verify the token with Firebase Admin
            decoded_token = firebase_auth.verify_id_token(firebase_token)
            uid = decoded_token.get("uid")
            email = decoded_token.get("email")
            display_name = decoded_token.get("name") or email.split("@")[0]

            if not email or not uid:
                logger.warning("Firebase token missing email or uid")
                return None

            email = email.lower()

            # Check if user exists by firebase_uid (canonical lookup)
            user = await User.find_one(User.firebase_uid == uid)
            if user:
                user.last_login = datetime.utcnow()
                # Sync display name if changed in Firebase
                if display_name and user.display_name != display_name:
                    user.display_name = display_name
                await user.save()
                return user

            # Fallback: Check by email (handles legacy users without firebase_uid)
            user = await self.get_user_by_email(email)
            if user:
                # Link the Firebase UID to this existing account
                user.firebase_uid = uid
                user.last_login = datetime.utcnow()
                await user.save()
                logger.info(f"Linked Firebase UID {uid} to existing user {email}")
                return user

            # Create new user
            user = User(
                email=email,
                display_name=display_name,
                firebase_uid=uid,
                is_active=True,
                is_verified=decoded_token.get("email_verified", False),
                last_login=datetime.utcnow()
            )
            await user.insert()
            logger.info(f"Registered new Firebase user: {email}")
            return user

        except Exception as e:
            logger.error(f"Firebase token verification failed: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Find a user by their email address (lower-cased)."""
        return await User.find_one(User.email == email.lower())

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Find a user by their ObjectId string."""
        from beanie import PydanticObjectId
        try:
            return await User.get(PydanticObjectId(user_id))
        except (ValueError, TypeError):
            return None
        except Exception:
            logger.error("User lookup failed for user_id=%s", user_id, exc_info=True)
            raise

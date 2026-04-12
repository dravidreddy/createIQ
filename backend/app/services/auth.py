"""
Authentication Service — MongoDB / Beanie

Handles user authentication, token management, and password operations.
No database session is injected — Beanie documents have class-level async methods.
"""

from datetime import datetime
from typing import Optional
from app.models.user import User
from app.schemas.user import UserCreate
from app.schemas.auth import Token
from app.utils.security import (
    hash_password,
    verify_password,
    create_tokens,
    verify_token,
)
import logging
from pymongo.errors import DuplicateKeyError
from firebase_admin import auth as firebase_auth
from app.utils.firebase import init_firebase # Ensures initialized

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service — stateless, no db session required."""

    async def login(self, user: User) -> Token:
        """Create and return JWT tokens for an already authenticated user."""
        user_id = str(user.id)
        access_token, refresh_token, expires_in = create_tokens(user_id)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
        )

    async def authenticate_firebase_user(self, firebase_token: str) -> Optional[User]:
        """Authenticate or register a user using a Firebase ID Token."""
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
            
            # Check if user exists
            user = await self.get_user_by_email(email)
            if user:
                # Link account if needed
                if not user.firebase_uid:
                    user.firebase_uid = uid
                    user.auth_provider = "firebase"
                
                user.last_login = datetime.utcnow()
                await user.save()
                return user
                
            # Create new user
            user = User(
                email=email,
                display_name=display_name,
                auth_provider="firebase",
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

    async def refresh_tokens(self, refresh_token: str) -> Optional[Token]:
        """Refresh access token using a valid refresh token."""
        user_id = verify_token(refresh_token, token_type="refresh")
        if not user_id:
            logger.warning("Invalid refresh token")
            return None

        user = await self.get_user_by_id(user_id)
        if not user or not user.is_active:
            return None

        access_token, new_refresh_token, expires_in = create_tokens(str(user.id))

        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=expires_in,
        )

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Find a user by their email address (lower-cased)."""
        return await User.find_one(User.email == email.lower())

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Find a user by their ObjectId string."""
        from beanie import PydanticObjectId
        try:
            return await User.get(PydanticObjectId(user_id))
        except (ValueError, TypeError):
            # Invalid ObjectId format
            return None
        except Exception:
            # DB errors should propagate — caller decides 503 vs 401
            logger.error("User lookup failed for user_id=%s", user_id, exc_info=True)
            raise

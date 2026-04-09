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

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service — stateless, no db session required."""

    async def register_user(self, user_data: UserCreate) -> User:
        """
        Register a new user.

        Raises:
            ValueError: If the email is already registered.
        """
        # Normalize email
        user_data.email = user_data.email.lower()

        existing = await self.get_user_by_email(user_data.email)
        if existing:
            raise ValueError("Email already registered")

        user = User(
            email=user_data.email,
            display_name=user_data.display_name,
            hashed_password=hash_password(user_data.password),
            is_active=True,
            is_verified=False,
        )
        try:
            await user.insert()
        except DuplicateKeyError:
            logger.warning("Duplicate registration attempt for email: %s", user.email)
            raise ValueError("Email already registered")

        logger.info("Registered new user: %s", user.email)
        return user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password."""
        user = await self.get_user_by_email(email)
        if not user:
            logger.warning("Login attempt for non-existent email: %s", email)
            return None

        if not verify_password(password, user.hashed_password):
            logger.warning("Failed login attempt for: %s", email)
            return None

        if not user.is_active:
            logger.warning("Login attempt for inactive user: %s", email)
            return None

        # Update last login timestamp
        user.last_login = datetime.utcnow()
        await user.save()

        logger.info("User authenticated: %s", email)
        return user

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

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Change password after verifying existing one."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        if not verify_password(current_password, user.hashed_password):
            return False

        user.hashed_password = hash_password(new_password)
        await user.save()

        logger.info("Password changed for user: %s", user.email)
        return True

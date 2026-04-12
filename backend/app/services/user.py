"""
User Service — MongoDB / Beanie

Handles user and creator profile management operations.
Profile is now stored in the separate `user_profiles` collection (UserProfile).
Legacy embedded profile reads are still supported for backward compatibility.
"""

from datetime import datetime
from typing import Optional
from beanie import PydanticObjectId
from app.models.user import User
from app.models.profile import ProfileEmbed, UserProfile
from app.schemas.user import UserUpdate
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileContext
from app.utils.determinism import get_now
import logging

logger = logging.getLogger(__name__)


class UserService:
    """User and profile management — no db session required."""

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ObjectId string."""
        from beanie import PydanticObjectId
        try:
            return await User.get(PydanticObjectId(user_id))
        except Exception:
            return None

    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """Update basic user fields."""
        user = await self.get_user(user_id)
        if not user:
            return None

        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        user.updated_at = get_now()
        await user.save()

        logger.info("Updated user: %s", user.email)
        return user

    async def delete_user(self, user_id: str) -> bool:
        """Delete user and all related data."""
        user = await self.get_user(user_id)
        if not user:
            return False

        # Also delete the standalone profile
        profile = await UserProfile.find_one(UserProfile.user_id == PydanticObjectId(user_id))
        if profile:
            await profile.delete()

        await user.delete()
        logger.info("Deleted user: %s (id=%s)", user.email, user_id)
        return True

    # ─── Profile — stored in `user_profiles` collection ─────────

    async def create_profile(self, user_id: str, profile_data: ProfileCreate) -> ProfileEmbed:
        """
        Create creator profile in the `user_profiles` collection.
        Also writes to the legacy embedded field for backward compat.

        Raises:
            ValueError: If a profile already exists.
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError("User not found")

        existing = await UserProfile.find_one(UserProfile.user_id == user_id)
        if existing:
            raise ValueError("Profile already exists")

        # Create standalone profile document
        standalone = UserProfile(
            user_id=PydanticObjectId(user_id),
            content_niche=profile_data.content_niche.value,
            custom_niche=profile_data.custom_niche,
            primary_platforms=[p.value for p in profile_data.primary_platforms],
            content_style=profile_data.content_style.value,
            target_audience=profile_data.target_audience,
            typical_video_length=profile_data.typical_video_length.value,
            preferred_language=profile_data.preferred_language,
            additional_context=profile_data.additional_context,
            vocabulary=profile_data.vocabulary,
            avoid_words=profile_data.avoid_words,
            formality_level=profile_data.formality_level,
            hook_framework=profile_data.hook_framework,
            default_cta=profile_data.default_cta,
            pacing_style=profile_data.pacing_style,
        )
        await standalone.insert()

        # Build legacy embed for backward compat response
        embed = ProfileEmbed(
            content_niche=standalone.content_niche,
            custom_niche=standalone.custom_niche,
            primary_platforms=standalone.primary_platforms,
            content_style=standalone.content_style,
            target_audience=standalone.target_audience,
            typical_video_length=standalone.typical_video_length,
            preferred_language=standalone.preferred_language,
            additional_context=standalone.additional_context,
            vocabulary=standalone.vocabulary,
            avoid_words=standalone.avoid_words,
            formality_level=standalone.formality_level,
            hook_framework=standalone.hook_framework,
            default_cta=standalone.default_cta,
            pacing_style=standalone.pacing_style,
        )

        # Also store in legacy embedded field
        user.profile = embed.model_dump()
        user.updated_at = get_now()
        await user.save()

        logger.info("Created profile for user %s", user_id)
        return embed

    async def get_profile(self, user_id: str) -> Optional[ProfileEmbed]:
        """Get profile — reads from standalone collection first, falls back to embedded."""
        standalone = await UserProfile.find_one(UserProfile.user_id == PydanticObjectId(user_id))
        if standalone:
            return ProfileEmbed(
                content_niche=standalone.content_niche,
                custom_niche=standalone.custom_niche,
                primary_platforms=standalone.primary_platforms,
                content_style=standalone.content_style,
                target_audience=standalone.target_audience,
                typical_video_length=standalone.typical_video_length,
                preferred_language=standalone.preferred_language,
                additional_context=standalone.additional_context,
                vocabulary=standalone.vocabulary,
                avoid_words=standalone.avoid_words,
                formality_level=standalone.formality_level,
                hook_framework=standalone.hook_framework,
                default_cta=standalone.default_cta,
                pacing_style=standalone.pacing_style,
                created_at=standalone.created_at,
                updated_at=standalone.updated_at,
            )

        # Fallback: try legacy embedded profile
        user = await self.get_user(user_id)
        if not user or not user.profile:
            return None

        if isinstance(user.profile, dict):
            try:
                return ProfileEmbed(**user.profile)
            except Exception:
                return None
        return None

    async def update_profile(self, user_id: str, profile_data: ProfileUpdate) -> Optional[ProfileEmbed]:
        """Update profile fields in the standalone collection."""
        standalone = await UserProfile.find_one(UserProfile.user_id == PydanticObjectId(user_id))
        
        # Legacy migration check logic
        if not standalone:
            user = await self.get_user(user_id)
            if not user or not user.profile or not isinstance(user.profile, dict):
                return None
            
            p_dict = user.profile
            standalone = UserProfile(
                user_id=PydanticObjectId(user_id),
                content_niche=p_dict.get("content_niche", "Other"),
                custom_niche=p_dict.get("custom_niche", None),
                primary_platforms=p_dict.get("primary_platforms", ["YouTube"]),
                content_style=p_dict.get("content_style", "Educational"),
                target_audience=p_dict.get("target_audience", None),
                typical_video_length=p_dict.get("typical_video_length", "Medium (1-10 min)"),
                preferred_language=p_dict.get("preferred_language", "English"),
                additional_context=p_dict.get("additional_context", None),
                vocabulary=p_dict.get("vocabulary", None),
                avoid_words=p_dict.get("avoid_words", None),
                formality_level=p_dict.get("formality_level", None),
                hook_framework=p_dict.get("hook_framework", None),
                default_cta=p_dict.get("default_cta", None),
                pacing_style=p_dict.get("pacing_style", None),
            )
            await standalone.insert()
            logger.info(f"Migrated legacy profile to standalone collection during update for {user_id}")

        update_data = profile_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if hasattr(value, "value"):
                    value = value.value
                elif isinstance(value, list):
                    value = [v.value if hasattr(v, "value") else v for v in value]
                setattr(standalone, field, value)

        standalone.updated_at = get_now()
        await standalone.save()

        # Sync back to legacy embedded field
        user = await self.get_user(user_id)
        if user:
            user.profile = {
                "content_niche": standalone.content_niche,
                "custom_niche": standalone.custom_niche,
                "primary_platforms": standalone.primary_platforms,
                "content_style": standalone.content_style,
                "target_audience": standalone.target_audience,
                "typical_video_length": standalone.typical_video_length,
                "preferred_language": standalone.preferred_language,
                "additional_context": standalone.additional_context,
                "vocabulary": standalone.vocabulary,
                "avoid_words": standalone.avoid_words,
                "formality_level": standalone.formality_level,
                "hook_framework": standalone.hook_framework,
                "default_cta": standalone.default_cta,
                "pacing_style": standalone.pacing_style,
            }
            user.updated_at = datetime.utcnow()
            await user.save()

        logger.info("Updated profile for user %s", user_id)
        return await self.get_profile(user_id)

    async def has_profile(self, user_id: str) -> bool:
        """Check if user has a profile set up."""
        profile = await self.get_profile(user_id)
        return profile is not None

    async def get_profile_context(self, user_id: str) -> Optional[ProfileContext]:
        """Get profile formatted for AI context injection."""
        profile = await self.get_profile(user_id)
        if not profile:
            return None

        return ProfileContext(
            content_niche=profile.custom_niche or profile.content_niche,
            platforms=profile.primary_platforms,
            content_style=profile.content_style,
            target_audience=profile.target_audience or "General audience",
            video_length=profile.typical_video_length,
            language=profile.preferred_language,
            additional_context=profile.additional_context or "",
            vocabulary=profile.vocabulary,
            avoid_words=profile.avoid_words,
            formality_level=profile.formality_level,
            hook_framework=profile.hook_framework,
            default_cta=profile.default_cta,
            pacing_style=profile.pacing_style,
        )

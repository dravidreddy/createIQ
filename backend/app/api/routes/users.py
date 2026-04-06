"""
User Routes — MongoDB / Beanie

User and profile management endpoints.
No more db: AsyncSession dependency.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import User
from app.schemas.user import UserUpdate, UserResponse, UserWithProfile
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse
from app.services.user import UserService
from app.api.deps import get_current_user, verify_csrf
from app.schemas.base import CreatorResponse, wrap_response

router = APIRouter(dependencies=[Depends(verify_csrf)])


@router.get("/me", response_model=CreatorResponse[UserWithProfile])
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user with embedded profile."""
    user_service = UserService()
    user = await user_service.get_user(str(current_user.id))
    profile = user.profile if user else None

    return wrap_response(UserWithProfile(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        has_profile=profile is not None,
        profile=ProfileResponse(
            id=str(current_user.id),   # profile shares user id (embedded)
            user_id=str(current_user.id),
            content_niche=profile.content_niche,
            custom_niche=profile.custom_niche,
            primary_platforms=profile.primary_platforms,
            content_style=profile.content_style,
            target_audience=profile.target_audience,
            typical_video_length=profile.typical_video_length,
            preferred_language=profile.preferred_language,
            additional_context=profile.additional_context,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        ) if profile else None,
    ))


@router.put("/me", response_model=CreatorResponse[UserResponse])
async def update_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update current user's basic info."""
    user_service = UserService()
    user = await user_service.update_user(str(current_user.id), user_data)
    has_profile = await user_service.has_profile(str(current_user.id))

    return wrap_response(UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        has_profile=has_profile,
    ))


@router.post("/profile", response_model=CreatorResponse[ProfileResponse], status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_user),
):
    """Create creator profile for current user."""
    user_service = UserService()

    try:
        profile = await user_service.create_profile(str(current_user.id), profile_data)
        return wrap_response(ProfileResponse(
            id=str(current_user.id),
            user_id=str(current_user.id),
            content_niche=profile.content_niche,
            custom_niche=profile.custom_niche,
            primary_platforms=profile.primary_platforms,
            content_style=profile.content_style,
            target_audience=profile.target_audience,
            typical_video_length=profile.typical_video_length,
            preferred_language=profile.preferred_language,
            additional_context=profile.additional_context,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        ))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/profile", response_model=CreatorResponse[ProfileResponse])
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile."""
    user_service = UserService()
    profile = await user_service.get_profile(str(current_user.id))

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create a profile first.",
        )

    return wrap_response(ProfileResponse(
        id=str(current_user.id),
        user_id=str(current_user.id),
        content_niche=profile.content_niche,
        custom_niche=profile.custom_niche,
        primary_platforms=profile.primary_platforms,
        content_style=profile.content_style,
        target_audience=profile.target_audience,
        typical_video_length=profile.typical_video_length,
        preferred_language=profile.preferred_language,
        additional_context=profile.additional_context,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    ))


@router.put("/profile", response_model=CreatorResponse[ProfileResponse])
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update current user's profile."""
    user_service = UserService()
    profile = await user_service.update_profile(str(current_user.id), profile_data)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    return wrap_response(ProfileResponse(
        id=str(current_user.id),
        user_id=str(current_user.id),
        content_niche=profile.content_niche,
        custom_niche=profile.custom_niche,
        primary_platforms=profile.primary_platforms,
        content_style=profile.content_style,
        target_audience=profile.target_audience,
        typical_video_length=profile.typical_video_length,
        preferred_language=profile.preferred_language,
        additional_context=profile.additional_context,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    ))


@router.delete("/me", response_model=CreatorResponse[dict])
async def delete_account(current_user: User = Depends(get_current_user)):
    """Delete current user account and all related data."""
    user_service = UserService()
    await user_service.delete_user(str(current_user.id))
    return wrap_response({"message": "Account deleted successfully"})

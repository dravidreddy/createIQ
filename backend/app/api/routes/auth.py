"""
Authentication Routes — Firebase-Native

Login via Firebase ID token, session cookie management, and logout.
All credential verification is delegated to Firebase Admin SDK.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request

from app.config import get_settings
from app.schemas.user import UserResponse
from app.schemas.auth import FirebaseTokenRequest
from app.services.auth import AuthService
from app.services.user import UserService
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.base import CreatorResponse, wrap_response

router = APIRouter()


@router.post("/firebase", response_model=CreatorResponse[UserResponse])
async def login_firebase(token_data_in: FirebaseTokenRequest, response: Response):
    """
    Authenticate user via Firebase ID token, upsert User document,
    and set the Firebase token as an HttpOnly session cookie.
    """
    auth_service = AuthService()
    settings = get_settings()

    # 1. Verify Firebase token & upsert user in MongoDB
    user = await auth_service.authenticate_firebase_user(token_data_in.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase token or authentication failed",
        )

    # 2. Set the Firebase ID token itself as the session cookie
    #    Firebase tokens expire in 1 hour; frontend proactively refreshes at ~50 min.
    cookie_params = {
        "httponly": True,
        "samesite": settings.cookie_samesite,
        "secure": settings.cookie_secure,
        "path": "/",
    }

    response.set_cookie(
        key="access_token",
        value=token_data_in.token,
        max_age=3600,  # 1 hour — matches Firebase token lifetime
        **cookie_params
    )

    # 3. Return User Data
    user_service = UserService()
    has_profile = await user_service.has_profile(str(user.id))

    return wrap_response(UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        has_profile=has_profile,
    ))


@router.get("/me", response_model=CreatorResponse[UserResponse])
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's information."""
    user_service = UserService()
    has_profile = await user_service.has_profile(str(current_user.id))

    return wrap_response(UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        has_profile=has_profile,
    ))


@router.post("/logout", response_model=CreatorResponse[dict])
async def logout(response: Response):
    """
    Logout current user by clearing the session cookie.
    Must use exact same path and domain as set_cookie.
    """
    settings = get_settings()
    cookie_params = {
        "path": "/",
        "httponly": True,
        "samesite": settings.cookie_samesite,
        "secure": settings.cookie_secure,
    }
    response.delete_cookie("access_token", **cookie_params)
    return wrap_response({"message": "Logged out successfully"})

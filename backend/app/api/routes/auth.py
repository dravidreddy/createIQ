"""
Authentication Routes — MongoDB / Beanie

Login, signup, token refresh endpoints.
No more db: AsyncSession dependency.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request

from app.config import get_settings
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import Token, LoginRequest, RefreshTokenRequest, PasswordChange
from app.services.auth import AuthService
from app.services.user import UserService
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.base import CreatorResponse, wrap_response

router = APIRouter()


@router.post("/signup", response_model=CreatorResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate):
    """Register a new user."""
    auth_service = AuthService()

    try:
        user = await auth_service.register_user(user_data)
        return wrap_response(UserResponse(
            id=str(user.id),
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            has_profile=False,
        ))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=CreatorResponse[UserResponse])
async def login(login_data: LoginRequest, response: Response):
    """
    Authenticate user and return User object + set JWT cookies.
    This atomic response eliminates the login-to-getMe race condition.
    """
    auth_service = AuthService()
    settings = get_settings()

    # 1. Authenticate
    user = await auth_service.authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # 2. Generate Tokens
    token_data = await auth_service.login(login_data.email, login_data.password)
    if not token_data:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token generation failed")

    # 3. Set Hardened Cookies
    # SameSite=Lax is used to allow the initial navigation but prevent CSRF on mutations
    cookie_params = {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.cookie_secure,
        "path": "/",
    }

    response.set_cookie(
        key="access_token",
        value=token_data.access_token,
        max_age=settings.access_token_expire_minutes * 60,
        **cookie_params
    )
    response.set_cookie(
        key="refresh_token",
        value=token_data.refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        **cookie_params
    )

    # 4. Return User Data Atomicly
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


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    """Refresh access token using refresh token cookie."""
    refresh_token_val = request.cookies.get("refresh_token")
    if not refresh_token_val:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    auth_service = AuthService()
    settings = get_settings()

    token = await auth_service.refresh_tokens(refresh_token_val)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    cookie_params = {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.cookie_secure,
        "path": "/",
    }

    response.set_cookie(
        key="access_token",
        value=token.access_token,
        max_age=settings.access_token_expire_minutes * 60,
        **cookie_params
    )
    response.set_cookie(
        key="refresh_token",
        value=token.refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        **cookie_params
    )

    return wrap_response({"message": "Token refreshed successfully"})


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
):
    """Change current user's password."""
    auth_service = AuthService()

    success = await auth_service.change_password(
        user_id=str(current_user.id),
        current_password=password_data.current_password,
        new_password=password_data.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    return wrap_response({"message": "Password changed successfully"})


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
    Logout current user by clearing cookies.
    Must use exact same path and domain as set_cookie.
    """
    # Use same params as login to ensure the browser identifies the correct cookie to delete
    cookie_params = {
        "path": "/",
        "httponly": True,
        "samesite": "lax",
    }
    response.delete_cookie("access_token", **cookie_params)
    response.delete_cookie("refresh_token", **cookie_params)
    return wrap_response({"message": "Logged out successfully"})

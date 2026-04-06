"""
API Dependencies — MongoDB / Beanie

Dependency injection for routes.
No more AsyncSession — Beanie documents are queried directly.
"""

from fastapi import Depends, HTTPException, status, Request
from beanie import PydanticObjectId

from app.models.user import User
from app.utils.security import verify_token
from app.services.auth import AuthService
from app.services.user import UserService
from app.services.project import ProjectService

async def get_current_user(request: Request) -> User:
    """
    Get current authenticated user with Zero-Gap Precedence.
    1. Authorization Header (Bearer)
    2. access_token Cookie
    3. token Query Parameter (SSE Fallback)
    """
    from app.config import get_settings
    settings = get_settings()

    # Load Test Bypass
    if settings.load_test_mode:
        load_test_user_id = request.headers.get("X-Load-Test-User")
        if load_test_user_id:
            return User(
                id=PydanticObjectId(load_test_user_id),
                email=f"loadtest_{load_test_user_id}@example.com",
                display_name=f"Load Tester {load_test_user_id}",
                hashed_password="...",
                is_active=True
            )
    token = None

    # 1. Header (Highest priority for CLI/Tests)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]

    # 2. Cookie (Standard browser)
    if not token:
        token = request.cookies.get("access_token")

    # 3. Query Param (SSE Fallback)
    if not token:
        token = request.query_params.get("token")

    if not token:
        from app.utils.logging import logger
        logger.warning(f"Auth: No credentials provided from {request.client.host}. Path: {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = verify_token(token, token_type="access")

    if not user_id:
        from app.utils.logging import logger
        logger.warning(f"Auth: Token verification failed for token type 'access'. Request from {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # user_id is a string (ObjectId)
    # Cache disabled to prevent stale state (e.g. has_profile stale reads)
    try:
        user = await User.get(PydanticObjectId(user_id))
    except (ValueError, TypeError):
        user = None
    except Exception:
        # DB is unreachable — return 503 so frontend knows NOT to clear session
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        )

    if not user:
        from app.utils.logging import logger
        logger.warning(f"Auth: User not found for user_id {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Convenience alias for get_current_user."""
    return current_user


def get_auth_service() -> AuthService:
    """Get AuthService instance (no db session needed)."""
    return AuthService()


def get_user_service() -> UserService:
    """Get UserService instance."""
    return UserService()


def get_project_service() -> ProjectService:
    """Get ProjectService instance."""
    return ProjectService()


async def verify_csrf(request: Request):
    """
    Verify CSRF protection for all state-changing requests.
    Enforces 'X-Requested-With' presence for browser-based calls.
    """
    # GET/HEAD/OPTIONS are exempt
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # Skip if using Authorization header (programmatic access)
    if request.headers.get("Authorization"):
        return

    # Check for custom header that browsers won't send cross-origin without CORS approval
    if not request.headers.get("X-Requested-With"):
        from app.utils.logging import logger
        logger.warning(f"CSRF: Missing X-Requested-With header on {request.method} {request.url}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF Protection: Missing mandatory custom header."
        )

"""
API Dependencies — MongoDB / Beanie

Dependency injection for routes.
No more AsyncSession — Beanie documents are queried directly.

Auth: Firebase ID tokens are verified via firebase_auth (cached).
"""

from fastapi import Depends, HTTPException, status, Request
from beanie import PydanticObjectId

from app.models.user import User
from app.utils.firebase_auth import verify_firebase_token
from app.services.auth import AuthService
from app.services.user import UserService
from app.services.project import ProjectService


def _extract_token(request: Request) -> str | None:
    """Extract Firebase token with zero-gap precedence.

    1. Authorization Header (Bearer) — CLI / programmatic
    2. access_token Cookie — Browser (standard)
    3. token Query Parameter — SSE fallback
    """
    # 1. Header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]

    # 2. Cookie
    token = request.cookies.get("access_token")
    if token:
        return token

    # 3. Query param (SSE fallback)
    return request.query_params.get("token")


async def get_current_user(request: Request) -> User:
    """Get current authenticated user via Firebase token verification.

    Flow:
      1. Extract token (header > cookie > query)
      2. Verify with Firebase Admin SDK (cached 5 min)
      3. Lookup User document by firebase_uid
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
                firebase_uid=f"loadtest_{load_test_user_id}",
                is_active=True
            )

    token = _extract_token(request)

    if not token:
        from app.utils.logging import logger
        logger.warning(f"Auth: No credentials provided from {request.client.host}. Path: {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify Firebase token (cached for 5 minutes)
    firebase_user = await verify_firebase_token(token)

    if not firebase_user:
        from app.utils.logging import logger
        logger.warning(f"Auth: Firebase token verification failed. Request from {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Lookup user by firebase_uid — the canonical link
    try:
        user = await User.find_one(User.firebase_uid == firebase_user["uid"])
    except Exception:
        # DB is unreachable — return 503 so frontend knows NOT to clear session
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        )

    if not user:
        from app.utils.logging import logger
        logger.warning(f"Auth: No user document for firebase_uid {firebase_user['uid']}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not registered. Please sign in again.",
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


async def get_current_workspace(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Enforce workspace isolation and RBAC.
    
    Requires x-workspace-id header. Verifies user belongs to the workspace.
    """
    from app.models.workspace import Workspace
    
    workspace_id = request.headers.get("x-workspace-id")
    
    if not workspace_id:
        # Temporary Fallback: Just return their personal workspace
        ws = await Workspace.find_one({"owner_id": str(current_user.id)})
        if not ws:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No x-workspace-id provided and no personal workspace found."
            )
        return ws
        
    try:
        workspace = await Workspace.get(PydanticObjectId(workspace_id))
    except Exception:
        workspace = None
        
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
        
    # Verify membership
    is_member = any(member.user_id == str(current_user.id) for member in workspace.members)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace."
        )
        
    return workspace

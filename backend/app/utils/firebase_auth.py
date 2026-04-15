"""
Firebase Token Verification with In-Memory TTL Cache

Replaces the legacy JWT verification layer. Every API request now verifies
the caller's Firebase ID token instead of a self-minted JWT.

The TTL cache avoids round-tripping to Firebase on every single request —
a verified token is cached for 5 minutes keyed on the raw token string.
"""

import logging
from typing import Any, Dict, Optional

from cachetools import TTLCache
from firebase_admin import auth as firebase_auth

from app.utils.firebase import init_firebase  # Ensures SDK is initialised

logger = logging.getLogger(__name__)

# Cache verified tokens for 5 minutes (Firebase tokens live for 1 hour,
# so 5 min is a safe window — a revoked token is stale for at most 5 min).
_token_cache: TTLCache = TTLCache(maxsize=1024, ttl=300)


async def verify_firebase_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a Firebase ID token and return the decoded claims.

    Returns a dict with at least ``uid``, ``email``, ``name`` on success,
    or ``None`` if the token is invalid / expired / revoked.
    """
    if not token:
        return None

    # 1. Cache hit — skip Firebase call
    cached = _token_cache.get(token)
    if cached is not None:
        return cached

    # 2. Verify with Firebase Admin SDK
    try:
        decoded = firebase_auth.verify_id_token(token, check_revoked=True)
        result: Dict[str, Any] = {
            "uid": decoded.get("uid"),
            "email": decoded.get("email"),
            "name": decoded.get("name") or decoded.get("email", "").split("@")[0],
            "email_verified": decoded.get("email_verified", False),
            "picture": decoded.get("picture"),
        }
        _token_cache[token] = result
        return result
    except firebase_auth.ExpiredIdTokenError:
        logger.debug("Firebase token expired")
        return None
    except firebase_auth.RevokedIdTokenError:
        logger.warning("Firebase token has been revoked")
        return None
    except firebase_auth.InvalidIdTokenError as e:
        logger.warning("Firebase token invalid: %s", e)
        return None
    except Exception as e:
        logger.error("Firebase token verification failed: %s", e)
        return None


def clear_token_cache() -> None:
    """Flush the in-memory token cache (useful in tests)."""
    _token_cache.clear()

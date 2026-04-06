"""
Rate Limiting Utility

Production-grade rate limiter using Redis sliding window.
Falls back to an in-memory implementation ONLY when Redis is unavailable
(i.e., local development without Redis).

For production, set REDIS_URL in environment variables.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
import asyncio
import time

from app.api.deps import get_current_user
from app.models.user import User
from app.models.infrastructure import get_redis, redis_cb, CircuitState
from app.config import get_settings

logger = logging.getLogger(__name__)

# Redis is now the REQUIRED backend for rate limiting.
_redis_client = None

# Lazily imported Redis client — None until first use
_redis_client = None


def _get_redis():
    """Use the centralized singleton Upstash Redis client (Respects Circuit Breaker)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    
    # Check circuit breaker before trying to initialize
    if redis_cb.state == CircuitState.OPEN:
        return None
    
    try:
        _redis_client = get_redis()
    except Exception as exc:
        logger.error(f"Rate limiter: Redis initialization failed ({exc}).")
        if get_settings().env == "prod":
            # During init we keep the error if in prod, but rate_limit will fail-open later
            raise
            
    return _redis_client


async def _check_redis_limit(redis, key: str, limit: int, window_seconds: int) -> bool:
    """
    Sliding window rate check using Redis MULTI/EXEC.
    Returns True if the request is allowed, False if rate-limited.
    """
    import time
    now = time.time()
    window_start = now - window_seconds

    pipe = redis.pipeline()
    # Remove timestamps outside the window, add the current timestamp, query count
    pipe.zremrangebyscore(key, "-inf", window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window_seconds + 1)
    results = await pipe.execute()

    count = results[2]
    return count <= limit


def _check_memory_limit(key: str, limit: int, window_seconds: int) -> bool:
    """In-memory sliding window rate check (single-process only)."""
    now = datetime.now()
    cutoff = now - timedelta(seconds=window_seconds)
    history = [t for t in _fallback_store[key] if t > cutoff]
    if len(history) >= limit:
        return False
    history.append(now)
    _fallback_store[key] = history
    return True


def rate_limit(requests_per_minute: int = 5):
    """
    Creates a production-ready rate limiting dependency.

    Uses Redis sliding window when REDIS_URL is set; falls back to in-memory
    for local development.

    Args:
        requests_per_minute: Maximum requests allowed per user/path per 60s
    """
    async def limit(
        request: Request,
        current_user: User = Depends(get_current_user)
    ):
        key = f"ratelimit:{current_user.id}:{request.url.path}"
        redis = _get_redis()

        try:
            if redis and await redis_cb.is_allowed():
                start_time = time.time()
                try:
                    allowed = await asyncio.wait_for(
                        _check_redis_limit(redis, key, requests_per_minute, window_seconds=60),
                        timeout=3.0
                    )
                    await redis_cb.record_success((time.time() - start_time) * 1000)
                except asyncio.TimeoutError:
                    logger.error("Rate limiter: Redis check TIMEOUT (3s). Failing OPEN.")
                    await redis_cb.record_failure(is_timeout=True)
                    allowed = True # Fail open
                except Exception as e:
                    logger.error(f"Rate limiter: Redis request FAILED: {e}. Failing OPEN.")
                    await redis_cb.record_failure()
                    allowed = True # Fail open
            else:
                # Fail open to prioritize availability over strict limiting
                if not redis:
                    logger.warning("Rate limiter: Redis unavailable (Circuit OPEN/Degraded). Passing request (Fail-Open).")
                allowed = True
        except Exception as exc:
            logger.error(f"Rate limiter unexpected error (failing open): {exc}")
            allowed = True

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please wait before making more requests.",
                headers={"Retry-After": "60"},
            )

    return limit

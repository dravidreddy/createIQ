"""
Security Utils — Rate limiting and input validation for AI services.

Note: Authentication is handled entirely by Firebase (see utils/firebase_auth.py).
This module retains only rate limiting and input sanitization.
"""

import logging
import time
from typing import Optional
import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SecurityLayer:
    """
    Provides lightweight rate limiting and input safety checks.
    """

    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def check_rate_limit(self, user_id: str, limit: int = 50, window_sec: int = 60) -> bool:
        """
        Sliding window rate limit using Redis sorted sets.
        """
        r = await self._get_redis()
        key = f"rl:user:{user_id}:global"
        now = time.time()

        # Cleanup old entries
        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, now - window_sec)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_sec + 10)

        results = await pipe.execute()
        current_count = results[2]

        if current_count > limit:
            logger.warning(f"SecurityLayer: Rate limit hit for user {user_id} ({current_count}/{limit})")
            return False

        return True

    @staticmethod
    def validate_input(text: str, max_length: int = 10000) -> bool:
        """
        Basic input validation to prevent massive payloads or obvious attacks.
        """
        if not text or len(text) > max_length:
            return False

        # Basic check for common injection patterns (highly simplified)
        forbidden_patterns = ["<script>", "javascript:", "DROP TABLE"]
        if any(pattern in text for pattern in forbidden_patterns):
            logger.warning("SecurityLayer: Potential injection pattern detected in input")
            return False

        return True

security_layer = SecurityLayer()

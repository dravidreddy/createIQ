"""
Security Utils — Rate limiting and input validation for AI services.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
import redis.asyncio as redis
import uuid
from datetime import datetime, timedelta, timezone

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Security context for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

# ─── Password Operations ────────────────────────────────────────

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# ─── JWT Token Management ───────────────────────────────────────

def create_tokens(user_id: str) -> Tuple[str, str, int]:
    """Create access and refresh tokens for a user ID."""
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
    
    jti = str(uuid.uuid4())
    access_token = _create_jwt_token(
        data={"sub": user_id, "type": "access", "jti": jti},
        expires_delta=access_token_expires
    )
    refresh_token = _create_jwt_token(
        data={"sub": user_id, "type": "refresh", "jti": jti},
        expires_delta=refresh_token_expires
    )
    
    return access_token, refresh_token, int(access_token_expires.total_seconds())

def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """Verify a token and return the user ID (sub)."""
    try:
        # Add 10s leeway to handle clock skew across distributed systems
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=[settings.algorithm],
            options={"leeway": 10}
        )
        if payload.get("type") != token_type:
            logger.warning(f"JWT: Type mismatch. Expected {token_type}, got {payload.get('type')}")
            return None
        return payload.get("sub")
    except JWTError as e:
        logger.warning(f"JWT: Verification failed: {str(e)}")
        return None

def _create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = int(time.time())
    if expires_delta:
        expire = now + int(expires_delta.total_seconds())
    else:
        expire = now + (15 * 60)
    
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now
    })
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

"""
Cost Tracking Service — Persistent real-time cost monitoring.

Uses Redis for atomic increments (high concurrency) and 
synchronizes with MongoDB (Beanie) for long-term analytics.
"""

import logging
from typing import Optional
import redis.asyncio as redis
from datetime import datetime

from app.config import get_settings
from app.models.job_metrics import JobMetrics
from app.utils.determinism import get_now

logger = logging.getLogger(__name__)
settings = get_settings()

class CostTrackingService:
    """
    Handles persistence of cost metrics across Redis and MongoDB.
    """

    _redis: Optional[redis.Redis] = None

    @classmethod
    async def get_redis(cls) -> redis.Redis:
        """Get or initialize the Redis client."""
        if cls._redis is None:
            cls._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return cls._redis

    @classmethod
    async def check_and_increment_budget(
        cls,
        user_id: str,
        cost_cents: float,
        limit_cents: float
    ) -> bool:
        """
        Atomically check if adding cost_cents exceeds limit_cents for the user today.
        If under limit, increment and return True. Otherwise return False.
        Uses Redis Lua script for atomicity to prevent race conditions.
        """
        r = await cls.get_redis()
        today = get_now().strftime("%Y-%m-%d")
        day_key = f"cost:user:{user_id}:daily:{today}"
        
        # Lua Script: 
        # KEYS[1]: day_key
        # ARGV[1]: limit_cents
        # ARGV[2]: cost_cents
        lua_script = """
        local current = tonumber(redis.call('GET', KEYS[1]) or "0")
        local limit = tonumber(ARGV[1])
        local cost = tonumber(ARGV[2])
        
        if current + cost > limit then
            return 0
        else
            redis.call('INCRBYFLOAT', KEYS[1], cost)
            redis.call('EXPIRE', KEYS[1], 172800) -- 2 days TTL
            return 1
        end
        """
        
        result = await r.eval(lua_script, 1, day_key, limit_cents, cost_cents)
        return bool(result)

    @classmethod
    async def record_execution_cost(
        cls,
        cost_cents: float,
        user_id: str,
        project_id: str,
        job_id: str,
        model_id: str
    ) -> None:
        """
        Record cost in Redis and sync to DB.
        Note: Daily user cap is handled via check_and_increment_budget separately now 
        if fine-grained enforcement is needed, but we still record cumulative here.
        """
        r = await cls.get_redis()
        
        try:
            async with r.pipeline(transaction=True) as pipe:
                pipe.incrbyfloat(f"cost:user:{user_id}", cost_cents)
                pipe.incrbyfloat(f"cost:project:{project_id}", cost_cents)
                pipe.incrbyfloat(f"cost:job:{job_id}", cost_cents)
                await pipe.execute()
        except Exception as e:
            logger.error(f"CostTrackingService: failed to sync to Redis: {e}")

        # Sync to MongoDB (Beanie)
        try:
            metrics = await JobMetrics.find_one(JobMetrics.job_id == job_id)
            if metrics:
                metrics.total_cost_cents = float(metrics.total_cost_cents or 0.0) + cost_cents
                metrics.updated_at = get_now()
                await metrics.save()
            else:
                await JobMetrics(
                    job_id=job_id,
                    total_cost_cents=cost_cents,
                    created_at=get_now(),
                    updated_at=get_now()
                ).insert()
        except Exception as e:
            logger.error(f"CostTrackingService: failed to sync to MongoDB: {e}")

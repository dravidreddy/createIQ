"""
Circuit Breaker — Provider-level health tracking for LLM providers.

Tracks consecutive failures per provider and trips after exceeding
the configured threshold. Auto-recovers after a cooldown period.
"""

import time
import logging
import json
from typing import Optional
import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CircuitBreaker:
    """
    Redis-backed persistent circuit breaker for LLM provider health.
    Ensures provider status survives process restarts and is shared across instances.

    States:
        CLOSED     — healthy, requests pass through
        OPEN       — tripped, requests are rejected immediately
        HALF_OPEN  — cooldown elapsed, next request is a test probe
    """

    def __init__(
        self,
        provider_name: str,
        failure_threshold: Optional[int] = None,
        cooldown_sec: Optional[int] = None,
    ):
        self.name = provider_name
        self.failure_threshold = failure_threshold or self._get_threshold()
        self.cooldown_sec = cooldown_sec or settings.cb_cooldown_default
        self.redis_key = f"cb:provider:{provider_name}"
        self._redis: Optional[redis.Redis] = None
        self._local_state: dict = {
            "state": "CLOSED",
            "failure_count": 0,
            "last_failure_time": 0.0,
            "probe_locked": "false" 
        }
        self._redis_offline = False

    def _get_threshold(self) -> int:
        """Fetch provider-specific threshold from settings."""
        # Using simple name mapping for now
        if "groq" in self.name.lower():
            return settings.cb_threshold_groq
        if any(p in self.name.lower() for p in ["openai", "claude", "gpt"]):
            return settings.cb_threshold_premium
        return settings.cb_threshold_default

    async def _get_redis(self) -> Optional[redis.Redis]:
        if self._redis_offline:
            return None
        if self._redis is None:
            try:
                self._redis = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
            except Exception as e:
                logger.warning(f"CircuitBreaker[{self.name}]: Redis connection failed, falling back to in-memory: {e}")
                self._redis_offline = True
                return None
        return self._redis

    async def _get_state(self) -> dict:
        r = await self._get_redis()
        if r is None:
            return self._local_state
            
        try:
            data = await r.hgetall(self.redis_key)
            if not data:
                return {
                    "state": "CLOSED",
                    "failure_count": 0,
                    "last_failure_time": 0.0,
                    "probe_locked": "false" 
                }
            # Convert types
            data["failure_count"] = int(data.get("failure_count", 0))
            data["last_failure_time"] = float(data.get("last_failure_time", 0.0))
            return data
        except Exception as e:
            logger.warning(f"CircuitBreaker[{self.name}]: Redis read failed: {e}")
            self._redis_offline = True
            return self._local_state

    async def _save_state(self, state_dict: dict) -> None:
        self._local_state = state_dict # Always update local cache
        r = await self._get_redis()
        if r is None:
            return
            
        try:
            await r.hset(self.redis_key, mapping=state_dict)
        except Exception as e:
            logger.warning(f"CircuitBreaker[{self.name}]: Redis write failed: {e}")
            self._redis_offline = True

    async def is_open(self) -> bool:
        """Check if the circuit is open (provider unhealthy)."""
        try:
            data = await self._get_state()
            state = data["state"]
            
            if state == "OPEN":
                # Use wall-clock time for shared Redis state
                elapsed = time.time() - data["last_failure_time"]
                if elapsed >= self.cooldown_sec:
                    # Transition to HALF_OPEN
                    data["state"] = "HALF_OPEN"
                    await self._save_state(data)
                    logger.info(f"CircuitBreaker[{self.name}]: entering HALF_OPEN (cooldown elapsed)")
                    return False
                return True
            
            if state == "HALF_OPEN":
                # In HALF_OPEN, we only allow ONE request through at a time (the probe)
                if data.get("probe_locked") == "true":
                    logger.debug(f"CircuitBreaker[{self.name}]: blocked additional probe while in HALF_OPEN")
                    return True 
                
                data["probe_locked"] = "true"
                await self._save_state(data)
                return False
                
            return False
        except Exception as e:
            logger.error(f"CircuitBreaker[{self.name}]: is_open error (fail-closed): {e}")
            return False # Fail-open (healthy) on structural errors

    async def record_success(self) -> None:
        """Record a successful request and recover/reset."""
        try:
            data = await self._get_state()
            state = data["state"]
            
            if state == "HALF_OPEN":
                data["state"] = "CLOSED"
                data["failure_count"] = 0
                data["probe_locked"] = "false"
                logger.info(f"CircuitBreaker[{self.name}]: CLOSED (probe succeeded)")
            elif state == "CLOSED":
                data["failure_count"] = max(0, data["failure_count"] - 1)
                
            await self._save_state(data)
        except Exception as e:
            logger.warning(f"CircuitBreaker[{self.name}]: record_success failed: {e}")

    async def record_failure(self) -> None:
        """Record a failed request and trip circuit if threshold reached."""
        try:
            data = await self._get_state()
            state = data["state"]
            
            data["failure_count"] += 1
            data["last_failure_time"] = time.time()
            data["probe_locked"] = "false" # Release lock on failure too

            if state == "HALF_OPEN":
                data["state"] = "OPEN"
                logger.warning(f"CircuitBreaker[{self.name}]: OPEN (probe failed)")
            elif data["failure_count"] >= self.failure_threshold:
                data["state"] = "OPEN"
                logger.warning(f"CircuitBreaker[{self.name}]: OPEN (threshold reached: {data['failure_count']})")
                
            await self._save_state(data)
        except Exception as e:
            logger.warning(f"CircuitBreaker[{self.name}]: record_failure failed: {e}")

    async def get_stats(self) -> dict:
        data = await self._get_state()
        return {
            "name": self.name,
            "threshold": self.failure_threshold,
            "redis_online": not self._redis_offline,
            **data
        }

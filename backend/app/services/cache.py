import hashlib
import json
import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta

import redis.asyncio as redis
from cachetools import TTLCache

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheService:
    """
    Redis-backed cache service for reducing API costs and latency.
    Falls back to in-memory TTLCache if Redis is unavailable.
    """
    
    def __init__(
        self,
        maxsize: int = 1000,
        ttl_seconds: int = 3600  # 1 hour default
    ):
        self.ttl = ttl_seconds
        self._redis: Optional[redis.Redis] = None
        self._local_cache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
        self.stats = {"hits": 0, "misses": 0, "sets": 0}
        
    async def _get_redis(self) -> Optional[redis.Redis]:
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    settings.redis_url, 
                    decode_responses=True,
                    socket_timeout=2.0
                )
                await self._redis.ping()
            except Exception as e:
                logger.warning(f"CacheService: Redis unavailable, using in-memory: {e}")
                self._redis = False # Mark as failed
        return self._redis if self._redis is not False else None

    def _make_key(self, namespace: str, key: str) -> str:
        combined = f"{namespace}:{key}"
        return hashlib.md5(combined.encode()).hexdigest()

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        cache_key = self._make_key(namespace, key)
        r = await self._get_redis()
        
        value = None
        if r:
            try:
                raw = await r.get(cache_key)
                value = json.loads(raw) if raw else None
            except Exception as e:
                logger.error(f"CacheService: Redis get error: {e}")
        else:
            value = self._local_cache.get(cache_key)
            
        if value is not None:
            self.stats["hits"] += 1
            logger.debug(f"Cache hit: {namespace}:{key[:20]}...")
        else:
            self.stats["misses"] += 1
            logger.debug(f"Cache miss: {namespace}:{key[:20]}...")
            
        return value

    async def set(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None):
        cache_key = self._make_key(namespace, key)
        r = await self._get_redis()
        exp = ttl or self.ttl
        
        if r:
            try:
                await r.set(cache_key, json.dumps(value), ex=exp)
            except Exception as e:
                logger.error(f"CacheService: Redis set error: {e}")
        else:
            self._local_cache[cache_key] = value
            
        self.stats["sets"] += 1

    async def delete(self, namespace: str, key: str):
        cache_key = self._make_key(namespace, key)
        r = await self._get_redis()
        if r:
            await r.delete(cache_key)
        else:
            self._local_cache.pop(cache_key, None)

    def get_stats(self) -> dict:
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0
        return {
            **self.stats,
            "hit_rate": round(hit_rate, 4),
            "backend": "redis" if self._redis else "in-memory"
        }


_cache_instance: Optional[CacheService] = None

def get_cache() -> CacheService:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
    return _cache_instance


# Default TTLs based on content type
TTL_MAP = {
    "hook": 3600,       # 1 hour
    "script": 21600,    # 6 hours
    "strategy": 86400,  # 24 hours
    "default": 3600
}


async def cache_llm_response(
    messages: list, 
    response_data: dict, 
    task_type: str = "default",
    **kwargs
):
    """Cache serialized LLM response with content-aware TTL."""
    key = hash_prompt(messages, task_type=task_type, **kwargs)
    ttl = TTL_MAP.get(task_type, TTL_MAP["default"])
    await get_cache().set("llm", key, response_data, ttl=ttl)


async def get_cached_llm_response(
    messages: list, 
    task_type: str = "default",
    **kwargs
) -> Optional[dict]:
    """Get cached serialized LLM response (scoped)."""
    key = hash_prompt(messages, task_type=task_type, **kwargs)
    return await get_cache().get("llm", key)


def hash_prompt(
    messages: list, 
    model_id: str = "unknown",
    task_type: str = "default",
    user_id: str = "anonymous",
    project_id: str = "default",
    params: dict = None
) -> str:
    """
    Create a scoped hash of LLM messages for caching.
    Prevents cross-user leakage and ensures parameter sensitivity.
    """
    # Handle LLMMessage objects or dicts
    processed_msgs = []
    for m in messages:
        if hasattr(m, "dict"):
            processed_msgs.append(m.dict())
        else:
            processed_msgs.append(m)

    payload = {
        "messages": processed_msgs,
        "model_id": model_id,
        "task_type": task_type,
        "user_id": user_id,
        "project_id": project_id,
        "params": params or {},
        "v": "1.1" # Internal cache version
    }
    
    content = json.dumps(payload, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()

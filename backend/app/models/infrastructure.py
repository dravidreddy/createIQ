"""
Infrastructure Layer — Cloud Managed Services (Upstash & Qdrant Cloud)

Handles singleton client lifecycle, connection pooling, and health pings.
Now includes:
- 3-State Circuit Breaker (CLOSED, OPEN, HALF-OPEN)
- Metrics Tracking (failures, timeouts, trips)
- Trace ID Awareness (ready for middleware)
- Rate-Limited Logging Utility
"""

import logging
import asyncio
import time
import uuid
import backoff
import redis.asyncio as redis
import socket
from enum import Enum
from typing import Optional, Any, Dict
from qdrant_client import AsyncQdrantClient
from app.config import get_settings
from app.utils.logging import infra_logger
# from app.memory.vector_store import initialize_vector_store (Removed to fix circular import)

# (Use infra_logger for rate-limited ops)

# --- Resilience Enums & Metrics ---
class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # System is down, fast-fail active
    HALF_OPEN = "half_open"  # Testing recovery with 1 probe

class ServiceMetrics:
    def __init__(self):
        self.failures = 0
        self.trips = 0
        self.timeouts = 0
        self.latency_ms = 0.0

# --- Circuit Breaker Class ---
class CircuitBreaker:
    def __init__(self, name: str, threshold: int = 3, cooldown: float = 60.0):
        self.name = name
        self.threshold = threshold
        self.cooldown = cooldown
        self.state = CircuitState.CLOSED
        self.metrics = ServiceMetrics()
        self.last_failure_time = 0.0
        self._lock = asyncio.Lock()

    async def is_allowed(self) -> bool:
        """Check if a request is allowed to pass based on state."""
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                # Check for cooldown expiry
                if time.time() - self.last_failure_time > self.cooldown:
                    logger.info(f"Circuit Breaker [{self.name}]: Transitioning to HALF-OPEN for recovery probe.")
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            
            if self.state == CircuitState.HALF_OPEN:
                # Only one request allowed in HALF_OPEN to test recovery
                return False
        return False

    async def record_failure(self, is_timeout: bool = False):
        """Record a failure and potentially trip the breaker."""
        async with self._lock:
            self.metrics.failures += 1
            if is_timeout:
                self.metrics.timeouts += 1
            
            self.last_failure_time = time.time()
            if self.state == CircuitState.CLOSED:
                if self.metrics.failures >= self.threshold:
                    logger.error(f"Circuit Breaker [{self.name}]: TRIPPED after {self.threshold} failures. State: OPEN.")
                    self.state = CircuitState.OPEN
                    self.metrics.trips += 1
            elif self.state == CircuitState.HALF_OPEN:
                logger.error(f"Circuit Breaker [{self.name}]: Recovery probe FAILED. Reverting to OPEN.")
                self.state = CircuitState.OPEN

    async def record_success(self, latency_ms: float = 0.0):
        """Record success and potentially close the breaker."""
        async with self._lock:
            self.metrics.latency_ms = latency_ms
            if self.state == CircuitState.HALF_OPEN:
                logger.info(f"Circuit Breaker [{self.name}]: Recovery probe SUCCEEDED. Resetting to CLOSED.")
                self.state = CircuitState.CLOSED
                self.metrics.failures = 0
            elif self.state == CircuitState.CLOSED:
                self.metrics.failures = 0 

# --- Singleton Clients & Breakers ---
_redis_client: Optional[redis.Redis] = None
_qdrant_client: Optional[AsyncQdrantClient] = None

redis_cb = CircuitBreaker("Redis", threshold=3, cooldown=60.0)
qdrant_cb = CircuitBreaker("Qdrant", threshold=3, cooldown=60.0)

# --- Global Health States (Legacy Compatibility) ---
REDIS_READY = False
QDRANT_READY = False
REDIS_LATENCY_MS = 0.0
QDRANT_LATENCY_MS = 0.0

def get_redis() -> Optional[redis.Redis]:
    """Get the singleton Redis client instance (Upstash)."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        if not settings.redis_url:
            raise ValueError("REDIS_URL is required but missing from configuration")
        
        url = settings.redis_url
        
        # Upstash Specific Logic: Enforce TLS/rediss for cloud
        if ".upstash.io" in url and url.startswith("redis://"):
            infra_logger.warning("Upstash URL detected without SSL protocol. Forcing 'rediss://'.")
            url = url.replace("redis://", "rediss://", 1)
        
        _redis_client = redis.from_url(
            url,
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            retry_on_timeout=True,
            max_connections=50
        )
    return _redis_client

def get_qdrant() -> Optional[AsyncQdrantClient]:
    """Get the singleton Qdrant Cloud client instance with validation."""
    global _qdrant_client
    if _qdrant_client is None:
        settings = get_settings()
        if not settings.qdrant_url:
            raise ValueError("CRITICAL: QDRANT_URL is missing from configuration. Cloud vector memory requires a valid endpoint.")
        if not settings.qdrant_api_key:
            raise ValueError("CRITICAL: QDRANT_API_KEY is missing from configuration.")
        
        # Prevent silent local fallback if Cloud URL is intended
        is_cloud = "qdrant.io" in settings.qdrant_url
        if is_cloud and "localhost" in settings.qdrant_url:
            raise ValueError(f"CRITICAL: Contradictory QDRANT_URL configuration: {settings.qdrant_url}")

        # [MANDATORY FIX] Version Guard for API compatibility (Ensures 'query_points' exists)
        try:
            import importlib.metadata
            version_str = importlib.metadata.version("qdrant-client")
            v = version_str.split(".")
            if int(v[0]) < 1 or (int(v[0]) == 1 and int(v[1]) < 10):
                infra_logger.warning(f"UNSUPPORTED QDRANT CLIENT VERSION: {version_str}. Upgrade to 1.10+ required for query_points support.")
        except Exception:
            # Fallback if version cannot be determined
            pass

        _qdrant_client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=5.0
        )
    return _qdrant_client

@backoff.on_exception(
    backoff.expo,
    (redis.ConnectionError, Exception),
    max_tries=2,
    logger=infra_logger.logger
)
async def probe_redis():
    """Perform a real-world ping test for Redis."""
    global REDIS_READY, REDIS_LATENCY_MS
    r = get_redis()
    if not r:
        return False
    
    start = time.time()
    await r.ping()
    latency = (time.time() - start) * 1000
    REDIS_LATENCY_MS = latency
    REDIS_READY = True
    await redis_cb.record_success(latency)
    return True

@backoff.on_exception(
    backoff.expo,
    (Exception),
    max_tries=2,
    logger=infra_logger.logger
)
async def probe_qdrant():
    """Perform DNS pre-flight and real-world collection check for Qdrant Cloud."""
    global QDRANT_READY, QDRANT_LATENCY_MS
    settings = get_settings()
    
    # 1. DNS Pre-flight Check (Multi-stage)
    if "qdrant.io" in settings.qdrant_url:
        host = settings.qdrant_url.replace("https://", "").replace("http://", "").split(":")[0].split("/")[0]
        try:
            infra_logger.info(f"Performing DNS pre-flight for Qdrant Cloud: {host}")
            socket.getaddrinfo(host, None)
        except socket.gaierror as e:
            error_msg = (
                f"CRITICAL: Qdrant Cloud DNS resolution FAILED for '{host}': {e}. "
                f"This often means your network's default DNS server is refusing queries to external cloud endpoints. "
                f"Consider using Google DNS (8.8.8.8) or Cloudflare DNS (1.1.1.1)."
            )
            infra_logger.error(error_msg)
            raise RuntimeError(error_msg)

    q = get_qdrant()
    if not q:
        return False
        
    start = time.time()
    await q.get_collections()
    latency = (time.time() - start) * 1000
    QDRANT_LATENCY_MS = latency
    QDRANT_READY = True
    await qdrant_cb.record_success(latency)
    return True

async def init_infrastructure():
    """Initialise cloud infrastructure with state-aware probing and strict fail-fast validation."""
    global REDIS_READY, QDRANT_READY
    settings = get_settings()
    
    infra_logger.info("Initializing Infrastructure resilience handshake...", key="infra_init")
    
    # 1. MongoDB Check (Integrated)
    try:
        from app.models.database import init_db
        await init_db()
        infra_logger.info("✓ MongoDB Atlas - Connected & Verified")
    except Exception as e:
        error_msg = f"CRITICAL: MongoDB Initialization FAILED: {e}"
        infra_logger.critical(error_msg, key="mongo_fail")
        raise RuntimeError(error_msg)

    # 2. Redis Probe
    if await redis_cb.is_allowed():
        try:
            await probe_redis()
            infra_logger.info(f"✓ Redis (Upstash) - State: {redis_cb.state.value} | Latency: {REDIS_LATENCY_MS:.2f}ms")
        except Exception as e:
            await redis_cb.record_failure()
            REDIS_READY = False
            error_msg = f"CRITICAL: Redis (Upstash) Probe FAILED. State: {redis_cb.state.value} | Error: {e}"
            infra_logger.critical(error_msg, key="redis_fail")
            # Failure is always fatal in this audit phase
            raise RuntimeError(error_msg)
    else:
        REDIS_READY = False
        raise RuntimeError(f"CRITICAL: Redis Circuit Breaker is {redis_cb.state.value} on startup.")

    # 3. Qdrant Probe & Initialization
    if await qdrant_cb.is_allowed():
        try:
            await probe_qdrant()
            infra_logger.info(f"✓ Qdrant Cloud - State: {qdrant_cb.state.value} | Latency: {QDRANT_LATENCY_MS:.2f}ms")
            
            # Eager initialization moved to main.py to fix circular import
            # await initialize_vector_store()
            
        except Exception as e:
            await qdrant_cb.record_failure()
            QDRANT_READY = False
            error_msg = f"CRITICAL: Qdrant Cloud Initialization FAILED. State: {qdrant_cb.state.value} | Error: {e}"
            infra_logger.critical(error_msg, key="qdrant_fail")
            # Failure is always fatal in this audit phase
            raise RuntimeError(error_msg)
    else:
        QDRANT_READY = False
        raise RuntimeError(f"CRITICAL: Qdrant Circuit Breaker is {qdrant_cb.state.value} on startup.")

async def close_infrastructure():
    """Gracefully close sessions."""
    global _redis_client, _qdrant_client
    if _redis_client:
        await _redis_client.close()
    if _qdrant_client:
        await _qdrant_client.close()
    infra_logger.info("Infrastructure sessions closed.")

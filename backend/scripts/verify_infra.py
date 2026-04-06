import asyncio
import os
import sys
import logging

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_cloud_infra():
    settings = get_settings()
    results = {}
    
    print("="*60)
    print(" CreatorIQ Cloud Infrastructure Verification")
    print("="*60)

    # 1. Qdrant Cloud Test
    from qdrant_client import AsyncQdrantClient
    try:
        print(f"Connecting to Qdrant: {settings.qdrant_url}...")
        client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        collections = await client.get_collections()
        print(f"✓ Qdrant Cloud: PASS (Found {len(collections.collections)} collections)")
        results["qdrant"] = "PASS"
    except Exception as e:
        print(f"✗ Qdrant Cloud: FAIL - {e}")
        results["qdrant"] = f"FAIL: {e}"

    # 2. Redis Cloud Test
    import redis.asyncio as redis
    try:
        print(f"Connecting to Redis: {settings.redis_url}...")
        r = redis.from_url(settings.redis_url, socket_timeout=5.0)
        pong = await r.ping()
        print(f"✓ Redis Cloud: PASS (Ping: {pong})")
        results["redis"] = "PASS"
    except Exception as e:
        print(f"✗ Redis Cloud: FAIL - {e}")
        results["redis"] = f"FAIL: {e}"

    print("="*60)
    return results

if __name__ == "__main__":
    asyncio.run(verify_cloud_infra())

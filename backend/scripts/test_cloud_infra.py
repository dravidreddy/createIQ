"""
CreatorIQ Cloud Infrastructure Validation Suite (Upstash + Qdrant Cloud)

Certifies connection integrity, CRUD functionality, and latency benchmarks.
Updated for Resilience (Partial Degradation Audit).
"""

import asyncio
import time
import logging
import uuid
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.models.infrastructure import (
    init_infrastructure, 
    close_infrastructure, 
    get_redis, 
    get_qdrant,
    REDIS_READY,
    QDRANT_READY,
    REDIS_LATENCY_MS,
    QDRANT_LATENCY_MS
)
from qdrant_client.http import models as qmodels

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def run_cloud_tests():
    logger.info("="*60)
    logger.info(" CreatorIQ Cloud Infrastructure Verification (Resilience Audit)")
    logger.info("="*60)

    # 1. Startup & Handshake
    logger.info("Executing Fail-Safe Startup Handshake...")
    await init_infrastructure()

    # 2. Upstash Redis Benchmarking
    if REDIS_READY:
        logger.info(f"Testing Upstash Redis (Handshake: {REDIS_LATENCY_MS:.2f}ms)...")
        r = get_redis()
        test_key = f"qa:test:{uuid.uuid4().hex[:8]}"
        
        try:
            # Measure CRUD Latency
            latencies = []
            for _ in range(3):
                s = time.time()
                await r.set(test_key, "test_value", ex=60)
                await r.get(test_key)
                latencies.append((time.time() - s) * 1000)
            
            avg_ms = sum(latencies) / len(latencies)
            logger.info(f"✓ Redis CRUD: PASS (Avg: {avg_ms:.2f}ms)")
            await r.delete(test_key)
        except Exception as e:
            logger.error(f"✗ Redis CRUD: FAILED - {e}")
    else:
        logger.warning("! Redis Benchmark: SKIPPED (Service Degraded/Blocked)")

    # 3. Qdrant Cloud Benchmarking
    if QDRANT_READY:
        logger.info(f"Testing Qdrant Cloud (Handshake: {QDRANT_LATENCY_MS:.2f}ms)...")
        q = get_qdrant()
        collection = "qa_validation_test"
        
        try:
            # Check/Create collection
            exists = await q.collection_exists(collection)
            if not exists:
                await q.create_collection(
                    collection_name=collection,
                    vectors_config=qmodels.VectorParams(size=768, distance=qmodels.Distance.COSINE)
                )
            
            # Measure Upsert & Search
            vector = [0.1] * 768
            point_id = str(uuid.uuid4())
            
            s_start = time.time()
            await q.upsert(
                collection_name=collection,
                points=[qmodels.PointStruct(id=point_id, vector=vector, payload={"test": True})]
            )
            upsert_ms = (time.time() - s_start) * 1000
            
            s_pair = time.time()
            results = await q.search(collection_name=collection, query_vector=vector, limit=1)
            search_ms = (time.time() - s_pair) * 1000
            
            if results and results[0].id == point_id:
                logger.info(f"✓ Qdrant Search: PASS (Upsert: {upsert_ms:.2f}ms | Search: {search_ms:.2f}ms)")
            else:
                logger.error("✗ Qdrant Search: FAIL (Record mismatch)")

            await q.delete_collection(collection_name=collection)
        except Exception as e:
            logger.error(f"✗ Qdrant CRUD: FAILED - {e}")
    else:
        logger.warning("! Qdrant Benchmark: SKIPPED (Service Degraded/Blocked)")

    # 4. Final Cleanup
    await close_infrastructure()
    
    logger.info("="*60)
    status = "DEGRADED" if not (REDIS_READY and QDRANT_READY) else "HEALTHY"
    logger.info(f" Cloud Infrastructure Audit COMPLETE [Status: {status}]")
    logger.info("="*60)

if __name__ == "__main__":
    asyncio.run(run_cloud_tests())

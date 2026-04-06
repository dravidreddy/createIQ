"""
CreatorIQ Audit Phase 1: Cloud Connection Validation
Verifies MongoDB, Redis, and Qdrant Cloud connectivity and CRUD operations.
"""

import asyncio
import time
import uuid
import sys
import os
import logging
from typing import Dict

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.database import init_db, close_db
from app.models.user import User
from app.models.infrastructure import (
    init_infrastructure,
    close_infrastructure,
    get_redis,
    get_qdrant,
    REDIS_READY,
    QDRANT_READY
)
from qdrant_client.http import models as qmodels

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AuditPhase1")

async def test_mongodb() -> Dict:
    logger.info("--- Testing MongoDB Atlas ---")
    start = time.time()
    try:
        await init_db()
        test_email = f"audit_test_{uuid.uuid4().hex[:8]}@example.com"
        
        # Create
        user = User(email=test_email, display_name="Audit User", hashed_password="hashed_password")
        await user.insert()
        
        # Read
        fetched = await User.find_one(User.email == test_email)
        if not fetched or fetched.display_name != "Audit User":
            raise ValueError("Data mismatch in MongoDB")
            
        # Delete
        await fetched.delete()
        
        latency = (time.time() - start) * 1000
        logger.info(f"✓ MongoDB: PASS (Latency: {latency:.2f}ms)")
        return {"status": "PASS", "latency_ms": latency}
    except Exception as e:
        logger.error(f"✗ MongoDB: FAIL - {e}")
        return {"status": "FAIL", "error": str(e)}
    finally:
        await close_db()

async def test_redis() -> Dict:
    logger.info("--- Testing Upstash Redis ---")
    start = time.time()
    try:
        await init_infrastructure()
        if not REDIS_READY:
            raise ConnectionError("Redis not ready after handshake")
            
        r = get_redis()
        test_key = f"audit:test:{uuid.uuid4().hex[:8]}"
        
        # Set
        await r.set(test_key, "audit_value", ex=10) # 10s TTL
        
        # Get
        val = await r.get(test_key)
        if val != "audit_value":
            raise ValueError(f"Data mismatch in Redis: {val}")
            
        # TTL check
        ttl = await r.ttl(test_key)
        if ttl <= 0:
            raise ValueError(f"TTL error in Redis: {ttl}")
            
        # Delete
        await r.delete(test_key)
        
        latency = (time.time() - start) * 1000
        logger.info(f"✓ Redis: PASS (Latency: {latency:.2f}ms)")
        return {"status": "PASS", "latency_ms": latency}
    except Exception as e:
        logger.error(f"✗ Redis: FAIL - {e}")
        return {"status": "FAIL", "error": str(e)}

async def test_qdrant() -> Dict:
    logger.info("--- Testing Qdrant Cloud ---")
    start = time.time()
    try:
        # infrastructure already initialized in test_redis
        if not QDRANT_READY:
            raise ConnectionError("Qdrant not ready after handshake")
            
        q = get_qdrant()
        collection = "audit_validation_test"
        
        # Check/Create
        if not await q.collection_exists(collection):
            await q.create_collection(
                collection_name=collection,
                vectors_config=qmodels.VectorParams(size=128, distance=qmodels.Distance.COSINE)
            )
            
        point_id = str(uuid.uuid4())
        vector = [0.1] * 128
        
        # Upsert
        await q.upsert(
            collection_name=collection,
            points=[qmodels.PointStruct(id=point_id, vector=vector, payload={"audit": True})]
        )
        
        # Search
        res = await q.search(collection_name=collection, query_vector=vector, limit=1)
        if not res or res[0].id != point_id:
            raise ValueError("Data mismatch in Qdrant")
            
        # Delete collection
        await q.delete_collection(collection_name=collection)
        
        latency = (time.time() - start) * 1000
        logger.info(f"✓ Qdrant: PASS (Latency: {latency:.2f}ms)")
        return {"status": "PASS", "latency_ms": latency}
    except Exception as e:
        logger.error(f"✗ Qdrant: FAIL - {e}")
        return {"status": "FAIL", "error": str(e)}
    finally:
        await close_infrastructure()

async def run_phase1():
    print("\n" + "="*50)
    print(" PHASE 1: CLOUD CONNECTION VALIDATION")
    print("="*50)
    
    results = {}
    results["mongo"] = await test_mongodb()
    results["redis"] = await test_redis()
    results["qdrant"] = await test_qdrant()
    
    print("\nSUMMARY:")
    for svc, res in results.items():
        status = res["status"]
        lat = f"({res.get('latency_ms', 0):.2f}ms)" if status == "PASS" else f"ERR: {res.get('error')}"
        print(f"  {svc.upper():8}: {status} {lat}")
    print("="*50 + "\n")
    
    if any(res["status"] == "FAIL" for res in results.values()):
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_phase1())

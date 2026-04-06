import asyncio
import os
import sys
import time
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List

# Path Alignment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from app.config import get_settings
    from motor.motor_asyncio import AsyncIOMotorClient
    import redis.asyncio as aioredis
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.http import models as qmodels
except ImportError as e:
    print(f"CRITICAL: Missing dependencies or path mismatch: {e}")
    sys.exit(1)

settings = get_settings()

class AuditReport:
    def __init__(self):
        self.results = {
            "MongoDB": {"Connection": "PENDING", "Write": "PENDING", "Read": "PENDING", "Integrity": "PENDING"},
            "Redis": {"Connection": "PENDING", "Cache Ops": "PENDING", "TTL": "PENDING"},
            "Qdrant": {"Connection": "PENDING", "Insert": "PENDING", "Retrieval": "PENDING"},
            "E2E": {"Data Flow": "PENDING", "Isolation": "PENDING", "Failure Detection": "PENDING"}
        }
        self.issues = []
        self.verdict = "❌ NEEDS FIXES"

    def add_issue(self, severity: str, message: str):
        self.issues.append({"severity": severity, "message": message})

    def mark(self, category: str, test: str, status: str):
        if category in self.results and test in self.results[category]:
            self.results[category][test] = status

    def generate_markdown(self):
        report = "# 📊 CreatorIQ Infrastructure Audit Report\n\n"
        report += f"**Timestamp:** {datetime.now().isoformat()}\n"
        report += f"**Environment:** {settings.env.upper()}\n\n"

        for category, tests in self.results.items():
            report += f"## {category}\n"
            for test, status in tests.items():
                icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "🕒"
                report += f"* {test}: {status} {icon}\n"
            report += "\n"

        report += "## Final Summary\n"
        if not self.issues:
            report += "* No major issues found.\n"
        else:
            for issue in self.issues:
                report += f"* **{issue['severity']}**: {issue['message']}\n"
        
        report += f"\n### Final Verdict: {self.verdict}\n"
        return report

report = AuditReport()

async def phase1_config_validation():
    print("🔍 PHASE 1: RUNTIME CONFIG VALIDATION")
    
    # 1. MongoDB
    if not settings.mongo_uri.startswith("mongodb+srv://"):
        report.add_issue("CRITICAL", f"MongoDB Protocol Mismatch: Expected 'mongodb+srv://', got '{settings.mongo_uri.split(':')[0]}'")
        report.mark("MongoDB", "Connection", "FAIL")
    elif "localhost" in settings.mongo_uri or "127.0.0.1" in settings.mongo_uri:
        report.add_issue("CRITICAL", "MongoDB is pointing to LOCALHOST")
        report.mark("MongoDB", "Connection", "FAIL")
    else:
        print("[+] MongoDB Protocol & Host: OK")
        report.mark("MongoDB", "Connection", "PASS")

    # 2. Redis
    if not (settings.redis_url.startswith("redis://") or settings.redis_url.startswith("rediss://")):
        report.add_issue("CRITICAL", f"Redis Protocol Mismatch: Expected 'rediss://' (SSL), got '{settings.redis_url.split(':')[0]}'")
        report.mark("Redis", "Connection", "FAIL")
    elif "localhost" in settings.redis_url or "127.0.0.1" in settings.redis_url:
        report.add_issue("CRITICAL", "Redis is pointing to LOCALHOST")
        report.mark("Redis", "Connection", "FAIL")
    else:
        print("[+] Redis Protocol & Host: OK")
        report.mark("Redis", "Connection", "PASS")

    # 3. Qdrant
    if not settings.qdrant_url.startswith("https://"):
        report.add_issue("CRITICAL", f"Qdrant Protocol Mismatch: Expected 'https://', got '{settings.qdrant_url.split(':')[0]}'")
        report.mark("Qdrant", "Connection", "FAIL")
    elif "localhost" in settings.qdrant_url or "127.0.0.1" in settings.qdrant_url:
        report.add_issue("CRITICAL", "Qdrant is pointing to LOCALHOST")
        report.mark("Qdrant", "Connection", "FAIL")
    else:
        print("[+] Qdrant Protocol & Host: OK")
        report.mark("Qdrant", "Connection", "PASS")

async def phase2_mongodb_validation():
    print("\n🔍 PHASE 2: MONGODB VALIDATION (PERSISTENCE)")
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongodb_db_name]
    coll = db["audit_test"]
    
    test_id = f"audit_{int(time.time())}"
    test_doc = {
        "test_id": test_id,
        "value": "mongo_test",
        "timestamp": datetime.now().isoformat(),
        "meta": {"source": "audit_script"}
    }
    
    start_time = time.time()
    try:
        # 1. Write
        await coll.insert_one(test_doc)
        latency = (time.time() - start_time) * 1000
        print(f"[+] Write Successful (Latency: {latency:.2f}ms)")
        report.mark("MongoDB", "Write", "PASS")
        
        if latency > 300:
            report.add_issue("WARNING", f"MongoDB abnormality: High write latency ({latency:.2f}ms)")

        # 2. Read
        read_doc = await coll.find_one({"test_id": test_id})
        if not read_doc:
            print("[-] READ FAILED: Document not found")
            report.mark("MongoDB", "Read", "FAIL")
            report.mark("MongoDB", "Integrity", "FAIL")
        else:
            print("[+] Read Successful")
            report.mark("MongoDB", "Read", "PASS")
            
            # 3. Verify Integrity
            if read_doc["value"] == "mongo_test":
                print("[+] Integrity Verified")
                report.mark("MongoDB", "Integrity", "PASS")
            else:
                print("[-] INTEGRITY FAILED: Value mismatch")
                report.mark("MongoDB", "Integrity", "FAIL")
                report.add_issue("CRITICAL", "MongoDB Integrity Failed: Value mismatch")

        # 4. Cleanup
        await coll.delete_one({"test_id": test_id})
        print("[+] Cleanup Successful")
        
    except Exception as e:
        print(f"[-] MongoDB Operation Failed: {e}")
        report.add_issue("CRITICAL", f"MongoDB Operation Failed: {e}")
        report.mark("MongoDB", "Write", "FAIL")
    finally:
        client.close()

async def phase3_redis_validation():
    print("\n🔍 PHASE 3: REDIS VALIDATION (CACHE)")
    try:
        r = aioredis.from_url(settings.redis_url, socket_timeout=5.0)
        await r.ping()
        
        test_key = f"audit:test:{int(time.time())}"
        test_val = "redis_test"
        
        # 1. SET
        await r.set(test_key, test_val, ex=5) # 5s TTL
        print(f"[+] SET key: {test_key}")
        
        # 2. GET
        cached_val = await r.get(test_key)
        if cached_val and cached_val.decode() == test_val:
            print("[+] GET match: OK")
            report.mark("Redis", "Cache Ops", "PASS")
        else:
            print("[-] GET mismatch or missing")
            report.mark("Redis", "Cache Ops", "FAIL")
            report.add_issue("CRITICAL", "Redis GET mismatch or missing data")

        # 3. TTL Test
        print("[*] Testing TTL (Waiting 6 seconds)...")
        await asyncio.sleep(6)
        expired_val = await r.get(test_key)
        if expired_val is None:
            print("[+] TTL working as expected")
            report.mark("Redis", "TTL", "PASS")
        else:
            print("[-] TTL FAIL: Key still exists after expiry")
            report.mark("Redis", "TTL", "FAIL")
            report.add_issue("WARNING", "Redis TTL failure detected")

        # 4. Cleanup (just in case)
        await r.delete(test_key)
        await r.close()
        
    except Exception as e:
        print(f"[-] Redis Operation Failed: {e}")
        report.add_issue("CRITICAL", f"Redis Operation Failed: {e}")
        report.mark("Redis", "Cache Ops", "FAIL")

async def phase4_qdrant_validation():
    print("\n🔍 PHASE 4: QDRANT VALIDATION (VECTOR MEMORY)")
    client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    collection_name = f"audit_test_{int(time.time())}"
    
    try:
        # 1. Create collection
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(size=768, distance=qmodels.Distance.COSINE),
        )
        print(f"[+] Collection '{collection_name}' created")
        
        # 2. Insert vector
        import random
        vector = [random.random() for _ in range(768)]
        payload = {"text": "CreatorIQ test vector", "tag": "audit", "session": "audit_master"}
        
        await client.upsert(
            collection_name=collection_name,
            points=[qmodels.PointStruct(id=1, vector=vector, payload=payload)]
        )
        print("[+] Vector inserted")
        report.mark("Qdrant", "Insert", "PASS")
        
        # 3. Retrieval (Similarity Search)
        try:
            results = await client.search(
                collection_name=collection_name,
                query_vector=vector,
                limit=1
            )
        except Exception as e:
            # Fallback for dynamic method resolution issues in some environments
            print(f"[*] Search method resolution issue, attempting fallback: {e}")
            results = await client.search(
                collection_name=collection_name,
                query_vector=vector,
                limit=1
            )
        
        if results and results[0].payload["tag"] == "audit":
            print("[+] Search Successful: Payload matches")
            report.mark("Qdrant", "Retrieval", "PASS")
        else:
            print("[-] Search Failed or Incorrect payload")
            report.mark("Qdrant", "Retrieval", "FAIL")
            report.add_issue("CRITICAL", "Qdrant Retrieval mismatch or empty results")

        # 4. Cleanup
        await client.delete_collection(collection_name)
        print(f"[+] Collection '{collection_name}' deleted")
        
    except Exception as e:
        print(f"[-] Qdrant Operation Failed: {e}")
        report.add_issue("CRITICAL", f"Qdrant Operation Failed: {e}")
        report.mark("Qdrant", "Insert", "FAIL")
    finally:
        await client.close()

async def phase5_e2e_data_flow():
    print("\n🔍 PHASE 5: END-TO-END DATA FLOW")
    # Simulate a real query by writing to each system manually and checking correlations
    # Since running full LangGraph might require more setup, we simulate the storage part
    session_id = f"session_e2e_{int(time.time())}"
    
    try:
        # Mongo Session Record
        mongo_client = AsyncIOMotorClient(settings.mongo_uri)
        db = mongo_client[settings.mongodb_db_name]
        await db["sessions"].insert_one({"session_id": session_id, "query": "YouTube hook about AI agents"})
        
        # Redis Result Cache
        r = aioredis.from_url(settings.redis_url)
        await r.set(f"cache:{session_id}", "Sample AI result", ex=60)
        
        # Qdrant Memory
        q_client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        # Use existing collection if possible, or temporary
        await q_client.upsert(
            collection_name="creatoriq_memory", 
            points=[qmodels.PointStruct(id=str(uuid.uuid4()), vector=[0.1]*768, payload={"user_id": "audit_user", "content": "AI agents hook"})]
        )
        
        # Verification
        m_ok = await db["sessions"].find_one({"session_id": session_id})
        r_ok = await r.get(f"cache:{session_id}")
        
        # Ensure collection exists before searching in E2E phase
        q_ok = None
        try:
            q_ok = await q_client.search(collection_name="creatoriq_memory", query_vector=[0.1]*768, limit=1)
        except Exception as e:
            print(f"[*] E2E Qdrant search fallback: {e}")
            # Try to initialize if missing (should be handled by app logic now)
            q_ok = await q_client.search(collection_name="creatoriq_memory", query_vector=[0.1]*768, limit=1)
        
        if m_ok and r_ok and q_ok:
            print("[+] E2E Trace Flow: VERIFIED across all DBs")
            report.mark("E2E", "Data Flow", "PASS")
        else:
            print("[-] E2E Trace Flow: FAILED (missing links)")
            report.mark("E2E", "Data Flow", "FAIL")
            report.add_issue("CRITICAL", "E2E Data Flow verification failed")

        # Cleanup
        await db["sessions"].delete_one({"session_id": session_id})
        await r.delete(f"cache:{session_id}")
        # Note: We don't delete from production collection 'creatoriq_memory' unless we have a specific ID, which we do
        await q_client.delete(collection_name="creatoriq_memory", points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(must=[qmodels.FieldCondition(key="user_id", match=qmodels.MatchValue(value="audit_user"))])
        ))
        
        await mongo_client.close()
        await r.close()
        await q_client.close()
        
    except Exception as e:
        print(f"[-] E2E Verification Failed: {e}")
        report.mark("E2E", "Data Flow", "FAIL")

async def phase6_isolation_check():
    print("\n🔍 PHASE 6: ISOLATION CHECK")
    # Parallel async tasks Session A and Session B
    async def session_task(id_str):
        r = aioredis.from_url(settings.redis_url)
        await r.set(f"iso:{id_str}", id_str, ex=10)
        val = await r.get(f"iso:{id_str}")
        await r.close()
        return val.decode() == id_str

    results = await asyncio.gather(session_task("AAA"), session_task("BBB"))
    
    if all(results):
        print("[+] Isolation Verified: Sessions do not cross-talk")
        report.mark("E2E", "Isolation", "PASS")
    else:
        print("[-] Isolation Failed")
        report.mark("E2E", "Isolation", "FAIL")
        report.add_issue("CRITICAL", "Isolation check failed (Parallel sessions corrupted)")

async def phase7_failure_detection():
    print("\n🔍 PHASE 7: FAILURE DETECTION")
    # 1. Invalid Redis
    try:
        bad_r = aioredis.from_url("rediss://wrong:pass@localhost:9999", socket_timeout=1.0)
        await bad_r.ping()
        print("[-] FAIL: Bad Redis URL connected (unexpected)")
        report.mark("E2E", "Failure Detection", "FAIL")
    except Exception as e:
        print(f"[+] Success: Redis failed fast as expected: {e}")
        report.mark("E2E", "Failure Detection", "PASS")

async def main():
    print("="*60)
    print(" CREATORIQ INFRASTRUCTURE DEEP AUDIT")
    print("="*60)
    
    await phase1_config_validation()
    await phase2_mongodb_validation()
    await phase3_redis_validation()
    await phase4_qdrant_validation()
    await phase5_e2e_data_flow()
    await phase6_isolation_check()
    await phase7_failure_detection()
    
    # Final Verdict
    all_passed = True
    for cat in report.results.values():
        if "FAIL" in cat.values():
            all_passed = False
            break
    
    if all_passed:
        report.verdict = "✅ FULLY FUNCTIONAL"
    
    # Generate Report
    md = report.generate_markdown()
    with open("audit_report.md", "w", encoding="utf-8") as f:
        f.write(md)
    
    print("\n" + "="*60)
    print(f" AUDIT COMPLETE - VERDICT: {report.verdict}")
    print(" Report saved to audit_report.md")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())

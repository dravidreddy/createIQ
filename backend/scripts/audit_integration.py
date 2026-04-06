"""
CreatorIQ Audit Phase 2 & 3: Infrastructure Integration & Pipeline Validation
Verifies app health and runs a sample query in "Degraded" mode.
"""

import asyncio
import uuid
import sys
import os
import httpx
from typing import Dict

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# (Note: We usually start the app locally and hit it with httpx/curl)
# But for a fast check, we'll hit the FastAPI TestClient or direct endpoint.

async def check_health() -> Dict:
    print("--- Phase 2: App Health Check ---")
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        try:
            resp = await client.get("/health")
            data = resp.json()
            print(f"Status: {data.get('status')}")
            print(f"Services: {data.get('services')}")
            return data
        except Exception as e:
            print(f"✗ Health Check FAILED: {e} (Ensure app is running on :8000)")
            return {"status": "FAIL", "error": str(e)}

async def run_pipeline_test() -> Dict:
    print("\n--- Phase 3: LLM Pipeline Validation ---")
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        try:
            # We'll use the 'generate' endpoint
            req_body = {
                "project_id": str(uuid.uuid4()), # Test project
                "prompt": "Create a short 1-line YouTube hook about AI agents.",
                "session_id": f"audit_{uuid.uuid4().hex[:8]}"
            }
            resp = await client.post("/api/v1/pipeline/generate", json=req_body)
            if resp.status_code != 200:
                print(f"✗ Pipeline FAILED: {resp.status_code} - {resp.text}")
                return {"status": "FAIL", "code": resp.status_code}
            
            data = resp.json()
            print(f"✓ Pipeline Response Received (Trace: {data.get('_infra_meta', {}).get('trace_id')})")
            print(f"Content: {data.get('content', '')[:100]}...")
            return data
        except Exception as e:
            print(f"✗ Pipeline Execution Error: {e}")
            return {"status": "FAIL", "error": str(e)}

async def run_integration_audit():
    print("="*60)
    print(" PHASE 2 & 3: INTEGRATION & PIPELINE AUDIT")
    print("="*60)
    
    # Check if app is alive
    health = await check_health()
    
    # Try a generation
    pipeline = await run_pipeline_test()
    
    print("\n" + "="*60)
    print(f" Health Status:  {health.get('status', 'OFFLINE')}")
    print(f" Pipeline:       {'PASS' if pipeline.get('status') != 'FAIL' else 'FAIL'}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_integration_audit())

"""
DEVTOOLS - Verify LLM System
DO NOT import in production code.
"""
import asyncio
import logging
import json
import redis.asyncio as redis
from app.llm.base import LLMMessage
from app.llm.router import get_llm_router
from app.config import get_settings
from app.services.cost_tracking import CostTrackingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_routing():
    router = get_llm_router()
    settings = get_settings()
    messages = [LLMMessage(role="user", content="Hello, tell me a short joke about AI.")]
    
    print("\n--- TEST 1: HIGH PRIORITY ROUTING ---")
    resp = await router.generate(messages, task_type="small_talk", priority="HIGH")
    print(f"Model Used: {resp.model_path}")
    print(f"Latency: {resp.latency_ms:.2f}ms")
    print(f"Cost: {resp.cost_cents:.4f}c")

    print("\n--- TEST 2: BUDGET ENFORCEMENT (HARD) ---")
    try:
        await router.generate(
            messages, 
            task_type="creative", 
            priority="MEDIUM", 
            current_budget_cents=100.0, 
            project_budget_limit=50.0
        )
    except Exception as e:
        print(f"Hard budget caught: {e}")

    print("\n--- TEST 3: SOFT BUDGET (DEGRADATION) ---")
    # 80% of 100 is 80. Let's set current to 85.
    # We'll use a task type that usually prefers "pro" models
    resp = await router.generate(
        messages,
        task_type="quality", 
        priority="MEDIUM",
        current_budget_cents=85.0,
        project_budget_limit=100.0
    )
    print(f"Soft budget reached. Model selected: {resp.model_path}")
    # Verify if it picked a routing/flash model instead of premium/pro

    print("\n--- TEST 4: OUTPUT CACHING ---")
    print("First call (possible miss)...")
    t1 = asyncio.get_event_loop().time()
    resp1 = await router.generate(messages, task_type="fast", priority="LOW")
    print(f"Call 1 latency: {(asyncio.get_event_loop().time() - t1)*1000:.2f}ms")

    print("Second call (should be hit)...")
    t2 = asyncio.get_event_loop().time()
    resp2 = await router.generate(messages, task_type="fast", priority="LOW")
    print(f"Call 2 latency: {(asyncio.get_event_loop().time() - t2)*1000:.2f}ms")
    if (asyncio.get_event_loop().time() - t2) < 0.1:
        print("SUCCESS: Cache hit confirmed (sub-100ms response)")

    print("\n--- TEST 5: COST PERSISTENCE (REDIS) ---")
    user_id = "test_user_123"
    job_id = "test_job_456"
    test_cost = 5.5
    await CostTrackingService.record_execution_cost(
        cost_cents=test_cost,
        user_id=user_id,
        project_id="test_project",
        job_id=job_id,
        model_id="gpt-4o"
    )
    
    # Check Redis directly
    r = await redis.from_url(settings.redis_url, decode_responses=True)
    val = await r.get(f"cost:job:{job_id}")
    print(f"Redis check for job {job_id}: {val} cents")
    if val and float(val) >= test_cost:
        print("SUCCESS: Cost persisted to Redis")

    print("\n--- TEST 6: FEATURE FLAGS (DYNAMIC DISABLE) ---")
    # Update flags to disable the current model
    flag_path = "config/feature_flags.json"
    with open(flag_path, "r") as f:
        flags = json.load(f)
    
    original_model = resp1.model_path
    print(f"Disabling model: {original_model}")
    flags[f"enable_model_{original_model}"] = False
    
    with open(flag_path, "w") as f:
        json.dump(flags, f)
    
    # Reload registry in router (or just re-init)
    router._load_registry()
    
    resp3 = await router.generate(messages, task_type="fast", priority="LOW", skip_cache=True)
    print(f"New model selected: {resp3.model_path}")
    if resp3.model_path != original_model:
        print("SUCCESS: Feature flag honored, model skipped")
    
    # Re-enable
    flags[f"enable_model_{original_model}"] = True
    with open(flag_path, "w") as f:
        json.dump(flags, f)

if __name__ == "__main__":
    asyncio.run(test_routing())

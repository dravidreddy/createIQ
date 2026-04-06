"""
DEVTOOLS - Verify Optimizations
DO NOT import in production code.
"""
import asyncio
import uuid
import time
from app.llm.router import get_llm_router
from app.llm.base import LLMMessage
from app.services.cache import get_cache

async def test_cache_scoping():
    print("\n--- Testing Cache Scoping ---")
    router = get_llm_router()
    messages = [LLMMessage(role="user", content="Tell me a joke about cache.")]
    
    # User A Request
    print("User A: First call...")
    resp_a1 = await router.generate(messages, user_id="user_A", project_id="proj_1")
    
    # User B Request (Same messages, different scoping)
    print("User B: Same call (should miss cache)...")
    resp_b = await router.generate(messages, user_id="user_B", project_id="proj_1")
    
    # User A Request (Should hit cache)
    print("User A: Second call (should hit cache)...")
    resp_a2 = await router.generate(messages, user_id="user_A", project_id="proj_1")
    
    if resp_a1.content == resp_a2.content:
        print("✅ Cache Scoping: SUCCESS (User A hit cache)")
    else:
        print("❌ Cache Scoping: FAILED (User A missed cache)")

async def test_idempotency():
    print("\n--- Testing Idempotency Safeguard ---")
    router = get_llm_router()
    messages = [LLMMessage(role="user", content="Ping")]
    idem_key = f"test-idem-{uuid.uuid4()}"
    
    print("Call 1 with idempotency key...")
    resp1 = await router.generate(messages, idempotency_key=idem_key)
    
    print("Call 2 with same idempotency key...")
    resp2 = await router.generate(messages, idempotency_key=idem_key)
    
    if resp1.content == resp2.content:
        print("✅ Idempotency: SUCCESS (Returned duplicate response)")
    else:
        print("❌ Idempotency: FAILED (Returned different response)")

async def test_circuit_breaker_persistence():
    print("\n--- Testing Circuit Breaker Persistence ---")
    router = get_llm_router()
    provider = "gpt-4o-mini"
    
    print(f"Tripping circuit for {provider}...")
    for _ in range(6): # Threshold is 5
        await router.record_failure(provider)
        
    is_open = await router.is_circuit_open(provider)
    print(f"Circuit state is open: {is_open}")
    
    if is_open:
        print("✅ Circuit Breaker: SUCCESS (Persistence worked in current instance)")
    else:
        print("❌ Circuit Breaker: FAILED (Circuit not open)")

async def main():
    try:
        await test_cache_scoping()
        await test_idempotency()
        await test_circuit_breaker_persistence()
    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    asyncio.run(main())

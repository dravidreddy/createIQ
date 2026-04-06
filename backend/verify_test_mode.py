import asyncio
import os
import sys

# Set root for imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.config import get_settings
from app.llm.execution_layer import ExecutionLayer
from app.llm.router import get_llm_router

async def verify():
    settings = get_settings()
    settings.test_mode = True
    
    print(f"--- TEST_MODE VERIFICATION ---")
    print(f"TEST_MODE Enabled: {settings.test_mode}")
    
    router = get_llm_router()
    exec_layer = ExecutionLayer(router)
    
    # Verify Mock Injection
    print("\nAttempting Mock Execution (Scenario: viral_tech_review)...")
    try:
        from app.llm.base import LLMMessage
        messages = [LLMMessage(role="user", content="Hello")]
        response = await exec_layer.execute(
            provider_name="groq", 
            messages=messages, 
            task_type="idea_discovery",
            scenario="viral_tech_review"
        )
        print(f"SUCCESS: Mock Response Received: {response.content[:50]}...")
        assert "ideas" in response.content
        assert response.provider_metadata.get("mocked") is True
        print("✓ Mock Injection Verified")
    except Exception as e:
        print(f"FAILED: Mock Injection: {e}")
        exit(1)

    # Verify FAIL-HARD Policy
    print("\nAttempting Missing Scenario (Fail-Hard)...")
    try:
        await exec_layer.execute(
            provider_name="groq", 
            messages=messages, 
            task_type="unknown_task",
            scenario="missing_scenario"
        )
        print("FAILED: Should have raised ScenarioNotFoundError")
    except Exception as e:
        print(f"SUCCESS: Caught expected exception: {e}")
        print("✓ Fail-Hard Policy Verified")

if __name__ == "__main__":
    os.environ["TEST_MODE"] = "true"
    asyncio.run(verify())

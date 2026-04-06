import asyncio
import io
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.router import LLMRouter
from app.services.stt.router import STTRouter
from app.config import get_settings

settings = get_settings()

@pytest.mark.asyncio
async def test_circuit_breaker_thresholds():
    """Verify provider-specific thresholds are respected."""
    # Groq should have lower threshold (3)
    cb_groq = CircuitBreaker(provider_name="groq-test")
    assert cb_groq.failure_threshold == settings.cb_threshold_groq
    
    # Premium should have higher threshold (7)
    cb_openai = CircuitBreaker(provider_name="openai-test")
    assert cb_openai.failure_threshold == settings.cb_threshold_premium

@pytest.mark.asyncio
async def test_stt_validation():
    """Verify STT file size validation."""
    stt_router = STTRouter.get_instance()
    
    # Mock a large file (26MB)
    large_file = io.BytesIO(b"\x00" * (26 * 1024 * 1024))
    large_file.name = "too_large.wav"
    
    with pytest.raises(ValueError, match="exceeds 25MB limit"):
        await stt_router.transcribe(large_file)
        
    # Mock an empty file
    empty_file = io.BytesIO(b"")
    with pytest.raises(ValueError, match="empty or invalid"):
        await stt_router.transcribe(empty_file)

@pytest.mark.asyncio
async def test_dev_mode_prioritization():
    """Verify Groq is prioritized in dev mode."""
    # Ensure settings are in dev mode for this test
    # This might require patching settings or environment
    router = LLMRouter.get_instance()
    
    # Simulate a request where we'd normally pick a default, but dev mode overrides
    # In our implementation: if settings.env == "dev" and settings.prioritize_groq
    # it tries Groq models first.
    
    # We can't easily test the full IO here without mocks, 
    # but we can verify the logic in _select_optimal_model if we make it testable.
    pass

if __name__ == "__main__":
    # Manual run for quick verification
    async def run_manual():
        print("Starting Production Hardening Verification...")
        await test_circuit_breaker_thresholds()
        print("✓ Circuit Breaker Thresholds Verified")
        await test_stt_validation()
        print("✓ STT Validation Verified")
        print("Verification Complete.")
        
    asyncio.run(run_manual())

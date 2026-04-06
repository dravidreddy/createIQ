import pytest
from app.llm.groq_provider import GroqProvider
from app.llm.base import LLMMessage

@pytest.mark.asyncio
async def test_groq_generate():
    """Basic test for Groq generation."""
    provider = GroqProvider(model="llama-3.3-70b-versatile")
    messages = [LLMMessage(role="user", content="Hello, respond with one word: 'Success'")]
    
    try:
        response = await provider.generate(messages, max_tokens=5)
        assert "success" in response.content.lower()
        assert response.model == "llama-3.3-70b-versatile"
    except Exception as e:
        pytest.fail(f"Groq generate failed: {e}")

@pytest.mark.asyncio
async def test_groq_stream():
    """Basic test for Groq streaming."""
    provider = GroqProvider(model="llama-3.1-8b-instant")
    messages = [LLMMessage(role="user", content="Count to 3")]
    
    chunks = []
    async for chunk in provider.stream(messages, max_tokens=10):
        if chunk.content:
            chunks.append(chunk.content)
    
    assert len(chunks) > 0

"""
Architectural Load Test Mocks

Provides high-performance mock implementations of LLM and Search providers
to enable stressing the internal LangGraph orchestration and MongoDB 
checkpointer without API costs or rate limiting.
"""

import asyncio
import random
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse, LLMStreamChunk
from app.tools.search import TavilySearchTool

logger = logging.getLogger(__name__)

class MockLLMProvider(BaseLLMProvider):
    """Simulates an LLM with configurable latency and static responses."""
    
    @property
    def model_name(self) -> str:
        return "mock-viral-model-v1"

    async def _simulate_latency(self):
        # Realistic TTFT (Time to First Token) of 0.5s - 1.5s
        await asyncio.sleep(random.uniform(0.5, 1.5))

    async def generate(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        await self._simulate_latency()
        # Simulate generation time
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        return LLMResponse(
            content="Mock viral content response. This is a high-energy, retention-focused simulation output.",
            input_tokens=100,
            output_tokens=200,
            model=self.model_name
        )

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        await self._simulate_latency()
        
        words = "This is a simulated high-energy streaming response for the CreatorIQ load test.".split()
        for i, word in enumerate(words):
            yield LLMStreamChunk(content=word + " ")
            await asyncio.sleep(0.05) # Fast streaming
            
        yield LLMStreamChunk(
            content="",
            is_complete=True,
            input_tokens=100,
            output_tokens=len(words)
        )

    async def generate_with_tools(
        self,
        messages: List[LLMMessage],
        tools: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        await self._simulate_latency()
        
        # Simulating tool call for search
        return {
            "content": "I will search for trending topics.",
            "tool_calls": [
                {
                    "name": "web_search",
                    "arguments": {"query": "trending creator topics 2026"}
                }
            ]
        }

class MockSearchTool:
    """Simulates Tavily search with static results and latency."""
    
    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        await asyncio.sleep(random.uniform(0.3, 1.0))
        return {
            "query": query,
            "results": [
                {
                    "title": "Mock Viral Trend 1",
                    "url": "https://example.com/trend1",
                    "content": "This is a mock research result about a viral trend.",
                    "score": 0.95
                },
                {
                    "title": "Mock Viral Trend 2",
                    "url": "https://example.com/trend2",
                    "content": "Another mock result for load testing.",
                    "score": 0.88
                }
            ]
        }

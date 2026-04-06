"""
Groq LLM Provider — High-speed inference for Llama 3 and OSS models.
"""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Dict, Any, List, Optional
from groq import AsyncGroq

from app.llm.base import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMError,
)
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class GroqProvider(BaseLLMProvider):
    """
    Groq LLM provider for ultra-fast Llama-3 inference.
    """

    def __init__(
        self, 
        api_key: str = None, 
        model: str = None
    ):
        self.api_key = api_key or settings.groq_api_key
        self._model_name = model or settings.groq_model or "llama-3.3-70b-versatile"
        self.provider_name = "groq"
        
        self.client = AsyncGroq(api_key=self.api_key)
        self._semaphore = asyncio.Semaphore(20) # Groq allows high concurrency

    @property
    def model_name(self) -> str:
        return self._model_name

    def supports_tools(self) -> bool:
        return True # Groq supports tool calling on Llama-3 models

    def supports_json(self) -> bool:
        return True # Groq supports JSON mode

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """Generate a response using Groq API."""
        start_time = time.perf_counter()
        
        # Convert to Groq format
        groq_messages = [{"role": m.role, "content": m.content} for m in messages]

        try:
            async with self._semaphore:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self._model_name,
                        messages=groq_messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format={"type": "json_object"} if kwargs.get("json_mode") else None,
                        **{k: v for k, v in kwargs.items() if k not in [
                            "json_mode", "tools", "execution_trace", "trace_id", 
                            "current_budget_cents", "project_budget_limit", 
                            "priority", "task_type", "project_id"
                        ]}
                    ),
                    timeout=30.0
                )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            return LLMResponse(
                content=response.choices[0].message.content or "",
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                latency_ms=latency_ms,
                model=self._model_name,
                model_path=f"groq/{self._model_name}",
                finish_reason=response.choices[0].finish_reason,
                provider_metadata={
                    "id": response.id,
                },
                tool_calls=[{
                    "id": tool.id,
                    "type": "function",
                    "function": {
                        "name": tool.function.name,
                        "arguments": tool.function.arguments
                    }
                } for tool in response.choices[0].message.tool_calls] if response.choices[0].message.tool_calls else None
            )

        except Exception as e:
            logger.error(f"Groq error: {e}")
            if "rate_limit" in str(e).lower():
                raise LLMRateLimitError(str(e), provider=self.provider_name)
            raise LLMError(f"Groq error: {str(e)}", provider=self.provider_name)

    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Generate a streaming response using Groq API."""
        groq_messages = [{"role": m.role, "content": m.content} for m in messages]

        try:
            async with self._semaphore:
                stream = await self.client.chat.completions.create(
                    model=self._model_name,
                    messages=groq_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    **{k: v for k, v in kwargs.items() if k not in ["json_mode", "tools"]}
                )
                
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield LLMStreamChunk(
                            content=chunk.choices[0].delta.content,
                            is_complete=False,
                            model=self._model_name
                        )
                
                yield LLMStreamChunk(content="", is_complete=True)

        except Exception as e:
            logger.error(f"Groq streaming error: {e}")
            raise LLMError(str(e), provider=self.provider_name)

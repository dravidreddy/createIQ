"""
OpenAI LLM Provider — Supports OpenAI, DeepSeek, and Together AI (OpenAI-compatible).
"""

import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, Any, List, Optional

import openai
from openai import AsyncOpenAI

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


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI-compatible LLM provider.
    
    Supports OpenAI, DeepSeek, Together AI, and any other provider 
    using the OpenAI v1 chat completion format.
    """

    def __init__(
        self, 
        api_key: str = None, 
        base_url: str = None, 
        model: str = None,
        provider_name: str = "openai"
    ):
        self.api_key = api_key or settings.openai_api_key
        self._model_name = model or settings.openai_model
        self.provider_name = provider_name
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url  # None uses default OpenAI URL
        )
        # Per-provider semaphore for rate limit protection
        self._semaphore = asyncio.Semaphore(10)

    @property
    def model_name(self) -> str:
        return self._model_name

    def supports_tools(self) -> bool:
        return True

    def supports_json(self) -> bool:
        return True

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """Generate a response using OpenAI-compatible API."""
        start_time = time.perf_counter()
        
        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in messages
        ]

        # Filter kwargs to only pass recognized parameters to the SDK
        allowed_kwargs = {k: v for k, v in kwargs.items() if k not in [
            "json_mode", "execution_trace", "trace_id", "current_budget_cents", 
            "project_budget_limit", "priority", "task_type", "project_id",
            "response_schema", "model_override"
        ]}

        try:
            async with self._semaphore:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self._model_name,
                        messages=openai_messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **allowed_kwargs,
                    ),
                    timeout=60.0
                )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Extract usage
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            choice = response.choices[0]
            
            return LLMResponse(
                content=choice.message.content or "",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                model=self._model_name,
                model_path=f"{self.provider_name}/{self._model_name}",
                finish_reason=choice.finish_reason,
                provider_metadata={
                    "id": response.id,
                    "system_fingerprint": getattr(response, "system_fingerprint", None)
                },
                tool_calls=[{
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in choice.message.tool_calls] if getattr(choice.message, "tool_calls", None) else None
            )

        except openai.RateLimitError as e:
            raise LLMRateLimitError(str(e), provider=self.provider_name)
        except asyncio.TimeoutError:
            raise LLMTimeoutError(f"OpenAI timeout for {self._model_name}", provider=self.provider_name)
        except Exception as e:
            raise LLMError(f"OpenAI error: {str(e)}", provider=self.provider_name)

    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Generate a streaming response using OpenAI-compatible API."""
        openai_messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in messages
        ]

        try:
            async with self._semaphore:
                stream = await self.client.chat.completions.create(
                    model=self._model_name,
                    messages=openai_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    **kwargs,
                )

                async for chunk in stream:
                    if not chunk.choices:
                        continue
                        
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield LLMStreamChunk(
                            content=delta.content,
                            is_complete=False,
                            model=self._model_name
                        )
                    
                    if getattr(delta, "tool_calls", None):
                        yield LLMStreamChunk(
                            content="",
                            is_complete=False,
                            model=self._model_name,
                            tool_call_chunks=[{
                                "index": tc.index,
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": getattr(tc.function, "name", None),
                                    "arguments": getattr(tc.function, "arguments", None)
                                }
                            } for tc in delta.tool_calls]
                        )
                
                yield LLMStreamChunk(content="", is_complete=True)

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise LLMError(str(e), provider=self.provider_name)

    async def generate_with_tools(
        self,
        messages: List[LLMMessage],
        tools: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """Generate a response with tool calling."""
        return await self.generate(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

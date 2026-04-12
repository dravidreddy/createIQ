"""
Anthropic LLM Provider — Supports Claude 3.5 Sonnet.
"""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Dict, Any, List, Optional

import anthropic
from anthropic import AsyncAnthropic

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


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic LLM provider for Claude models.
    """

    def __init__(
        self, 
        api_key: str = None, 
        model: str = None
    ):
        self.api_key = api_key or settings.anthropic_api_key
        self._model_name = model or settings.anthropic_model
        self.provider_name = "anthropic"
        
        self.client = AsyncAnthropic(api_key=self.api_key)
        # Per-provider semaphore for rate limit protection
        self._semaphore = asyncio.Semaphore(10)

    @property
    def model_name(self) -> str:
        return self._model_name

    def supports_tools(self) -> bool:
        return True

    def supports_json(self) -> bool:
        return True # Claude 3 supports tool-use as a proxy for JSON or pre-computation

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """Generate a response using Anthropic API."""
        start_time = time.perf_counter()
        
        # Extract system prompt if present
        system_prompt = None
        user_messages = []
        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                user_messages.append({"role": msg.role, "content": msg.content})

        # Tool conversion if present
        tools = kwargs.get("tools")
        if tools:
            # Simple conversion of OpenAI tools to Anthropic format
            anthropic_tools = []
            for t in tools:
                if t.get("type") == "function":
                    f = t["function"]
                    anthropic_tools.append({
                        "name": f["name"],
                        "description": f.get("description", ""),
                        "input_schema": f["parameters"]
                    })
            kwargs["tools"] = anthropic_tools

        # Filter kwargs to only pass recognized parameters to the SDK
        allowed_kwargs = {k: v for k, v in kwargs.items() if k not in [
            "json_mode", "execution_trace", "trace_id", "current_budget_cents", 
            "project_budget_limit", "priority", "task_type", "project_id"
        ]}

        try:
            async with self._semaphore:
                response = await asyncio.wait_for(
                    self.client.messages.create(
                        model=self._model_name,
                        system=system_prompt,
                        messages=user_messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **allowed_kwargs
                    ),
                    timeout=60.0
                )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Extract usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            
            # Extract content and tool calls
            content = ""
            tool_calls = []
            for part in response.content:
                if getattr(part, "type", None) == "text":
                    content += part.text
                elif getattr(part, "type", None) == "tool_use":
                    tool_calls.append({
                        "id": part.id,
                        "type": "function",
                        "function": {
                            "name": part.name,
                            "arguments": json.dumps(part.input)
                        }
                    })
            
            return LLMResponse(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                model=self._model_name,
                model_path=f"anthropic/{self._model_name}",
                finish_reason=response.stop_reason or "stop",
                provider_metadata={
                    "id": response.id,
                    "model_auth": response.model
                },
                tool_calls=tool_calls if tool_calls else None
            )

        except anthropic.RateLimitError as e:
            raise LLMRateLimitError(str(e), provider=self.provider_name)
        except asyncio.TimeoutError:
            raise LLMTimeoutError(f"Anthropic timeout for {self._model_name}", provider=self.provider_name)
        except Exception as e:
            raise LLMError(f"Anthropic error: {str(e)}", provider=self.provider_name)

    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Generate a streaming response using Anthropic API."""
        system_prompt = None
        user_messages = []
        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                user_messages.append({"role": msg.role, "content": msg.content})

        try:
            async with self._semaphore:
                async with self.client.messages.stream(
                    model=self._model_name,
                    system=system_prompt,
                    messages=user_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **{k: v for k, v in kwargs.items() if k not in ["json_mode", "tools"]}
                ) as stream:
                    async for event in stream:
                        if event.type == "content_block_delta" and event.delta.type == "text_delta":
                            yield LLMStreamChunk(
                                content=event.delta.text,
                                is_complete=False,
                                model=self._model_name
                            )
                        elif event.type == "content_block_delta" and event.delta.type == "input_json_delta":
                            yield LLMStreamChunk(
                                content=event.delta.partial_json,
                                is_complete=False,
                                model=self._model_name
                            )
                
                yield LLMStreamChunk(content="", is_complete=True)

        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
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

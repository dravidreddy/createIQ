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
    Shares API key rotation state across all instances so that when one model
    exhausts a key's rate limit, other models immediately skip to the next key.
    """

    # Class-level shared state for key rotation
    _shared_api_keys: list = []
    _shared_clients: list = []
    _shared_client_idx: int = 0
    _initialized: bool = False

    def __init__(
        self, 
        api_key: str = None, 
        model: str = None
    ):
        self._model_name = model or "llama-3.3-70b-versatile"
        
        # Initialize shared clients once (all instances share the same key pool)
        if not GroqProvider._initialized:
            GroqProvider._shared_api_keys = [k for k in [
                api_key or settings.groq_api_key,
                settings.groq_api_key_2,
                settings.groq_api_key_3
            ] if k]
            GroqProvider._shared_clients = [AsyncGroq(api_key=key) for key in GroqProvider._shared_api_keys]
            if not GroqProvider._shared_clients:
                logger.warning("No Groq API keys provided!")
            GroqProvider._initialized = True
            logger.info(f"GroqProvider: Initialized with {len(GroqProvider._shared_clients)} API keys")
            
        self._semaphore = asyncio.Semaphore(20)

    @property
    def clients(self):
        return GroqProvider._shared_clients

    @property
    def current_client_idx(self):
        return GroqProvider._shared_client_idx
    
    @current_client_idx.setter
    def current_client_idx(self, value):
        GroqProvider._shared_client_idx = value

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
            # Retry logic for api key rotation
            max_attempts = len(self.clients)
            
            for attempt in range(max_attempts):
                client = self.clients[self.current_client_idx]
                try:
                    async with self._semaphore:
                        response = await asyncio.wait_for(
                            client.chat.completions.create(
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
                    error_msg = str(e).lower()
                    if "rate limit" in error_msg or "429" in error_msg:
                        logger.warning(f"Groq rate limit hit on key index {self.current_client_idx}, rotating...")
                        self.current_client_idx = (self.current_client_idx + 1) % len(self.clients)
                        if attempt == max_attempts - 1:
                            raise LLMRateLimitError(str(e), provider=self.provider_name)
                        continue # Try next key
                    
                    logger.error(f"Groq error: {e}")
                    raise LLMError(f"Groq error: {str(e)}", provider=self.provider_name)
        except Exception as e:
            raise LLMError(f"Groq generate failed: {str(e)}", provider=self.provider_name)

    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Generate a streaming response using Groq API."""
        groq_messages = [{"role": m.role, "content": m.content} for m in messages]

        # Streaming API Key Rotation
        max_attempts = len(self.clients)
        for attempt in range(max_attempts):
            client = self.clients[self.current_client_idx]
            try:
                async with self._semaphore:
                    stream = await client.chat.completions.create(
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
                error_msg = str(e).lower()
                if "rate limit" in error_msg or "429" in error_msg:
                    logger.warning(f"Groq streaming rate limit hit on key index {self.current_client_idx}, rotating...")
                    self.current_client_idx = (self.current_client_idx + 1) % len(self.clients)
                    if attempt == max_attempts - 1:
                        raise LLMRateLimitError(str(e), provider=self.provider_name)
                    continue
                logger.error(f"Groq streaming error: {e}")
                raise LLMError(str(e), provider=self.provider_name)
            
            # If we succeed, exit the loop
            break

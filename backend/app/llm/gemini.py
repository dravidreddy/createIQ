"""
Gemini LLM Provider — Async-native implementation.

Uses the new `google-genai` SDK (not the legacy `google.generativeai`)
for fully async LLM calls without blocking the event loop.
"""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Dict, Any, List

from google import genai
from google.genai import types

from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse, LLMStreamChunk
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiProvider(BaseLLMProvider):
    """
    Gemini LLM provider using the async-native google-genai SDK.

    All calls are truly async — no run_in_executor needed.
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.gemini_api_key
        self._model_name = model or settings.gemini_model
        self.client = genai.Client(api_key=self.api_key)

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
        """Generate a response from Gemini (fully async)."""
        start_time = time.perf_counter()
        system_instruction, contents = self._convert_messages(messages)

        # Build generation config
        config_kwargs = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        # Handle JSON mode
        if kwargs.get("json_mode") or kwargs.get("response_format", {}).get("type") == "json_object":
            config_kwargs["response_mime_type"] = "application/json"

        # Handle Tools
        if kwargs.get("tools"):
            # Simple conversion of OpenAI tools to Gemini format
            gemini_tools = []
            for tool in kwargs["tools"]:
                if "function" in tool:
                    func = tool["function"]
                    gemini_tools.append(
                        types.Tool(
                            function_declarations=[
                                types.FunctionDeclaration(
                                    name=func["name"],
                                    description=func.get("description", ""),
                                    parameters=func.get("parameters", {}),
                                )
                            ]
                        )
                    )
            config_kwargs["tools"] = gemini_tools

        # Add system instruction if present
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        config = types.GenerateContentConfig(**config_kwargs)

        # Filter kwargs to only pass recognized parameters to the SDK
        sdk_kwargs = {
            "config": {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "candidate_count": 1,
            }
        }
        
        # Add response_mime_type if JSON mode was requested
        if config_kwargs.get("response_mime_type"):
            sdk_kwargs["config"]["response_mime_type"] = config_kwargs["response_mime_type"]
            
        # Add system instruction if present
        if system_instruction:
            sdk_kwargs["config"]["system_instruction"] = system_instruction

        # Add tools if present
        if config_kwargs.get("tools"):
             sdk_kwargs["config"]["tools"] = config_kwargs["tools"]

        try:
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=self._model_name,
                    contents=contents,
                    **sdk_kwargs
                ),
                timeout=60.0,
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Extract usage
            usage = response.usage_metadata
            input_tokens = usage.prompt_token_count if usage else 0
            output_tokens = usage.candidates_token_count if usage else 0

            # Extract content and tool calls
            content = response.text or ""
            tool_calls = []
            
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        tool_calls.append({
                            "id": f"call_{part.function_call.name}",
                            "type": "function",
                            "function": {
                                "name": part.function_call.name,
                                "arguments": json.dumps(part.function_call.args) if part.function_call.args else "{}"
                            }
                        })

            return LLMResponse(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                model=self._model_name,
                model_path=f"google/{self._model_name}",
                finish_reason="stop",
                provider_metadata={"usage": usage.to_dict() if usage else {}},
                tool_calls=tool_calls if tool_calls else None
            )

        except (asyncio.TimeoutError, EOFError) as e:
            # EOFError is common on some systems with the google-genai aio client
            raise LLMTimeoutError(f"Gemini connection error (Timeout/EOF): {str(e)}", provider="google")
        except Exception as e:
            raise LLMError(f"Gemini error: {str(e)}", provider="google")

    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Generate a streaming response from Gemini (fully async, token-by-token)."""
        system_instruction, contents = self._convert_messages(messages)

        config_kwargs = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        config = types.GenerateContentConfig(**config_kwargs)

        total_input_tokens = 0
        total_output_tokens = 0

        try:
            async for chunk in self.client.aio.models.generate_content_stream(
                model=self._model_name,
                contents=contents,
                config=config,
            ):
                text = chunk.text or ""
                if chunk.usage_metadata:
                    total_input_tokens = chunk.usage_metadata.prompt_token_count or 0
                    total_output_tokens = chunk.usage_metadata.candidates_token_count or 0

                if text:
                    yield LLMStreamChunk(
                        content=text,
                        is_complete=False,
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                        model=self._model_name
                    )

            # Final completion chunk
            yield LLMStreamChunk(
                content="",
                is_complete=True,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                model=self._model_name
            )
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            raise LLMError(str(e), provider="google")

    def _convert_messages(self, messages: List[LLMMessage]):
        """Convert LLMMessage list to Gemini format."""
        system_instruction = None
        contents = []

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            else:
                role = "user" if msg.role == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part(text=msg.content)]
                ))
        
        return system_instruction, contents


    async def generate_with_tools(
        self,
        messages: List[LLMMessage],
        tools: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """Generate a response with function calling."""
        return await self.generate(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

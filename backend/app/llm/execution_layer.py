"""
Execution Layer — Production-grade lifecycle management for LLM requests.

Handles fallbacks, retries, timeouts, and budget enforcement at the runtime level.
Sits between the LLMRouter and the individual BaseLLMProviders.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import AsyncGenerator, Dict, Any, List, Optional, Callable
import redis.asyncio as redis
import app.llm.base as base_mod
from app.llm.base import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    LLMError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMProviderDownError,
    LLMInvalidRequestError,
    LLMBudgetExceededError
)
# We will use base_mod.LLMNotExecutedError and base_mod.TokenUsageMissingError 
# to avoid potential NameErrors if the import was interrupted.

from app.llm.output_guard import OutputGuard
from app.llm.usage_tracker import usage_tracker
from app.config import get_settings
from app.utils.cost_tracker import CostCalculator
from app.services.cost_tracking import CostTrackingService
from app.services.cache import get_cached_llm_response, cache_llm_response
from app.utils.streaming import StreamValidator
from app.utils.determinism import get_time, get_uuid
from app.utils.resilience import retry_with_backoff, FailureSimulator

logger = logging.getLogger(__name__)
settings = get_settings()

class ExecutionLayer:
    """
    Centralized execution layer for LLM calls with advanced production guardrails.
    Includes JSON validation, repair, and standardized metrics.
    """

    def __init__(self, router: Any):
        self.router = router
        self.max_retries = 2
        self.max_fallback_depth = 3
        self.base_delay = 1.0
        self.per_call_timeout = 12.0
        self._redis: Optional[redis.Redis] = None
        self.output_guard = OutputGuard(router)

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def _get_mock_response(self, task_type: str, scenario: str = "generic_success") -> LLMResponse:
        """Fetch a mock response from the scenario manifest. FAIL-HARD if not found."""
        try:
            path = os.path.join(os.path.dirname(__file__), "mocks", "scenarios.json")
            with open(path, "r") as f:
                data = json.load(f)
            
            scenarios = data.get("scenarios", {})
            if scenario not in scenarios:
                raise LLMError(f"ScenarioNotFoundError: '{scenario}' not found in mock manifest.", provider="mock")
            
            mock_data = scenarios[scenario].get(task_type) or scenarios[scenario].get("default")
            if not mock_data:
                 raise LLMError(f"ScenarioNotFoundError: task '{task_type}' missing in scenario '{scenario}'.", provider="mock")
            
            return LLMResponse(
                content=mock_data["content"],
                input_tokens=mock_data["usage"]["input"],
                output_tokens=mock_data["usage"]["output"],
                model="mock-deterministic",
                finish_reason="stop",
                provider_metadata={"mocked": True, "scenario": scenario}
            )
        except Exception as e:
            logger.error(f"ExecutionLayer: Mock lookup failed: {e}")
            raise e

    async def _check_rate_limit(self, user_id: str) -> bool:
        """Token Bucket Rate Limiting with Fail-Open Redis Fallback."""
        try:
            r = await self._get_redis()
            rpm_key = f"rl:user:{user_id}:rpm:{time.strftime('%M')}"
            count = await r.incr(rpm_key)
            if count == 1:
                await r.expire(rpm_key, 60)
            return count <= settings.alpha_rate_limit_rpm
        except Exception as e:
            logger.warning(f"ExecutionLayer: Redis rate limit failed (Fail-Open): {e}")
            return True # Fail-open for rate limiting

    async def _check_budget(self, job_id: str, state_cost_cents: float = 0.0) -> bool:
        """
        Check if the current job has exceeded its budget.
        Now supports Fail-Safe state cost fallback if Redis is down.
        Returns True if under budget, False if over hard limit.
        """
        if not job_id or job_id == "unknown":
            return True
            
        current_cost = state_cost_cents
        try:
            r = await self._get_redis()
            redis_cost = await r.get(f"cost:job:{job_id}")
            if redis_cost is not None:
                current_cost = float(redis_cost)
        except Exception as e:
            logger.warning(f"ExecutionLayer: Redis budget check failed, using state fallback ({state_cost_cents}c): {e}")
            # current_cost remains state_cost_cents
        
        # 1. Hard Limit Check
        if current_cost >= settings.budget_default_per_job_cents:
            logger.error(f"ExecutionLayer: HARD BUDGET EXCEEDED for job {job_id} ({current_cost} >= {settings.budget_default_per_job_cents}c)")
            return False
            
        # 2. Soft Limit (Warning)
        if current_cost >= settings.budget_warning_threshold_cents:
            logger.warning(f"ExecutionLayer: SOFT BUDGET WARNING for job {job_id} ({current_cost}c)")
            
        return True

    async def _check_idempotency(self, key: str) -> Optional[LLMResponse]:
        if not key: return None
        try:
            r = await self._get_redis()
            data = await r.get(f"idempotency:{key}")
            if data:
                return LLMResponse(**json.loads(data))
        except Exception as e:
            logger.warning(f"ExecutionLayer: Idempotency check failed: {e}")
        return None

    async def _save_idempotency(self, key: str, response: LLMResponse):
        if not key: return
        try:
            r = await self._get_redis()
            await r.set(f"idempotency:{key}", json.dumps(response.model_dump()), ex=86400) # 24h
        except Exception as e:
            logger.warning(f"ExecutionLayer: Failed to save idempotency: {e}")

    def _get_timeout(self, provider_name: str) -> float:
        """Fetch model-specific timeout from settings."""
        name = provider_name.lower()
        if "groq" in name:
            return settings.timeout_groq
        if "together" in name:
            return settings.timeout_together
        if any(p in name for p in ["openai", "gpt"]):
            return settings.timeout_openai
        if any(p in name for p in ["claude", "anthropic"]):
            return settings.timeout_claude
        return settings.timeout_default

    async def execute(
        self,
        provider_name: str,
        messages: List[LLMMessage],
        task_type: str = "quality",
        priority: str = "MEDIUM",
        **kwargs
    ) -> LLMResponse:
        """Execute an LLM call with strict safety nets and output validation."""
        request_id = kwargs.get("request_id") or get_uuid()
        trace_id = kwargs.get("trace_id") or get_uuid()
        user_id = kwargs.get("user_id", "anonymous")
        project_id = kwargs.get("project_id", "default")
        idem_key = kwargs.get("idempotency_key")
        
        # 0. TEST_MODE Interception (Deterministic Mocks)
        if settings.test_mode:
            scenario = kwargs.get("scenario") or "generic_success"
            logger.info("ExecutionLayer: TEST_MODE active", extra={"scenario": scenario, "task": task_type})
            return await self._get_mock_response(task_type, scenario=scenario)

        # 0.1 Resilience Simulation (Phase 8.2)
        # Allows simulating failures via kwargs or headers if available in context
        sim_request = kwargs.get("request")
        if sim_request:
            await FailureSimulator.simulate_from_request(sim_request)

        # 1. Idempotency Check
        cached_resp = await self._check_idempotency(idem_key)
        if cached_resp: return cached_resp

        # 2. Budget and Rate Limit Checks
        job_id = kwargs.get("job_id", "unknown")
        state_cost = kwargs.get("current_state_cost", 0.0)
        if not await self._check_rate_limit(user_id):
            raise LLMRateLimitError(f"Rate limit exceeded for user {user_id}", provider="system")
            
        if not await self._check_budget(job_id, state_cost_cents=state_cost):
            # Graceful termination instead of exception
            return LLMResponse(
                content="",
                input_tokens=0,
                output_tokens=0,
                model="system",
                finish_reason="budget_exceeded",
                provider_metadata={"error": "budget_exceeded"}
            )

        # 3. Output Scoped Caching
        skip_cache = kwargs.get("skip_cache", False) or priority == "HIGH"
        if not skip_cache:
            cached = await get_cached_llm_response(
                messages, 
                task_type=task_type,
                user_id=user_id,
                project_id=project_id,
                params=kwargs.get("params")
            )
            if cached:
                return LLMResponse(**cached)

        # 4. Fallback Execution Loop
        fallback_chain = self.router.get_fallback_chain(provider_name)[:self.max_fallback_depth]
        providers_to_try = [provider_name] + fallback_chain
        
        last_error = None
        execution_trace = kwargs.get("execution_trace", [])
        execution_trace.append(f"plan_execution:providers={providers_to_try}")
        
        for name in providers_to_try:
            provider = self.router.get_provider(name)
            if not provider:
                execution_trace.append(f"skipped_provider_missing:{name}")
                continue
                
            if await self.router.is_circuit_open(name):
                execution_trace.append(f"skipped_provider_circuit_open:{name}")
                continue
            
            timeout = self.per_call_timeout
        
            @retry_with_backoff(max_attempts=self.max_retries, retry_on=(LLMTimeoutError, asyncio.TimeoutError, LLMRateLimitError))
            async def _attempt_provider_call():
                execution_trace.append(f"llm_call_started:{name}")
                logger.info(
                    "ExecutionLayer: Attempting provider call",
                    extra={"provider": name, "request_id": request_id, "trace_id": trace_id}
                )
                start_time = time.perf_counter()
                
                response = await asyncio.wait_for(
                    provider.generate(messages=messages, **kwargs),
                    timeout=timeout
                )
                
                latency_ms = (time.perf_counter() - start_time) * 1000
                response.latency_ms = latency_ms
                return response

            try:
                response = await _attempt_provider_call()

                # 4b. Strict Execution Validation
                if not response.content or len(response.content.strip()) == 0:
                    execution_trace.append(f"llm_call_failed:{name}:empty_response")
                    if hasattr(base_mod, "LLMNotExecutedError"):
                        raise base_mod.LLMNotExecutedError(f"LLM {name} returned empty content", provider=name)
                    else:
                        raise LLMError(f"LLM {name} returned empty content", provider=name)
                
                if response.input_tokens == 0 or response.output_tokens == 0:
                    execution_trace.append(f"llm_call_failed:{name}:zero_tokens")
                    if hasattr(base_mod, "TokenUsageMissingError"):
                        raise base_mod.TokenUsageMissingError(f"LLM {name} returned zero tokens", provider=name)
                    else:
                        raise LLMError(f"LLM {name} returned zero tokens", provider=name)

                execution_trace.append(f"llm_call_success:{name}")

                # 5. Output Validation & Repair (Tier-3)
                json_schema = kwargs.get("response_schema")
                if json_schema and kwargs.get("json_mode"):
                    response = await self.output_guard.validate_and_repair(
                        response=response,
                        schema=json_schema,
                        messages=messages,
                        trace_id=trace_id,
                        **kwargs
                    )

                # 6. Usage Tracking & Cost Recording
                await usage_tracker.track_request(response, user_id, project_id, trace_id=trace_id)
                await CostTrackingService.record_execution_cost(
                    cost_cents=response.cost_cents,
                    user_id=user_id,
                    project_id=project_id,
                    job_id=kwargs.get("job_id", "unknown"),
                    model_id=response.model
                )

                # 7. Store Cache & Idempotency
                if not skip_cache:
                    await cache_llm_response(messages, response.model_dump(), task_type=task_type, user_id=user_id, project_id=project_id)
                await self._save_idempotency(idem_key, response)

                await self.router.record_success(name, latency_ms)
                return response
                    
            except (LLMTimeoutError, asyncio.TimeoutError) as e:
                execution_trace.append(f"llm_call_failed:{name}:timeout")
                logger.warning("ExecutionLayer: Provider timed out", extra={"provider": name, "timeout": timeout})
                await self.router.record_failure(name)
                last_error = e
                continue # Try next provider in fallback chain

            except LLMRateLimitError as e:
                execution_trace.append(f"llm_call_failed:{name}:rate_limit")
                logger.warning("ExecutionLayer: Provider rate limited", extra={"provider": name})
                await self.router.record_failure(name)
                last_error = e
                continue

            except (LLMNotExecutedError, TokenUsageMissingError) as e:
                # These are critical execution failures for this specific provider/attempt
                execution_trace.append(f"llm_call_failed:{name}:logic_error:{type(e).__name__}")
                logger.error(f"[{request_id}] ExecutionLayer: {name} failed validation: {e}")
                await self.router.record_failure(name)
                last_error = e
                break # Failed validation => move to next provider

            except Exception as e:
                execution_trace.append(f"llm_call_failed:{name}:error:{type(e).__name__}")
                last_error = e
                logger.error(f"[{request_id}] ExecutionLayer: Error on {name}: {e}")
                await self.router.record_failure(name)
                break
            
            if name != providers_to_try[-1]:
                execution_trace.append(f"fallback_triggered:{name}->{providers_to_try[providers_to_try.index(name)+1]}")
            
        raise last_error or LLMError("All providers in execution chain failed.")

    async def execute_stream(
        self,
        provider_name: str,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute a streaming call with standardized SSE events and token batching.
        """
        request_id = kwargs.get("request_id") or str(uuid.uuid4())
        trace_id = kwargs.get("trace_id") or str(uuid.uuid4())
        
                # Optimized fallback depth for streaming to avoid long hangs
        fallback_chain = self.router.get_fallback_chain(provider_name)[:1]
        providers_to_try = [provider_name] + fallback_chain
        
        # ─── SSE Sequence Tracker ───
        current_seq_id = 0

        last_error = None
        for name in providers_to_try:
            # 0. TEST_MODE Interception (Streaming Mocks)
            if settings.test_mode:
                scenario_name = kwargs.get("scenario", "generic_success")
                mock_resp = await self._get_mock_response("default", scenario=scenario_name)
                
                yield {"type": "start", "model": "mock", "seq_id": current_seq_id}
                current_seq_id += 1
                
                # Split content into fake chunks for stream testing
                chunks = mock_resp.content.split(" ")
                for chunk in chunks:
                    yield {"type": "token", "content": chunk + " ", "seq_id": current_seq_id}
                    current_seq_id += 1
                    await asyncio.sleep(0.02) # Stable delay
                
                yield {"type": "end", "usage": {"input": 10, "output": 10}, "seq_id": current_seq_id}
                return

            provider = self.router.get_provider(name)
            if not provider or await self.router.is_circuit_open(name):
                continue
                
            # 0. Budget Check
            job_id = kwargs.get("job_id", "unknown")
            state_cost = kwargs.get("current_state_cost", 0.0)
            if not await self._check_budget(job_id, state_cost_cents=state_cost):
                yield {
                    "type": "error", 
                    "message": "Hard budget limit reached. Terminating gracefully.", 
                    "error_type": "BUDGET_EXCEEDED"
                }
                return

            try:
                yield {"type": "start", "model": name, "request_id": request_id, "trace_id": trace_id, "seq_id": current_seq_id}
                current_seq_id += 1
                
                # TokenBatcher stabilizes UI output
                batcher = TokenBatcher(batch_ms=80) 
                
                gen = provider.stream(messages=messages, **kwargs)
                async for chunk in gen:
                    if chunk.is_complete:
                        # Flush remaining tokens
                        if batcher.buffer:
                            yield {"type": "token", "content": batcher.flush(), "seq_id": current_seq_id}
                            current_seq_id += 1
                            
                        yield {
                            "type": "end", 
                            "usage": {"input": chunk.input_tokens, "output": chunk.output_tokens},
                            "provider": name,
                            "seq_id": current_seq_id
                        }
                        current_seq_id += 1
                        break
                    
                    if chunk.content:
                        batcher.add(chunk.content)
                        if batcher.should_emit():
                            yield {"type": "token", "content": batcher.flush(), "seq_id": current_seq_id}
                            current_seq_id += 1
                    
                    if chunk.tool_call_chunks:
                        # Direct emission of tool calls (don't batch)
                        yield {"type": "tool_call", "data": chunk.tool_call_chunks, "seq_id": current_seq_id}
                        current_seq_id += 1

                await self.router.record_success(name, 0.0)
                return # Success

            except Exception as e:
                logger.warning(f"[{request_id}] ExecutionLayer: Stream failed for {name}: {e}")
                await self.router.record_failure(name)
                last_error = e
                # Continues to next provider in fallback chain
                
        yield {"type": "error", "message": str(last_error or "Stream failed"), "request_id": request_id, "seq_id": current_seq_id}

class TokenBatcher:
    """Buffers tokens and emits them in batches to reduce SSE overhead/flicker."""
    def __init__(self, batch_ms: int = 50):
        self.buffer = []
        self.last_emit = time.perf_counter()
        self.batch_sec = batch_ms / 1000.0

    def add(self, token: str):
        self.buffer.append(token)

    def should_emit(self) -> bool:
        return (time.perf_counter() - self.last_emit) >= self.batch_sec and len(self.buffer) > 0

    def flush(self) -> str:
        content = "".join(self.buffer)
        self.buffer = []
        self.last_emit = time.perf_counter()
        return content

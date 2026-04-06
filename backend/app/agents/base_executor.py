"""
BaseAgentExecutor — Resilient wrapper for all pipeline sub-agents.

Provides:
  - Exponential back-off with jitter retries
  - Priority levels (CRITICAL, HIGH, NORMAL, LOW)
  - Degraded-mode fallback on exhausted retries
  - SSE event emission during execution
  - Token-by-token streaming support

All sub-agents inherit from this instead of the plain BaseAgent.
"""

import asyncio
import logging
import random
import time
from abc import abstractmethod
from enum import IntEnum
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.agents.base import BaseAgent
from app.llm.base import LLMMessage

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    CRITICAL = 1  # Must succeed — max retries
    HIGH = 2
    NORMAL = 3
    LOW = 4      # Best-effort — fewer retries


# Retry config per priority — hardened for rate-limited providers
_RETRY_CONFIG = {
    Priority.CRITICAL: {"max_retries": 5, "base_delay": 2.0},
    Priority.HIGH:     {"max_retries": 3, "base_delay": 2.0},
    Priority.NORMAL:   {"max_retries": 2, "base_delay": 1.0},
    Priority.LOW:      {"max_retries": 1, "base_delay": 0.5},
}


class BaseAgentExecutor(BaseAgent):
    """Resilient agent executor with retry, priority, streaming, and degradation.

    Subclasses MUST implement:
      - ``name`` property
      - ``description`` property
      - ``priority`` property
      - ``execute_core(input_data)`` — the actual agent logic
    """

    def __init__(
        self,
        user_context: Dict[str, Any] = None,
        job_id: Optional[str] = None,
    ):
        super().__init__(user_context=user_context)
        self.job_id = job_id
        self._cost_cents: float = 0.0
        self._latency_ms: int = 0

    # ── Abstract interface ──────────────────────────────────────

    @property
    @abstractmethod
    def priority(self) -> Priority:
        """Agent priority level."""
        ...

    @abstractmethod
    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Core agent logic — called inside the retry wrapper."""
        ...

    async def execute_degraded(
        self,
        input_data: Dict[str, Any],
        error: Exception,
    ) -> Dict[str, Any]:
        """Fallback when all retries are exhausted.

        Default implementation returns a stub so the pipeline can continue.
        Subclasses may override for smarter degradation.
        """
        return {
            "status": "degraded",
            "agent": self.name,
            "error": str(error),
            "output": None,
        }

    # ── Retry-wrapped execute ───────────────────────────────────

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent with exponential back-off retries."""
        cfg = _RETRY_CONFIG.get(self.priority, _RETRY_CONFIG[Priority.NORMAL])
        max_retries = cfg["max_retries"]
        base_delay = cfg["base_delay"]
        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                start = time.monotonic()
                result = await self.execute_core(input_data)
                elapsed_ms = int((time.monotonic() - start) * 1000)
                self._latency_ms += elapsed_ms

                self.log("info", f"Attempt {attempt} succeeded")
                result["_meta"] = {
                    "agent": self.name,
                    "attempt": attempt,
                    "latency_ms": self.last_latency_ms,
                    "model": self.last_model_used,
                    "degraded": False,
                    "token_usage": self.token_usage.copy(),
                    "cost_cents": self.get_cost_cents(),
                    "prompt_version": getattr(self, "current_prompt_version", "v1"),
                }
                return result

            except Exception as exc:
                last_error = exc
                err_str = str(exc).lower()

                # Non-retryable errors — break immediately, don't waste time retrying
                non_retryable_patterns = [
                    "invalid_api_key", "authentication", "unauthorized",
                    "billing", "quota_exceeded", "permission_denied",
                    "invalid api key", "api key not valid",
                ]
                if any(p in err_str for p in non_retryable_patterns):
                    self.log("error", f"Non-retryable error, skipping retries: {exc}")
                    break

                self.log(
                    "error",
                    f"Attempt {attempt}/{max_retries} failed: {exc}",
                )

                if attempt < max_retries:
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                    await asyncio.sleep(delay)

        # All retries exhausted — degrade
        self.log("error", f"All {max_retries} retries exhausted or non-retryable error encountered — entering degraded mode. Last error: {last_error}")
        result = await self.execute_degraded(input_data, last_error)
        result["_meta"] = {
            "agent": self.name,
            "attempt": max_retries,
            "latency_ms": self._latency_ms,
            "degraded": True,
            "token_usage": self.token_usage.copy(),
            "cost_cents": self.get_cost_cents(),
            "error_detail": str(last_error),
            "prompt_version": getattr(self, "current_prompt_version", "v1"),
        }
        return result

    # ── Streaming execute ───────────────────────────────────────

    async def execute_stream(
        self,
        input_data: Dict[str, Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream execution events including agent lifecycle and token chunks.

        Yields SSE-compatible event dicts:
          - agent_start
          - reasoning (step-by-step)
          - agent_complete or error
        """
        yield {
            "type": "agent_start",
            "agent": self.name,
            "data": {"message": f"Starting {self.name}..."},
        }

        try:
            result = await self.execute(input_data)
            is_degraded = result.get("_meta", {}).get("degraded", False)

            yield {
                "type": "agent_complete",
                "agent": self.name,
                "data": {
                    "message": f"Completed {self.name}",
                    "tokens": self.token_usage.copy(),
                    "cost_cents": self.get_cost_cents(),
                    "degraded": is_degraded,
                },
            }
            yield {
                "type": "agent_output",
                "agent": self.name,
                "data": result,
            }

        except Exception as exc:
            yield {
                "type": "error",
                "agent": self.name,
                "data": {
                    "message": str(exc),
                    "recoverable": self.priority != Priority.CRITICAL,
                },
            }

    # ── Helper: LLM call with automatic tracking ──────────────

    async def llm_generate(
        self,
        messages: List[LLMMessage],
        task_type: str = "quality",
        **kwargs,
    ):
        """Call LLM via router with automatic token, cost, and latency tracking."""
        # Inject priority and budget context into the call
        priority_map = {
            Priority.CRITICAL: "HIGH",
            Priority.HIGH: "HIGH",
            Priority.NORMAL: "MEDIUM",
            Priority.LOW: "LOW"
        }
        
        # Pass budget context from state (if available in user_context)
        kwargs.setdefault("current_budget_cents", self.user_context.get("total_cost_cents", 0.0))
        kwargs.setdefault("project_budget_limit", self.user_context.get("project_budget_limit", 50.0))
        
        response = await self.router.generate(
            messages=messages,
            task_type=task_type,
            priority=priority_map.get(self.priority, "MEDIUM"),
            **kwargs
        )
        
        # update_metrics is defined in BaseAgent
        self.update_metrics(response)
        return response

"""
BaseAgentExecutor — Resilient wrapper for all V3.3 agents.

Provides:
  - Exponential back-off with jitter retries
  - Priority levels (CRITICAL, HIGH, NORMAL, LOW)
  - Degraded-mode fallback on exhausted retries
  - Automatic cost/latency recording to JobMetrics

All agents inherit from this instead of the plain BaseAgent.
"""

import asyncio
import logging
import random
import time
from abc import abstractmethod
from enum import IntEnum
from typing import Any, Dict, Optional

from app.agents.base import BaseAgent
from app.llm.base import BaseLLMProvider
from app.schemas.profile import ProfileContext

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    CRITICAL = 1  # Must succeed — max retries
    HIGH = 2
    NORMAL = 3
    LOW = 4      # Best-effort — fewer retries


# Retry config per priority
_RETRY_CONFIG = {
    Priority.CRITICAL: {"max_retries": 5, "base_delay": 1.0},
    Priority.HIGH:     {"max_retries": 3, "base_delay": 1.0},
    Priority.NORMAL:   {"max_retries": 2, "base_delay": 0.5},
    Priority.LOW:      {"max_retries": 1, "base_delay": 0.3},
}


class BaseAgentExecutor(BaseAgent):
    """Resilient agent executor with retry, priority, and degradation support.

    Subclasses MUST implement:
      - ``priority`` property
      - ``execute_core(input_data)`` — the actual agent logic
      - ``execute_degraded(input_data, error)`` — fallback on total failure
    """

    def __init__(
        self,
        llm: BaseLLMProvider = None,
        user_context: ProfileContext = None,
        job_id: Optional[str] = None,
    ):
        super().__init__(llm=llm, user_context=user_context)
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

                self.log("info", f"Attempt {attempt} succeeded in {elapsed_ms}ms")
                result["_meta"] = {
                    "agent": self.name,
                    "attempt": attempt,
                    "latency_ms": elapsed_ms,
                    "degraded": False,
                }
                return result

            except Exception as exc:
                last_error = exc
                self.log(
                    "error",
                    f"Attempt {attempt}/{max_retries} failed: {exc}",
                )

                if attempt < max_retries:
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                    await asyncio.sleep(delay)

        # All retries exhausted — degrade
        self.log("error", f"All {max_retries} retries exhausted — entering degraded mode")
        result = await self.execute_degraded(input_data, last_error)
        result["_meta"] = {
            "agent": self.name,
            "attempt": max_retries,
            "latency_ms": self._latency_ms,
            "degraded": True,
        }
        return result

    # ── Streaming (delegates to non-stream for now) ─────────────

    async def execute_stream(self, input_data):
        """Default streaming — yield the full result as a single event."""
        result = await self.execute(input_data)
        yield result

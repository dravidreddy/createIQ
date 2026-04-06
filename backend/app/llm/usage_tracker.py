"""
Usage Tracker — Monitoring and logging LLM usage metrics.
"""

import logging
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.llm.base import LLMResponse
from app.utils.cost_tracker import CostCalculator

logger = logging.getLogger(__name__)

class UsageMetrics(BaseModel):
    """Schema for tracked usage metrics."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_cents: float
    latency_ms: float
    model: str
    provider: str
    timestamp: float
    trace_id: str
    request_id: Optional[str] = None

class UsageTracker:
    """
    Tracks and logs usage across all LLM providers.
    Supports detailed observability for dev-mode selection and fallbacks.
    """

    def __init__(self):
        self.calculator = CostCalculator()

    async def track_request(
        self,
        response: LLMResponse,
        user_id: str = "anonymous",
        project_id: Optional[str] = None,
        trace_id: str = "unknown",
        request_id: Optional[str] = None
    ) -> UsageMetrics:
        """
        Calculates cost and logs the request metrics with trace context.
        """
        cost = response.cost_cents
        if cost == 0.0:
            cost = self.calculator.calculate_cost_cents(
                model_id=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens
            )
            response.cost_cents = cost

        metrics = UsageMetrics(
            prompt_tokens=response.input_tokens,
            completion_tokens=response.output_tokens,
            total_tokens=response.input_tokens + response.output_tokens,
            cost_cents=cost,
            latency_ms=response.latency_ms,
            model=response.model,
            provider=response.model_path.split("/")[0] if "/" in response.model_path else "unknown",
            timestamp=time.time(),
            trace_id=trace_id,
            request_id=request_id
        )

        # Log for observability
        logger.info(
            f"[USAGE] [{trace_id}] {metrics.provider}/{metrics.model} | "
            f"Tokens: {metrics.total_tokens} ({metrics.prompt_tokens}i/{metrics.completion_tokens}o) | "
            f"Cost: ${metrics.cost_cents/100.0:.4f} | "
            f"Latency: {metrics.latency_ms:.0f}ms"
        )

        # TODO: Persist to database for billing/analytics
        
        return metrics

    def log_event(self, event_type: str, details: str, trace_id: str = "unknown"):
        """
        Logs selection, fallback, or circuit breaker events clearly.
        """
        marker = "==>" if "selection" in event_type.lower() else "!!!"
        logger.info(f"[EVENT] [{trace_id}] {marker} {event_type.upper()}: {details}")

usage_tracker = UsageTracker()

usage_tracker = UsageTracker()

def get_usage_tracker() -> UsageTracker:
    """Get usage tracker instance."""
    return usage_tracker

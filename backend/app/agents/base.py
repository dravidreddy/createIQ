"""
Base Agent

Abstract base class for all AI agents in the pipeline.
Uses LLMRouter for provider selection instead of the legacy factory.
"""

from app.utils.datetime_utils import utc_now
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator, Optional, List
from datetime import datetime
from app.llm.base import BaseLLMProvider, LLMMessage
from app.llm.router import get_llm_router
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for AI agents.

    All agents (sub-agents, group supervisors) inherit from this class
    and implement their specific logic.
    """

    def __init__(
        self,
        user_context: Dict[str, Any] = None,
    ):
        """
        Initialize base agent.

        Args:
            user_context: User/project context dict for personalization
        """
        self._router = get_llm_router()
        self.user_context = user_context or {}
        self.execution_logs: List[Dict[str, Any]] = []
        self.token_usage = {"input": 0, "output": 0}
        self.total_cost_cents = 0.0
        self.last_latency_ms = 0.0
        self.last_model_path = ""
        self.last_model_used = "unknown"

    @property
    def router(self):
        """Access the LLM router."""
        return self._router

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent description."""
        pass

    def log(self, log_type: str, message: str, data: Dict = None):
        """
        Add a log entry.

        Args:
            log_type: Type of log (tool_call, reasoning, info, error)
            message: Log message
            data: Additional data
        """
        entry = {
            "timestamp": utc_now().isoformat(),
            "agent": self.name,
            "type": log_type,
            "message": message,
            "data": data or {}
        }
        self.execution_logs.append(entry)
        logger.info(f"[{self.name}] {log_type}: {message}")

    def update_metrics(self, response: Any):
        """Update token usage, cost, and latency from an LLMResponse."""
        self.token_usage["input"] += response.input_tokens
        self.token_usage["output"] += response.output_tokens
        self.total_cost_cents += getattr(response, "cost_cents", 0.0)
        self.last_latency_ms = getattr(response, "latency_ms", 0.0)
        self.last_model_path = getattr(response, "model_path", "")
        self.last_model_used = getattr(response, "model", "unknown")

    def get_cost_cents(self) -> float:
        """Return the accumulated cost in cents."""
        return self.total_cost_cents

    @abstractmethod
    async def execute(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the agent's task.

        Args:
            input_data: Input data for the agent

        Returns:
            Agent output
        """
        pass

    @abstractmethod
    async def execute_stream(
        self,
        input_data: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute the agent's task with streaming.

        Args:
            input_data: Input data for the agent

        Yields:
            Stream events (tool calls, reasoning, output chunks)
        """
        pass

    async def run(
        self,
        input_data: Dict[str, Any],
        stream: bool = False
    ):
        """
        Run the agent.

        Args:
            input_data: Input data
            stream: Whether to stream output

        Returns:
            Output or async generator
        """
        self.log("info", f"Starting execution", {"input_keys": list(input_data.keys())})

        if stream:
            return self.execute_stream(input_data)
        else:
            result = await self.execute(input_data)
            self.log("info", f"Execution complete", {"token_usage": self.token_usage})
            return result

"""
PacingOptimizerAgent — Stage 4 sub-agent.

Suggests pacing adjustments, retention hooks, and beat timing
to optimize audience retention throughout the script.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt

logger = logging.getLogger(__name__)


class PacingOptimizerAgent(BaseAgentExecutor):
    """Optimizes script pacing for audience retention."""

    @property
    def name(self) -> str:
        return "PacingOptimizerAgent"

    @property
    def description(self) -> str:
        return "Optimizes pacing for audience retention"

    @property
    def priority(self) -> Priority:
        return Priority.NORMAL

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        script = input_data.get("script", "")
        if isinstance(script, dict):
            script = script.get("full_script", str(script))
        structure_analysis = input_data.get("structure_analysis", {})
        user_preferences = input_data.get("user_preferences", {})

        self.log("info", "Optimizing pacing")

        system_prompt = await self.get_orchestrated_prompt(
            "pacing_optimizer", self.user_context, user_preferences
        )
        user_prompt = load_user_prompt(
            "pacing_optimizer",
            script=script[:5000],
            structure_analysis=structure_analysis,
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_generate(messages, task_type="quality")
        result = parse_llm_json(response.content, fallback={
            "pacing_adjustments": [],
            "retention_hooks_to_add": [],
            "restructured_script": script,
        })

        self.log("info", f"Pacing optimized: {len(result.get('pacing_adjustments', []))} adjustments")
        return result

"""
EngagementBoosterAgent — Stage 5 sub-agent.

Adds retention hooks, questions, pattern interrupts, and engagement triggers
to maximize audience interaction and watch time.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt

logger = logging.getLogger(__name__)


class EngagementBoosterAgent(BaseAgentExecutor):
    """Adds engagement triggers and retention hooks to scripts."""

    @property
    def name(self) -> str:
        return "EngagementBoosterAgent"

    @property
    def description(self) -> str:
        return "Adds retention hooks and engagement triggers"

    @property
    def priority(self) -> Priority:
        return Priority.NORMAL

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        edited_script = input_data.get("edited_script", "")
        if isinstance(edited_script, dict):
            edited_script = edited_script.get("full_script", str(edited_script))

        self.log("info", "Boosting engagement elements")

        system_prompt = await self.get_orchestrated_prompt(
            "engagement_booster", self.user_context, {}
        )
        user_prompt = load_user_prompt(
            "engagement_booster",
            script=edited_script[:6000],
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_generate(messages, task_type="quality")
        result = parse_llm_json(response.content, fallback={
            "boosters_added": [],
            "enhanced_script": edited_script,
        })

        boosters = result.get("boosters_added", [])
        self.log("info", f"Added {len(boosters)} engagement boosters")
        return result

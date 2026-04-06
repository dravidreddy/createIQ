"""
SeriesPlannerAgent — Stage 6 sub-agent.

Plans a 5-part content series based on the completed content.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt

logger = logging.getLogger(__name__)


class SeriesPlannerAgent(BaseAgentExecutor):
    """Plans multi-part content series from completed scripts."""

    @property
    def name(self) -> str:
        return "SeriesPlannerAgent"

    @property
    def description(self) -> str:
        return "Plans a 5-part content series"

    @property
    def priority(self) -> Priority:
        return Priority.NORMAL

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        final_script = input_data.get("final_script", "")
        if isinstance(final_script, dict):
            final_script = final_script.get("full_script", str(final_script))
        selected_idea = input_data.get("selected_idea", {})
        project_context = input_data.get("project_context", {})

        self.log("info", "Planning content series")

        system_prompt = load_system_prompt("series_planner")
        user_prompt = load_user_prompt(
            "series_planner",
            final_script=final_script[:3000],
            selected_idea=selected_idea,
            niche=project_context.get("niche", "general"),
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_generate(messages, task_type="quality")
        result = parse_llm_json(response.content, fallback={"series_plan": []})

        plan = result.get("series_plan", [])
        self.log("info", f"Series plan: {len(plan)} episodes planned")
        return result

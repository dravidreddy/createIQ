"""
GrowthAdvisorAgent — Stage 6 sub-agent.

Provides growth strategy, posting schedule, cross-promotion tips,
and audience growth projections.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt

logger = logging.getLogger(__name__)


class GrowthAdvisorAgent(BaseAgentExecutor):
    """Provides growth strategy and posting schedule recommendations."""

    @property
    def name(self) -> str:
        return "GrowthAdvisorAgent"

    @property
    def description(self) -> str:
        return "Growth strategy and posting schedule advisor"

    @property
    def priority(self) -> Priority:
        return Priority.LOW

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        series_plan = input_data.get("series_plan", [])
        user_preferences = input_data.get("user_preferences", {})

        self.log("info", "Generating growth strategy")

        system_prompt = await self.get_orchestrated_prompt(
            "growth_advisor", self.user_context, {}
        )
        user_prompt = load_user_prompt(
            "growth_advisor",
            series_plan=series_plan,
            user_preferences=user_preferences,
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_generate(
            messages, task_type="quality", temperature=0.6
        )
        result = parse_llm_json(response.content, fallback={
            "posting_schedule": {},
            "growth_tips": [],
            "cross_promotion_ideas": [],
            "audience_growth_projections": {},
        })

        self.log("info", f"Growth strategy complete: {len(result.get('growth_tips', []))} tips")
        return result

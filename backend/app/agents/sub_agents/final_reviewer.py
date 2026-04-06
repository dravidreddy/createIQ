"""
FinalReviewerAgent — Stage 5 sub-agent.

Holistic quality review, final scoring, and production of the definitive script.
Uses evaluation engine for final quality gate.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt

logger = logging.getLogger(__name__)


class FinalReviewerAgent(BaseAgentExecutor):
    """Final holistic quality review and definitive script production."""

    @property
    def name(self) -> str:
        return "FinalReviewerAgent"

    @property
    def description(self) -> str:
        return "Final quality review and definitive script production"

    @property
    def priority(self) -> Priority:
        return Priority.HIGH

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        enhanced_script = input_data.get("enhanced_script", "")
        if isinstance(enhanced_script, dict):
            enhanced_script = enhanced_script.get("full_script", str(enhanced_script))
        user_preferences = input_data.get("user_preferences", {})

        self.log("info", "Performing final review")

        system_prompt = load_system_prompt(
            "final_reviewer",
            user_preferences=user_preferences,
        )
        user_prompt = load_user_prompt(
            "final_reviewer",
            script=enhanced_script[:6000],
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_generate(messages, task_type="quality", max_tokens=6144)
        result = parse_llm_json(response.content, fallback={
            "quality_score": 0.7,
            "improvement_summary": "",
            "final_script": enhanced_script,
        })

        quality = result.get("quality_score", 0.7)
        self.log("info", f"Final review complete — quality score: {quality}")

        return result

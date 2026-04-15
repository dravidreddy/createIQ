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
from app.schemas.llm_outputs import FinalReviewOutput

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
        selected_idea = input_data.get("selected_idea", {})
        project_context = {**self.user_context, **(input_data.get("project_context", {}) or {})}
        style_overrides = project_context.get("style_overrides") or {}

        self.log("info", "Performing final review")

        system_prompt = await self.get_orchestrated_prompt(
            "final_reviewer", self.user_context, user_preferences
        )
        user_prompt = load_user_prompt(
            "final_reviewer",
            script=enhanced_script[:6000],
            idea_title=selected_idea.get("title", project_context.get("topic", "")),
            vocabulary=project_context.get("vocabulary") or style_overrides.get("vocabulary"),
            avoid_words=project_context.get("avoid_words") or style_overrides.get("avoid_words"),
            pacing_style=project_context.get("pacing_style") or style_overrides.get("pacing_style"),
            user_preferences=user_preferences,
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_generate(
            messages,
            task_type="quality",
            max_tokens=4096,
            json_mode=True,
            response_schema=FinalReviewOutput,
        )
        result = parse_llm_json(response.content, fallback={
            "quality_score": 0.7,
            "improvement_summary": "",
            "final_script": enhanced_script,
        })

        quality = result.get("quality_score", 0.7)
        self.log("info", f"Final review complete — quality score: {quality}")

        return result

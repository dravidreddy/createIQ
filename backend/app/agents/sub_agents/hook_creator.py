"""
HookCreatorAgent — Stage 2 sub-agent.

Generates 3-5 hooks using different psychological frameworks:
Curiosity Gap, FOMO, Contrarian, Story Loop, Data Shock.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt

logger = logging.getLogger(__name__)


class HookCreatorAgent(BaseAgentExecutor):
    """Creates hooks using psychological frameworks."""

    @property
    def name(self) -> str:
        return "HookCreatorAgent"

    @property
    def description(self) -> str:
        return "Generates compelling hooks using psychological frameworks"

    @property
    def priority(self) -> Priority:
        return Priority.HIGH

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        selected_idea = input_data.get("selected_idea", {})
        user_preferences = input_data.get("user_preferences", {})
        framework = input_data.get("framework", "")

        self.log("info", f"Creating hooks for: {selected_idea.get('title', 'unknown')} (framework: {framework or 'all'})")

        system_prompt = await self.get_orchestrated_prompt(
            "hook_creator", self.user_context, user_preferences
        )
        user_prompt = load_user_prompt(
            "hook_creator",
            idea_title=selected_idea.get("title", ""),
            idea_description=selected_idea.get("description", ""),
            unique_angle=selected_idea.get("unique_angle", ""),
            target_emotion=selected_idea.get("target_emotion", "curiosity"),
            framework=framework,
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_generate(messages, task_type="quality")
        result = parse_llm_json(response.content, fallback={"hooks": []})

        hooks = result.get("hooks", [])
        self.log("info", f"Generated {len(hooks)} hooks")
        return {"hooks": hooks}

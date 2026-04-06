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

        self.log("info", f"Creating hooks for: {selected_idea.get('title', 'unknown')}")

        system_prompt = load_system_prompt(
            "hook_creator",
            user_preferences=user_preferences,
        )
        user_prompt = load_user_prompt(
            "hook_creator",
            selected_idea=selected_idea,
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

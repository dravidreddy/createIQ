"""
LineEditorAgent — Stage 5 sub-agent.

Performs line-by-line edit suggestions for clarity, engagement, and flow.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt

logger = logging.getLogger(__name__)


class LineEditorAgent(BaseAgentExecutor):
    """Line-by-line editor for clarity, engagement, and flow."""

    @property
    def name(self) -> str:
        return "LineEditorAgent"

    @property
    def description(self) -> str:
        return "Line-by-line editing for clarity and engagement"

    @property
    def priority(self) -> Priority:
        return Priority.HIGH

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        script = input_data.get("script", "")
        if isinstance(script, dict):
            script = script.get("full_script", script.get("restructured_script", str(script)))
        structure_guidance = input_data.get("structure_guidance", {})
        user_preferences = input_data.get("user_preferences", {})

        self.log("info", "Performing line-by-line editing")

        system_prompt = await self.get_orchestrated_prompt(
            "line_editor", self.user_context, user_preferences
        )
        user_prompt = load_user_prompt(
            "line_editor",
            script=script[:6000],
            structure_guidance=structure_guidance,
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_generate(messages, task_type="quality", max_tokens=6144)
        result = parse_llm_json(response.content, fallback={
            "edits": [],
            "edited_script": script,
        })

        edits = result.get("edits", [])
        self.log("info", f"Line editing complete: {len(edits)} edits suggested")
        return result

"""
IdeaGeneratorAgent — Stage 1 sub-agent.

Synthesizes trend research into 5 structured content ideas,
incorporating user preferences and past memory.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt
from app.schemas.llm_outputs import IdeaGenerationOutput

logger = logging.getLogger(__name__)


class IdeaGeneratorAgent(BaseAgentExecutor):
    """Generates structured content ideas from research results."""

    @property
    def name(self) -> str:
        return "IdeaGeneratorAgent"

    @property
    def description(self) -> str:
        return "Synthesizes research into structured content ideas"

    @property
    def priority(self) -> Priority:
        return Priority.HIGH

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        research_results = input_data.get("research_results", [])
        user_preferences = input_data.get("user_preferences", {})
        project_context = input_data.get("project_context", {})

        self.log("info", f"Generating ideas from {len(research_results)} research results")

        system_prompt = await self.get_orchestrated_prompt(
            "idea_generator", self.user_context, user_preferences
        )
        user_prompt = load_user_prompt(
            "idea_generator",
            research_results=research_results,
            topic=project_context.get("topic", ""),
            platforms=project_context.get("platforms", ["YouTube"]),
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
            response_schema=IdeaGenerationOutput,
        )
        
        logger.debug("IdeaGenerator raw response from %s (%d chars)", response.model, len(response.content))
        
        result = parse_llm_json(response.content, fallback={"ideas": []})

        ideas = result.get("ideas", [])
        self.log("info", f"Generated {len(ideas)} content ideas")

        return {"ideas": ideas}

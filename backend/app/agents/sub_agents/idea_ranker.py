"""
IdeaRankerAgent — Stage 1 sub-agent.

Scores and ranks generated ideas on engagement, uniqueness, and audience fit.
Uses the fast scoring model (Groq) for efficiency.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt

logger = logging.getLogger(__name__)


class IdeaRankerAgent(BaseAgentExecutor):
    """Ranks ideas by engagement potential, uniqueness, and audience fit."""

    @property
    def name(self) -> str:
        return "IdeaRankerAgent"

    @property
    def description(self) -> str:
        return "Scores and ranks content ideas"

    @property
    def priority(self) -> Priority:
        return Priority.NORMAL

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        ideas = input_data.get("ideas", [])
        user_preferences = input_data.get("user_preferences", {})

        if not ideas:
            return {"ranked_ideas": []}

        self.log("info", f"Ranking {len(ideas)} ideas")

        system_prompt = load_system_prompt(
            "idea_ranker",
            user_preferences=user_preferences,
        )
        user_prompt = load_user_prompt(
            "idea_ranker",
            ideas=ideas,
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        # Use fast scoring model for efficiency
        response = await self.llm_generate(
            messages, task_type="scoring", temperature=0.2, max_tokens=2048
        )
        result = parse_llm_json(response.content, fallback={"ranked_ideas": ideas})

        ranked = result.get("ranked_ideas", ideas)
        # Sort by total_score if present
        ranked.sort(key=lambda x: x.get("total_score", 0), reverse=True)

        self.log("info", f"Ranked {len(ranked)} ideas")
        return {"ranked_ideas": ranked}

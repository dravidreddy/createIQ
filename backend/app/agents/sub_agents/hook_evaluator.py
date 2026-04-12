"""
HookEvaluatorAgent — Stage 2 sub-agent.

Quality-scores each hook and refines weak ones (score < 0.7).
Uses the fast scoring model for evaluation.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt

logger = logging.getLogger(__name__)


class HookEvaluatorAgent(BaseAgentExecutor):
    """Evaluates and refines hooks based on quality scoring."""

    @property
    def name(self) -> str:
        return "HookEvaluatorAgent"

    @property
    def description(self) -> str:
        return "Quality-scores hooks and refines weak ones"

    @property
    def priority(self) -> Priority:
        return Priority.NORMAL

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        hooks = input_data.get("hooks", [])

        if not hooks:
            return {"evaluated_hooks": []}

        self.log("info", f"Evaluating {len(hooks)} hooks")

        system_prompt = await self.get_orchestrated_prompt(
            "hook_evaluator", {}, {}
        )
        user_prompt = load_user_prompt("hook_evaluator", hooks=hooks)

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_generate(
            messages, task_type="scoring", temperature=0.2, max_tokens=2048
        )
        result = parse_llm_json(response.content, fallback={"evaluated_hooks": hooks})

        evaluated = result.get("evaluated_hooks", hooks)
        # Sort by quality_score
        evaluated.sort(key=lambda x: x.get("quality_score", 0), reverse=True)

        self.log("info", f"Evaluated {len(evaluated)} hooks, best score: {evaluated[0].get('quality_score', 'N/A') if evaluated else 'N/A'}")
        return {"evaluated_hooks": evaluated}

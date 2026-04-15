"""
FactCheckerAgent — Stage 3 sub-agent.

Verifies factual claims in the script using web search and Q&A tools.
Marks unverified claims with [UNVERIFIED] tags.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.tools.search import get_tavily_tool
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt
from app.schemas.llm_outputs import FactCheckOutput

logger = logging.getLogger(__name__)


class FactCheckerAgent(BaseAgentExecutor):
    """Verifies factual claims in scripts."""

    @property
    def name(self) -> str:
        return "FactCheckerAgent"

    @property
    def description(self) -> str:
        return "Verifies factual claims and marks unverified ones"

    @property
    def priority(self) -> Priority:
        return Priority.HIGH

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        script = input_data.get("script", input_data.get("full_script", ""))
        if isinstance(script, dict):
            script = script.get("full_script", str(script))
        project_context = {**self.user_context, **(input_data.get("project_context", {}) or {})}
        user_preferences = input_data.get("user_preferences", self.user_context.get("user_preferences", {}))

        self.log("info", "Fact-checking script")

        search_tool = get_tavily_tool()

        system_prompt = await self.get_orchestrated_prompt(
            "fact_checker", project_context, user_preferences
        )
        user_prompt = load_user_prompt("fact_checker", script=script[:12000])

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_generate(
            messages,
            task_type="quality",
            max_tokens=4096,
            json_mode=True,
            response_schema=FactCheckOutput,
        )
        result = parse_llm_json(response.content, fallback={
            "verified_claims": [],
            "unverified_claims": [],
            "corrected_script": script,
        })

        # Verify top unverified claims via search
        unverified = result.get("unverified_claims", [])
        for claim in unverified[:3]:
            claim_text = claim if isinstance(claim, str) else claim.get("claim", "")
            if claim_text:
                self.log("tool_call", f"search_qna: {claim_text[:80]}")
                answer = await search_tool.search_qna(claim_text)
                if isinstance(claim, dict):
                    claim["verification_result"] = answer[:500]

        self.log("info", f"Fact-check complete: {len(result.get('verified_claims', []))} verified, {len(unverified)} unverified")
        return result

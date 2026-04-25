"""
Competitor Analyzer Agent — Extracts insights from a competitor's YouTube transcript.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt

logger = logging.getLogger(__name__)


class CompetitorAnalyzerAgent(BaseAgentExecutor):
    """Analyzes a YouTube transcript and breaks down its structure/hooks."""

    @property
    def name(self) -> str:
        return "CompetitorAnalyzerAgent"

    @property
    def description(self) -> str:
        return "Reverse-engineers a competitor's YouTube transcript."

    @property
    def priority(self) -> Priority:
        return Priority.HIGH

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        transcript = input_data.get("transcript", "")
        if not transcript:
            raise ValueError("Transcript is required for competitor analysis.")

        # Truncate if insanely long (keep ~5000 words max to fit in context)
        words = transcript.split()
        if len(words) > 5000:
            transcript = " ".join(words[:5000]) + "... [TRUNCATED]"

        # For this standalone tool, we bypass NAPOS orchestration and use raw loader
        system_prompt = load_system_prompt(
            "competitor_analyzer",
            user_preferences={},
        )
        user_prompt = load_user_prompt(
            "competitor_analyzer",
            transcript=transcript,
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_generate(
            messages,
            task_type="analysis",
            max_tokens=2048,
            temperature=0.3,
            json_mode=True,
        )

        fallback = {
            "hook_breakdown": {"text": "Could not extract", "strategy": ""},
            "core_message": "Could not extract",
            "structure": [],
            "pattern_interrupts": [],
            "pacing_and_tone": "Unknown",
            "call_to_action": {"text": "", "placement": ""}
        }

        result = parse_llm_json(response.content, fallback=fallback)
        return result

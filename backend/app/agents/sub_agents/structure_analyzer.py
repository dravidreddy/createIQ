"""
StructureAnalyzerAgent — Stage 4 sub-agent.

Analyzes script against platform-specific structure rules,
providing retention checkpoints, visual/audio cues, and CTA placement.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt

logger = logging.getLogger(__name__)


class StructureAnalyzerAgent(BaseAgentExecutor):
    """Analyzes script structure for platform optimization."""

    @property
    def name(self) -> str:
        return "StructureAnalyzerAgent"

    @property
    def description(self) -> str:
        return "Analyzes script structure for platform-specific optimization"

    @property
    def priority(self) -> Priority:
        return Priority.NORMAL

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        script = input_data.get("script", "")
        if isinstance(script, dict):
            script = script.get("full_script", str(script))
        platforms = input_data.get("platforms", ["YouTube"])
        video_length = input_data.get("video_length", "Medium (1-10 min)")

        self.log("info", f"Analyzing structure for {', '.join(platforms)}")

        system_prompt = load_system_prompt(
            "structure_analyzer",
            platforms=platforms,
            video_length=video_length,
        )
        user_prompt = load_user_prompt(
            "structure_analyzer",
            script=script[:5000],
            platforms=platforms,
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_generate(messages, task_type="quality")
        result = parse_llm_json(response.content, fallback={
            "hook_analysis": {},
            "structure_breakdown": [],
            "retention_checkpoints": [],
            "visual_audio_cues": [],
            "cta_placement": {},
        })

        self.log("info", f"Structure analysis complete: {len(result.get('structure_breakdown', []))} sections analyzed")
        return result

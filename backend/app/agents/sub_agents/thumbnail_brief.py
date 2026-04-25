"""
Thumbnail Brief Agent — Auto-generates a thumbnail concept brief from a finished script.

Takes script + hook + topic and produces a structured thumbnail concept:
  - Primary overlay text
  - Expression/mood
  - Color scheme
  - Layout guidance
  - Visual elements
  - Style reference
"""

import json
import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage

logger = logging.getLogger(__name__)

THUMBNAIL_PROMPT = """You are a YouTube thumbnail design strategist. Given a script and its hook, generate a detailed thumbnail concept brief that would maximize click-through rate.

Return a JSON object with EXACTLY this structure:
{
  "primary_text": "<2-5 word overlay text for the thumbnail — short, punchy, creates curiosity>",
  "secondary_text": "<optional smaller text, or empty string>",
  "expression": "<facial expression for the creator: shocked, excited, curious, angry, laughing, serious, confused, mind_blown>",
  "color_scheme": "<specific color guidance: e.g. 'high contrast yellow (#FFD700) on dark navy (#1a1a2e)', 'red and white urgency', 'neon green tech aesthetic'>",
  "layout": "<composition: e.g. 'face left 40%, text right 60%', 'centered face with text above', 'split screen comparison'>",
  "elements": ["<list of 3-5 visual elements to include>"],
  "style_reference": "<reference style: e.g. 'MrBeast-style bold text', 'minimalist tech review', 'tabloid drama', 'before/after transformation'>",
  "emotional_hook": "<what emotion should the thumbnail trigger in 0.5 seconds: curiosity, FOMO, shock, desire, fear>",
  "contrast_tip": "<specific tip to make it pop in the feed>"
}

Design for MAXIMUM click-through rate. Think about:
- What would make someone stop scrolling?
- The thumbnail must be readable at 120x68px (mobile size)
- High contrast and bold text always win
- Faces with emotions get 30% more clicks

Return ONLY valid JSON."""


class ThumbnailBriefAgent(BaseAgentExecutor):
    """Generates thumbnail concept briefs from completed scripts."""

    @property
    def name(self) -> str:
        return "thumbnail_brief"

    @property
    def description(self) -> str:
        return "Generates a thumbnail concept brief from a finished script"

    @property
    def priority(self) -> Priority:
        return Priority.LOW  # Non-critical, runs after save

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        script = input_data.get("script", "")
        hook = input_data.get("hook", "")
        topic = input_data.get("topic", "")

        # Build context from script (truncate to key parts)
        script_preview = script[:1500] if isinstance(script, str) else str(script)[:1500]

        user_content = f"""Topic: {topic}

Hook: {hook}

Script Preview:
{script_preview}"""

        messages = [
            LLMMessage(role="system", content=THUMBNAIL_PROMPT),
            LLMMessage(role="user", content=user_content),
        ]

        response = await self.llm_generate(
            messages=messages,
            task_type="CREATIVE",
            json_mode=True,
        )

        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            result = json.loads(content.strip())

        return result

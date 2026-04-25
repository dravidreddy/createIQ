"""
Hook Tester Agent — Scores the first 30 seconds of a script for hook strength.

Evaluates on 5 dimensions:
  - Curiosity Gap: Does it create an information gap?
  - Emotional Trigger: Does it evoke emotion?
  - Specificity: Is it specific vs generic?
  - Pattern Interrupt: Does it break the scroll?
  - Relevance: Does it match the topic and niche?

Returns an overall score (1-10), breakdown, verdict, and 2-3 rewrite suggestions.
"""

import json
import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json

logger = logging.getLogger(__name__)

HOOK_SCORING_PROMPT = """You are an expert YouTube/TikTok hook analyst. Your job is to score the opening hook of a script — the first ~30 seconds that determines whether viewers stay or leave.

{context_block}

Score the hook on these 5 dimensions (each 1-10):

1. **Curiosity Gap** — Does it create an irresistible information gap? ("I need to know what happens next")
2. **Emotional Trigger** — Does it evoke a strong emotion? (shock, fear, excitement, anger, awe)
3. **Specificity** — Is it concrete and specific, or vague and generic? ("I tested 47 AI tools" > "I tested some AI tools")
4. **Pattern Interrupt** — Does it break the viewer's scroll pattern? (unexpected opening, contrarian take, visual shock)
5. **Relevance** — Does the hook clearly connect to the topic and resonate with the target audience?

Return a JSON object with EXACTLY this structure:
{{
  "overall_score": <float 1-10, weighted average>,
  "breakdown": {{
    "curiosity_gap": <int 1-10>,
    "emotional_trigger": <int 1-10>,
    "specificity": <int 1-10>,
    "pattern_interrupt": <int 1-10>,
    "relevance": <int 1-10>
  }},
  "hook_text": "<the exact hook text you analyzed, first ~30 seconds>",
  "verdict": "<1-2 sentence assessment of the hook's strength and weakness>",
  "rewrites": [
    {{
      "text": "<rewritten hook that scores higher>",
      "predicted_score": <float>,
      "improvement": "<what was changed and why>"
    }},
    {{
      "text": "<alternative rewrite with different approach>",
      "predicted_score": <float>,
      "improvement": "<what was changed and why>"
    }}
  ]
}}

Be honest and critical. A score of 7+ means the hook is genuinely strong.
Most hooks score 4-6. Only truly exceptional hooks score 8+.
Return ONLY valid JSON."""


class HookTesterAgent(BaseAgentExecutor):
    """Scores hook strength and suggests rewrites."""

    @property
    def name(self) -> str:
        return "hook_tester"

    @property
    def description(self) -> str:
        return "Scores the first 30 seconds of a script for hook strength and suggests rewrites"

    @property
    def priority(self) -> Priority:
        return Priority.NORMAL

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        script_text = input_data.get("script_text", "")
        niche = input_data.get("niche", "")
        platform = input_data.get("platform", "")

        if not script_text.strip():
            return {
                "overall_score": 0,
                "breakdown": {
                    "curiosity_gap": 0,
                    "emotional_trigger": 0,
                    "specificity": 0,
                    "pattern_interrupt": 0,
                    "relevance": 0,
                },
                "hook_text": "",
                "verdict": "No script text provided.",
                "rewrites": [],
            }

        # Extract first ~150 words (≈30 seconds of speech)
        words = script_text.split()
        hook_text = " ".join(words[:150])

        if len(words) > 150:
            hook_text += "\n\n[... rest of script truncated for analysis ...]"

        # Build context block for niche/platform awareness
        context_parts = []
        if niche:
            context_parts.append(f"Content Niche: {niche}")
        if platform:
            context_parts.append(f"Platform: {platform}")

        if context_parts:
            context_block = "Context for scoring:\n" + "\n".join(context_parts) + "\n\nScore relative to what works in this specific niche and platform."
        else:
            context_block = ""

        system_prompt = HOOK_SCORING_PROMPT.format(context_block=context_block)

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=f"Analyze this hook:\n\n{hook_text}"),
        ]

        response = await self.llm_generate(
            messages=messages,
            task_type="scoring",
            json_mode=True,
        )

        # Parse response with robust fallback
        result = parse_llm_json(response.content, fallback={
            "overall_score": 0,
            "breakdown": {
                "curiosity_gap": 0,
                "emotional_trigger": 0,
                "specificity": 0,
                "pattern_interrupt": 0,
                "relevance": 0,
            },
            "hook_text": " ".join(words[:150]),
            "verdict": "Analysis failed.",
            "rewrites": [],
        })

        # Ensure hook_text is always present
        if "hook_text" not in result or not result["hook_text"]:
            result["hook_text"] = " ".join(words[:150])

        # Ensure relevance exists in breakdown (backward compat)
        if "relevance" not in result.get("breakdown", {}):
            result.setdefault("breakdown", {})["relevance"] = 5

        return result

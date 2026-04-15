"""
ScriptDrafterAgent — Stage 3 sub-agent (CRITICAL priority).

Writes the complete production-ready script with sections, visual notes,
CTAs, and engagement elements. This is the most important agent in the pipeline.
Respects user preferences for tone, style, length, and engagement.
"""

import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt
from app.schemas.llm_outputs import ScriptDraftOutput

logger = logging.getLogger(__name__)


class ScriptDrafterAgent(BaseAgentExecutor):
    """Writes full production-ready scripts. CRITICAL priority — max retries."""

    @property
    def name(self) -> str:
        return "ScriptDrafterAgent"

    @property
    def description(self) -> str:
        return "Drafts complete production-ready scripts"

    @property
    def priority(self) -> Priority:
        return Priority.CRITICAL

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        selected_idea = input_data.get("selected_idea", {})
        selected_hook = input_data.get("selected_hook", {})
        research = input_data.get("research", [])
        user_preferences = input_data.get("user_preferences", {})
        project_context = {**self.user_context, **(input_data.get("project_context", {}) or {})}
        style_overrides = project_context.get("style_overrides") or {}

        topic = selected_idea.get("title", "")
        self.log("info", f"Drafting script for: {topic}")

        # Build comprehensive context
        research_summary = ""
        if isinstance(research, list):
            research_summary = "\n".join([
                f"- {r.get('title', r.get('topic', ''))}: {str(r.get('content', r.get('key_data_points', '')))[:300]}"
                for r in research[:10]
            ])
        elif isinstance(research, str):
            research_summary = research[:3000]

        prompt_context = {**project_context, "selected_idea": selected_idea}
        system_prompt = await self.get_orchestrated_prompt(
            "script_drafter", prompt_context, user_preferences
        )
        user_prompt = load_user_prompt(
            "script_drafter",
            topic=topic,
            selected_idea=selected_idea,
            selected_hook=selected_hook,
            research_context=research_summary,
            user_preferences=user_preferences,
            platforms=project_context.get("platforms", ["YouTube"]),
            target_audience=project_context.get("target_audience", "general audience"),
            video_length=project_context.get("video_length", "Medium (1-10 min)"),
            language=project_context.get("language", "English"),
            vocabulary=project_context.get("vocabulary") or style_overrides.get("vocabulary"),
            avoid_words=project_context.get("avoid_words") or style_overrides.get("avoid_words"),
            pacing_style=project_context.get("pacing_style") or style_overrides.get("pacing_style"),
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_generate(
            messages,
            task_type="quality",
            max_tokens=4096,
            temperature=0.7,
            json_mode=True,
            response_schema=ScriptDraftOutput,
        )

        result = parse_llm_json(response.content, fallback={
            "title": topic,
            "hook": selected_hook.get("text", ""),
            "sections": [],
            "conclusion": "",
            "call_to_action": "",
            "full_script": response.content,
            "word_count": len(response.content.split()),
            "estimated_duration": "unknown",
        })

        # Ensure full_script exists
        if not result.get("full_script"):
            result["full_script"] = response.content

        self.log("info", f"Script drafted: {result.get('word_count', '?')} words")
        return result

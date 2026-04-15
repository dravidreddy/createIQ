"""
DeepResearcherAgent — Stage 3 sub-agent.

Performs deep research using web search, context extraction, and memory search
to build comprehensive background material for script writing.
"""

import asyncio
import logging
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.tools.search import get_tavily_tool
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt
from app.utils.context_pruner import ContextPruner
from app.schemas.llm_outputs import DeepResearchOutput

logger = logging.getLogger(__name__)


class DeepResearcherAgent(BaseAgentExecutor):
    """Deep research agent for comprehensive script background material."""

    @property
    def name(self) -> str:
        return "DeepResearcherAgent"

    @property
    def description(self) -> str:
        return "Performs deep research for script writing"

    @property
    def priority(self) -> Priority:
        return Priority.HIGH

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        selected_idea = input_data.get("selected_idea", {})
        selected_hook = input_data.get("selected_hook", {})
        project_context = {**self.user_context, **(input_data.get("project_context", {}) or {})}
        user_preferences = input_data.get("user_preferences", self.user_context.get("user_preferences", {}))
        topic = selected_idea.get("title", "")

        self.log("info", f"Deep research for: {topic}")

        # 1. Targeted web searches in parallel
        search_tool = get_tavily_tool()
        queries = [
            f"{topic} in-depth analysis facts statistics",
            f"{topic} expert opinions research studies",
            f"{topic} examples case studies",
            f"{topic} common misconceptions myths",
        ]

        self.log("tool_call", f"web_search: {len(queries)} queries in parallel")
        results_list = await asyncio.gather(*[
            search_tool.search(query, search_depth="advanced", max_results=5) for query in queries
        ], return_exceptions=True)

        all_results = []
        all_sources = []
        for result in results_list:
            if isinstance(result, Exception):
                self.log("warning", f"Search query failed: {result}")
                continue
            all_results.extend(result.get("results", []))
            all_sources.extend(result.get("sources", []))

        # 2. Get search context for LLM consumption
        self.log("tool_call", "search_context")
        context = await search_tool.search_context(f"{topic} comprehensive guide")

        # 3. Synthesize with LLM
        pruner = ContextPruner()
        all_results = pruner.prune_context_chunks(all_results, max_tokens=4000)

        system_prompt = await self.get_orchestrated_prompt(
            "deep_researcher", {**project_context, "topic": topic}, user_preferences
        )
        user_prompt = load_user_prompt(
            "deep_researcher",
            topic=topic,
            selected_idea=selected_idea,
            selected_hook=selected_hook,
            hook=selected_hook.get("text", ""),
        )

        research_text = "\n\n".join([
            f"**{r.get('title', '')}**\n{r.get('content', '')[:400]}"
            for r in all_results[:12]
        ])

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(
                role="user",
                content=f"{user_prompt}\n\n## Research Data:\n{research_text}\n\n## Extended Context:\n{context[:3000]}",
            ),
        ]

        # Prune total message history for Groq's 32k limit
        messages = pruner.prune_messages(messages, max_tokens=28000)

        response = await self.llm_generate(
            messages,
            task_type="quality",
            max_tokens=4096,
            json_mode=True,
            response_schema=DeepResearchOutput,
        )
        result = parse_llm_json(response.content, fallback={
            "research": all_results[:10],
            "context": context[:3000],
            "sources": list(set(all_sources)),
        })

        if "sources" not in result:
            result["sources"] = list(set(all_sources))

        return result

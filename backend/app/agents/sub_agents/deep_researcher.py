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
        system_prompt = load_system_prompt("deep_researcher")
        user_prompt = load_user_prompt(
            "deep_researcher",
            topic=topic,
            selected_idea=selected_idea,
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

        response = await self.llm_generate(messages, task_type="quality", max_tokens=4096)
        result = parse_llm_json(response.content, fallback={
            "research": all_results[:10],
            "context": context[:3000],
            "sources": list(set(all_sources)),
        })

        if "sources" not in result:
            result["sources"] = list(set(all_sources))

        return result

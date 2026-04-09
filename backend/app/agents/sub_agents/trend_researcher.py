"""
TrendResearcherAgent — Stage 1 sub-agent.

Performs targeted web searches to identify trending topics in the user's niche.
Uses Tavily search tool for real-time web research.
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

logger = logging.getLogger(__name__)


class TrendResearcherAgent(BaseAgentExecutor):
    """Searches web for trending topics in the user's niche."""

    @property
    def name(self) -> str:
        return "TrendResearcherAgent"

    @property
    def description(self) -> str:
        return "Performs targeted web searches for trending topics"

    @property
    def priority(self) -> Priority:
        return Priority.HIGH

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        topic = input_data.get("topic", "")
        niche = input_data.get("niche", "general")
        platforms = input_data.get("platforms", ["YouTube"])
        user_preferences = input_data.get("user_preferences", {})

        self.log("info", f"Researching trends for: {topic} in {niche}")

        # 1. Perform 4 targeted web searches in parallel
        search_tool = get_tavily_tool()
        queries = [
            f"trending {niche} content ideas 2025 {topic}",
            f"{topic} viral content trends {' '.join(platforms)}",
            f"latest {niche} news {topic}",
            f"{topic} audience engagement trends",
        ]

        self.log("tool_call", f"web_search: {len(queries)} queries in parallel")
        results_list = await asyncio.gather(*[
            search_tool.search(query, max_results=5) for query in queries
        ], return_exceptions=True)

        all_results = []
        all_sources = []
        for result in results_list:
            if isinstance(result, Exception):
                self.log("warning", f"Search query failed: {result}")
                continue
            all_results.extend(result.get("results", []))
            all_sources.extend(result.get("sources", []))

        # 2. Synthesize with LLM
        system_prompt = load_system_prompt(
            "trend_researcher",
            platforms=platforms,
            target_audience=input_data.get("target_audience", "general"),
            user_preferences=user_preferences,
        )
        user_prompt = load_user_prompt(
            "trend_researcher",
            topic=topic,
            niche=niche,
            platforms=platforms,
        )

        # Include search results in context, pruned to stay within budget
        pruner = ContextPruner()
        pruned_results = pruner.prune_context_chunks(all_results, max_tokens=4000)
        
        search_context = "\n\n".join([
            f"**{r.get('title', '')}** ({r.get('url', '')})\n{r.get('content', '')[:500]}"
            for r in pruned_results
        ])

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=f"{user_prompt}\n\n## Search Results:\n{search_context}"),
        ]

        # Prune total message history for Groq's 32k limit
        messages = pruner.prune_messages(messages, max_tokens=28000)

        response = await self.llm_generate(messages, task_type="quality")
        
        # DEBUG: Log raw response for evaluation analysis
        print(f"\n--- DEBUG: TREND RESEARCH RESPONSE FROM {response.model} ---\n{response.content}\n--- END DEBUG ---\n")
        
        result = parse_llm_json(response.content, fallback={
            "research_results": [],
            "sources": list(set(all_sources)),
        })

        # Ensure sources are included
        if "sources" not in result:
            result["sources"] = list(set(all_sources))

        return result

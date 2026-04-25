"""
TrendResearcherAgent — Stage 1 sub-agent.

Performs targeted web searches to identify trending topics in the user's niche.
Uses Tavily search tool for real-time web research.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.tools.search import get_tavily_tool
from app.tools.youtube import get_youtube_tool
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt
from app.utils.context_pruner import ContextPruner
from app.schemas.llm_outputs import TrendResearchOutput

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

        # 1. Perform targeted web searches in parallel
        search_tool = get_tavily_tool()
        youtube_tool = get_youtube_tool()
        
        queries = [
            f"trending {niche} content ideas {datetime.now().year} {topic}",
            f"{topic} viral content trends {' '.join(platforms)}",
            f"latest {niche} news {topic}",
        ]

        self.log("tool_call", f"web_search: {len(queries)} queries + 1 YouTube query in parallel")
        
        tasks = [search_tool.search(query, max_results=5) for query in queries]
        
        # Add YouTube search if platform is YouTube or not specified
        if "YouTube" in platforms or not platforms:
            yt_query = f"{topic} {niche} trending"
            tasks.append(youtube_tool.search_trends(yt_query, max_results=5, order="viewCount"))

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        all_results = []
        all_sources = []
        for result in results_list:
            if isinstance(result, Exception):
                self.log("warning", f"Search query failed: {result}")
                continue
            all_results.extend(result.get("results", []))
            all_sources.extend(result.get("sources", []))

        # 2. Synthesize with LLM
        project_ctx = {
            "platforms": platforms,
            "target_audience": input_data.get("target_audience", "general"),
            "niche": niche,
            "topic": topic,
        }
        system_prompt = await self.get_orchestrated_prompt(
            "trend_researcher", project_ctx, user_preferences
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

        response = await self.llm_generate(
            messages,
            task_type="quality",
            json_mode=True,
            response_schema=TrendResearchOutput,
        )
        
        logger.debug("TrendResearcher raw response from %s (%d chars)", response.model, len(response.content))
        
        result = parse_llm_json(response.content, fallback={
            "research_results": [],
            "sources": list(set(all_sources)),
        })

        # Ensure sources are included
        if "sources" not in result:
            result["sources"] = list(set(all_sources))

        return result

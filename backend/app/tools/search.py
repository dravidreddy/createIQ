"""
Tavily Search Tool — True async wrapper.

Web search tool for content research using Tavily API.
All synchronous Tavily SDK calls are wrapped with asyncio.to_thread()
to avoid blocking the event loop.
"""

import asyncio
import logging
from typing import Any, Dict, List

from tavily import TavilyClient

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Module-level singleton
_tavily_instance = None


def get_tavily_tool() -> "TavilySearchTool":
    """Get or create the shared TavilySearchTool singleton."""
    global _tavily_instance
    if _tavily_instance is None:
        if settings.load_test_mode:
            from app.utils.test_mocks import MockSearchTool
            _tavily_instance = MockSearchTool()
            logger.info("TavilySearchTool: Using MockSearchTool for load testing")
        else:
            _tavily_instance = TavilySearchTool()
    return _tavily_instance


class TavilySearchTool:
    """
    Tavily search tool for web research.

    Provides real-time web search capabilities for:
    - Trend discovery
    - Fact-checking
    - Research gathering

    All calls are non-blocking via asyncio.to_thread().
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.tavily_api_key
        self.client = TavilyClient(api_key=self.api_key)

    async def search(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 5,
        include_domains: List[str] = None,
        exclude_domains: List[str] = None,
    ) -> Dict[str, Any]:
        """Perform a non-blocking web search."""
        try:
            logger.info("Searching: %s", query)

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.search,
                    query=query,
                    search_depth=search_depth,
                    max_results=max_results,
                    include_domains=include_domains or [],
                    exclude_domains=exclude_domains or [],
                ),
                timeout=15.0
            )

            results = {
                "query": query,
                "results": [],
                "answer": response.get("answer", ""),
                "sources": [],
            }

            for item in response.get("results", []):
                results["results"].append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0),
                })
                results["sources"].append(item.get("url", ""))

            logger.info("Found %d results for: %s", len(results["results"]), query)
            return results

        except Exception as e:
            logger.error("Search error for query '%s': %s", query, e)
            raise  # Let BaseAgentExecutor handle retry/degrade

    async def search_context(
        self,
        query: str,
        search_depth: str = "advanced",
        max_tokens: int = 4000,
    ) -> str:
        """Search and return formatted context for LLM (non-blocking)."""
        try:
            context = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.get_search_context,
                    query=query,
                    search_depth=search_depth,
                    max_tokens=max_tokens,
                ),
                timeout=15.0
            )
            return context
        except Exception as e:
            logger.error("Context search error: %s", e)
            return f"Error searching: {e}"

    async def search_qna(self, query: str) -> str:
        """Get a direct answer to a question (non-blocking)."""
        try:
            answer = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.qna_search,
                    query=query,
                ),
                timeout=15.0
            )
            return answer
        except Exception as e:
            logger.error("QnA search error: %s", e)
            return f"Error: {e}"


def get_tavily_tool_definition() -> Dict[str, Any]:
    """Get tool definition for LLM function calling."""
    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for real-time information on any topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "search_depth": {
                        "type": "string",
                        "enum": ["basic", "advanced"],
                        "description": "Search depth",
                    },
                },
                "required": ["query"],
            },
        },
    }

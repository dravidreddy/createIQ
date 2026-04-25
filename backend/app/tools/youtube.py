"""
YouTube Data API Tool — True async wrapper.

Fetches real-time video trending data and metrics via YouTube Data API v3.
All synchronous googleapiclient calls are wrapped with asyncio.to_thread()
to avoid blocking the event loop.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Module-level singleton
_youtube_instance = None


def get_youtube_tool() -> "YouTubeSearchTool":
    """Get or create the shared YouTubeSearchTool singleton."""
    global _youtube_instance
    if _youtube_instance is None:
        if settings.load_test_mode:
            from app.utils.test_mocks import MockSearchTool # Fallback to generic mock
            _youtube_instance = MockSearchTool()
            logger.info("YouTubeSearchTool: Using MockSearchTool for load testing")
        else:
            _youtube_instance = YouTubeSearchTool()
    return _youtube_instance


class YouTubeSearchTool:
    """
    YouTube Data API search tool for real-time video metrics.

    Provides real-time search capabilities for:
    - YouTube viral trends
    - Competitor analysis
    - Video view/date metrics

    All calls are non-blocking via asyncio.to_thread().
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.youtube_api_key
        # Delay initialization of build() until needed to prevent errors if key is missing
        self._youtube = None

    def _get_client(self):
        """Lazy initialization of the YouTube API client."""
        if not self._youtube:
            if not self.api_key:
                raise ValueError("YouTube API key is not configured.")
            self._youtube = build("youtube", "v3", developerKey=self.api_key, cache_discovery=False)
        return self._youtube

    async def search_trends(
        self,
        query: str,
        max_results: int = 5,
        order: str = "relevance", # "relevance", "date", "rating", "title", "videoCount", "viewCount"
    ) -> Dict[str, Any]:
        """
        Perform a non-blocking YouTube search and return video metrics.
        Returns empty results gracefully if API key is missing.
        """
        if not self.api_key:
            logger.warning("YouTubeSearchTool: No API key configured. Skipping YouTube search.")
            return {"query": query, "results": [], "sources": []}

        try:
            logger.info("YouTube Searching: %s", query)
            youtube = self._get_client()

            # 1. Search for videos
            search_response = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: youtube.search().list(
                        q=query,
                        part="id,snippet",
                        maxResults=max_results,
                        type="video",
                        order=order,
                    ).execute()
                ),
                timeout=15.0
            )

            video_ids = []
            for item in search_response.get("items", []):
                if item["id"]["kind"] == "youtube#video":
                    video_ids.append(item["id"]["videoId"])

            if not video_ids:
                return {"query": query, "results": [], "sources": []}

            # 2. Fetch video statistics (views, likes, etc.)
            stats_response = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: youtube.videos().list(
                        id=",".join(video_ids),
                        part="snippet,statistics",
                    ).execute()
                ),
                timeout=15.0
            )

            results = {
                "query": query,
                "results": [],
                "sources": [],
            }

            for item in stats_response.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                video_id = item.get("id")
                url = f"https://www.youtube.com/watch?v={video_id}"

                # Format human-readable output
                title = snippet.get("title", "")
                channel = snippet.get("channelTitle", "")
                views = stats.get("viewCount", "0")
                published_at = snippet.get("publishedAt", "")[:10]

                # Create a dense content string for the LLM
                content = f"[YouTube Video] Title: '{title}' | Channel: {channel} | Views: {views} | Published: {published_at}"

                results["results"].append({
                    "title": title,
                    "url": url,
                    "content": content,
                    "score": 1.0, # Dummy score to match Tavily format
                    "metadata": {
                        "views": int(views),
                        "channel": channel,
                        "published_at": published_at,
                    }
                })
                results["sources"].append(url)

            logger.info("YouTubeSearchTool: Found %d videos for: %s", len(results["results"]), query)
            return results

        except HttpError as e:
            logger.error("YouTube API error for query '%s': %s", query, e.reason)
            return {"query": query, "results": [], "sources": []}
        except Exception as e:
            logger.error("YouTube Search error for query '%s': %s", query, e)
            return {"query": query, "results": [], "sources": []}

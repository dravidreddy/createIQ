"""
Feedback Loop Service — Capture and store user feedback for routing optimization.
"""

from app.utils.datetime_utils import utc_now
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FeedbackLoopService:
    """
    Service to collect and analyze user feedback on LLM outputs.
    """

    def __init__(self, db_client: Optional[AsyncIOMotorClient] = None):
        self._client = db_client or AsyncIOMotorClient(settings.mongodb_url)
        self._db = self._client.get_database("creatoriq_feedback")
        self._collection = self._db.get_collection("model_feedback")

    async def record_feedback(
        self,
        user_id: str,
        job_id: str,
        stage_name: str,
        model_id: str,
        rating: int,        # 1-5
        comment: str = "",
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Record user feedback for a specific node execution.
        """
        doc = {
            "user_id": user_id,
            "job_id": job_id,
            "stage_name": stage_name,
            "model_id": model_id,
            "rating": rating,
            "comment": comment,
            "metadata": metadata or {},
            "timestamp": utc_now().isoformat()
        }
        
        result = await self._collection.insert_one(doc)
        logger.info(f"FeedbackLoop: recorded {rating}/5 for {model_id} in {stage_name}")
        return str(result.inserted_id)

    async def get_model_performance(self, model_id: str) -> Dict[str, Any]:
        """
        Aggregate performance metrics for a specific model.
        """
        cursor = self._collection.aggregate([
            {"$match": {"model_id": model_id}},
            {"$group": {
                "_id": "$model_id",
                "avg_rating": {"$avg": "$rating"},
                "total_reviews": {"$sum": 1}
            }}
        ])
        results = await cursor.to_list(length=1)
        return results[0] if results else {"avg_rating": 3.0, "total_reviews": 0}

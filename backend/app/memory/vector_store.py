"""
QdrantVectorStore — Single-collection vector store for semantic memory.

Uses a SINGLE Qdrant collection ('creatoriq_memory') with metadata filters
for user_id, project_id, and content_type. Embeddings generated via
the google-genai async SDK (text-embedding-004, 768 dimensions).
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types as genai_types

import asyncio
import time
import backoff
from app.config import get_settings
from app.models import infrastructure
from app.models.infrastructure import get_qdrant, qdrant_cb, CircuitState
from app.utils.determinism import get_now, get_uuid

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.http import models as qmodels
    from qdrant_client.http.exceptions import UnexpectedResponse

    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    class UnexpectedResponse(Exception): pass # Mock for type safety
    logger.warning("qdrant-client not installed — vector memory disabled")


class QdrantVectorStore:
    """Qdrant adapter using a single shared collection with metadata filters."""

    COLLECTION_NAME = "creatoriq_memory"
    VECTOR_SIZE = 768  # text-embedding-004
    DISTANCE_METRIC = qmodels.Distance.COSINE

    def __init__(self):
        self._client: Optional["AsyncQdrantClient"] = None
        self._genai_client: Optional[genai.Client] = None
        self._initialized = False

    async def _ensure_client(self) -> Optional["AsyncQdrantClient"]:
        """Centralized singleton Qdrant Cloud client (Respects health state).."""
        if not QDRANT_AVAILABLE or not infrastructure.QDRANT_READY:
            return None
            
        self._client = get_qdrant()

        if settings.gemini_api_key and self._genai_client is None:
            self._genai_client = genai.Client(api_key=settings.gemini_api_key)

        return self._client

    @backoff.on_exception(
        backoff.expo,
        (Exception,),
        max_tries=3,
        logger=logger
    )
    async def init_collection(self) -> None:
        """[MANDATORY FIX] Idempotent collection initialization with schema validation."""
        client = await self._ensure_client()
        if client is None:
            raise RuntimeError("Qdrant client not available for initialization")

        # 1. Check if exists and validate schema
        try:
            collection_info = await asyncio.wait_for(
                client.get_collection(self.COLLECTION_NAME),
                timeout=5.0
            )
            
            # [MANDATORY FIX] Schema Validation
            config = collection_info.config.params.vectors
            # Handle both single vector and named vectors if ever extended
            actual_size = config.size if hasattr(config, "size") else None
            actual_distance = config.distance if hasattr(config, "distance") else None

            if actual_size != self.VECTOR_SIZE or actual_distance != self.DISTANCE_METRIC:
                error_msg = (
                    f"CRITICAL: Qdrant Schema Mismatch for '{self.COLLECTION_NAME}'. "
                    f"Expected: size={self.VECTOR_SIZE}, distance={self.DISTANCE_METRIC}. "
                    f"Actual: size={actual_size}, distance={actual_distance}."
                )
                logger.critical(error_msg)
                raise RuntimeError(error_msg)
            
            logger.info("QdrantVectorStore: Existing collection '%s' validated successfully.", self.COLLECTION_NAME)
            
        except UnexpectedResponse as e:
            if e.status_code == 404:
                # 2. Create collection if missing
                logger.info("QdrantVectorStore: Collection '%s' missing. Creating now...", self.COLLECTION_NAME)
                try:
                    await asyncio.wait_for(
                        client.create_collection(
                            collection_name=self.COLLECTION_NAME,
                            vectors_config=qmodels.VectorParams(
                                size=self.VECTOR_SIZE,
                                distance=self.DISTANCE_METRIC,
                            ),
                        ),
                        timeout=10.0
                    )
                    
                    # Create payload indexes for efficient filtering
                    for field_name in ("user_id", "project_id", "thread_id", "content_type"):
                        await client.create_payload_index(
                            collection_name=self.COLLECTION_NAME,
                            field_name=field_name,
                            field_schema=qmodels.PayloadSchemaType.KEYWORD,
                        )
                    logger.info("QdrantVectorStore: Created collection '%s' with payload indexes.", self.COLLECTION_NAME)
                except UnexpectedResponse as e2:
                    if e2.status_code == 409:
                        logger.info("QdrantVectorStore: Collection created by another instance (409). Continuing.")
                    else:
                        raise
            else:
                raise
        except asyncio.TimeoutError:
            logger.error("QdrantVectorStore: Initialization TIMEOUT (10s)")
            raise

        self._initialized = True

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding using google-genai async SDK."""
        if not self._genai_client:
            # Fallback: return zero vector
            logger.warning("QdrantVectorStore: no embedding client — returning zero vector")
            return []

        try:
            result = await self._genai_client.aio.models.embed_content(
                model="gemini-embedding-001",
                contents=text[:2000],  # Truncate to avoid token limits
                config={"output_dimensionality": self.VECTOR_SIZE},  # Match Qdrant collection (768)
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error("QdrantVectorStore: embedding failed — %s", e)
            return []

    async def upsert(
        self,
        content: str,
        user_id: str,
        thread_id: str,
        project_id: Optional[str] = None,
        content_type: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        # Circuit Breaker Check
        if not await qdrant_cb.is_allowed():
            logger.warning(f"VectorStore: Qdrant Circuit Breaker is {qdrant_cb.state.value}. Skipping upsert.")
            return ""

        client = await self._ensure_client()
        if client is None:
            return ""

        # [MANDATORY FIX] Strict Eager Initialization Enforcement
        if not self._initialized:
            # Note: We expect eager initialization to have happened. 
            # In production, this being False here suggests a failed handshake.
            logger.warning("VectorStore: Unexpected lazy init triggered in upsert. Initializing...")
            await self.init_collection()

        embedding = await self._get_embedding(content)
        if not embedding:
            return ""
        point_id = get_uuid()

        payload = {
            "user_id": user_id,
            "project_id": project_id or "",
            "thread_id": thread_id,
            "content_type": content_type,
            "content": content[:5000],  # Truncate stored content
            "metadata": metadata or {},
            "created_at": get_now().isoformat(),
        }

        # [MANDATORY FIX] Exponential Backoff for Upsert
        @backoff.on_exception(
            backoff.expo,
            (Exception,),
            max_tries=3,
            logger=logger
        )
        async def _reliable_upsert():
            start_time = time.time()
            try:
                await self._execute_upsert(client, point_id, embedding, payload)
                await qdrant_cb.record_success((time.time() - start_time) * 1000)
            except UnexpectedResponse as e:
                if e.status_code == 404:
                    logger.warning(f"VectorStore: Unexpected 404 for '{self.COLLECTION_NAME}'. Recovering...")
                    await self.init_collection()
                    raise # Backoff will retry
                else:
                    await qdrant_cb.record_failure()
                    raise
            except asyncio.TimeoutError:
                await qdrant_cb.record_failure(is_timeout=True)
                raise
            except Exception:
                await qdrant_cb.record_failure()
                raise

        await _reliable_upsert()
        return point_id

    async def _execute_upsert(self, client, point_id, embedding, payload):
        """Execute raw Qdrant upsert."""
        await asyncio.wait_for(
            client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[qmodels.PointStruct(id=point_id, vector=embedding, payload=payload)],
            ),
            timeout=5.0
        )

    async def search(
        self,
        query: str,
        user_id: str,
        thread_id: str,
        project_id: Optional[str] = None,
        content_type: Optional[str] = None,
        top_k: int = 5,
        recency_weight: float = 0.2, # Max boost percentage
    ) -> List[Dict[str, Any]]:
        # Circuit Breaker Check
        if not await qdrant_cb.is_allowed():
            logger.warning(f"VectorStore: Qdrant Circuit Breaker is {qdrant_cb.state.value}. Skipping search.")
            return []

        client = await self._ensure_client()
        if client is None:
            return []

        if not self._initialized:
            await self.init_collection()

        query_vector = await self._get_embedding(query)
        if not query_vector:
            return []

        # Build filter
        must_conditions = [
            qmodels.FieldCondition(key="user_id", match=qmodels.MatchValue(value=user_id)),
        ]
        if project_id:
            must_conditions.append(qmodels.FieldCondition(key="project_id", match=qmodels.MatchValue(value=project_id)))
        if content_type:
            must_conditions.append(qmodels.FieldCondition(key="content_type", match=qmodels.MatchValue(value=content_type)))

        search_filter = qmodels.Filter(must=must_conditions)

        # Timeout Protected Search
        start_time = time.time()
        try:
            results = await asyncio.wait_for(
                client.query_points(
                    collection_name=self.COLLECTION_NAME,
                    query=query_vector,
                    query_filter=search_filter,
                    limit=top_k * 2,
                ),
                timeout=5.0
            )
            await qdrant_cb.record_success((time.time() - start_time) * 1000)
        except asyncio.TimeoutError:
            logger.error("VectorStore: Qdrant search TIMEOUT (5s)")
            await qdrant_cb.record_failure(is_timeout=True)
            return []
        except Exception as e:
            logger.error(f"VectorStore: Qdrant search FAILED: {e}")
            await qdrant_cb.record_failure()
            return []

        now = get_now()
        reranked = []
        
        for hit in results.points:
            score = hit.score
            created_at_str = hit.payload.get("created_at")
            
            # Recency Boost: linear decay over 7 days
            boost = 0.0
            if thread_id and hit.payload.get("thread_id") == thread_id:
                boost += 0.05
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    age_hours = (now - created_at).total_seconds() / 3600
                    if age_hours < 168: # 7 days
                        boost = recency_weight * (1.0 - (age_hours / 168.0))
                except Exception as e:
                    logger.warning(f"Failed to parse created_at for recency boost: {e}")
            
            reranked.append({
                "content": hit.payload.get("content", ""),
                "content_type": hit.payload.get("content_type", ""),
                "project_id": hit.payload.get("project_id", ""),
                "similarity_score": hit.score,
                "final_score": score + boost,
                "metadata": hit.payload.get("metadata", {}),
                "created_at": created_at_str,
            })

        # Sort by final score and take top_k
        reranked.sort(key=lambda x: x["final_score"], reverse=True)
        return reranked[:top_k]

    async def delete_by_user(self, user_id: str) -> None:
        """Delete all vectors for a user."""
        client = await self._ensure_client()
        if client is None:
            return

        await client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="user_id",
                            match=qmodels.MatchValue(value=user_id),
                        )
                    ]
                )
            ),
        )

async def initialize_vector_store() -> None:
    """Eagerly initialize the default vector store collection (creatoriq_memory)."""
    if not QDRANT_AVAILABLE:
        return
        
    store = QdrantVectorStore()
    logger.info(f"VectorStore: Initializing collection '{store.COLLECTION_NAME}'...")
    try:
        await store.init_collection()
        logger.info(f"VectorStore: Core collection '{store.COLLECTION_NAME}' is READY.")
    except Exception as e:
        logger.error(f"VectorStore: FATAL Initialization failure: {e}")
        # [MANDATORY FIX] Fail-fast: Re-raise to ensure the app handshake stops
        raise

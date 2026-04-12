"""
MongoDBCheckpointer — LangGraph-compatible checkpoint saver using MongoDB.

Persists LangGraph state to MongoDB so pipelines survive server restarts
and can resume from any interrupt point.
"""

import uuid
import lz4.frame
import json
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Optional, Sequence, Tuple

from beanie.operators import Set
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

from app.models.pipeline_checkpoint import PipelineCheckpoint
from app.utils.determinism import get_now

logger = logging.getLogger(__name__)


class MongoDBCheckpointer(BaseCheckpointSaver):
    """Persists LangGraph checkpoints to MongoDB via Beanie ODM."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_thread_id(self, config: RunnableConfig) -> str:
        """Extract thread_id from config."""
        return config.get("configurable", {}).get("thread_id", "default")

    def _get_checkpoint_ns(self, config: RunnableConfig) -> str:
        """Extract checkpoint namespace from config."""
        return config.get("configurable", {}).get("checkpoint_ns", "")

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Load the latest checkpoint for a thread from MongoDB."""
        thread_id = self._get_thread_id(config)
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id") or ""

        query = {"thread_id": thread_id}
        if checkpoint_id:
            doc = await PipelineCheckpoint.find_one(
                PipelineCheckpoint.thread_id == thread_id,
                PipelineCheckpoint.checkpoint_id == checkpoint_id,
            )
        else:
            doc = await PipelineCheckpoint.find_one(
                PipelineCheckpoint.thread_id == thread_id,
                sort=[("created_at", -1)],
            )

        if doc is None:
            return None

        checkpoint_raw = doc.checkpoint_data
        if doc.is_compressed and isinstance(checkpoint_raw, bytes):
            try:
                decompressed = lz4.frame.decompress(checkpoint_raw)
                checkpoint = json.loads(decompressed.decode("utf-8"))
            except Exception as e:
                logger.error(f"Failed to decompress checkpoint: {e}")
                checkpoint = {}
        else:
            checkpoint = checkpoint_raw

        metadata = doc.metadata

        parent_config = None
        if doc.parent_checkpoint_id:
            parent_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": doc.parent_checkpoint_id,
                }
            }

        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": doc.checkpoint_id,
                }
            },
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=parent_config,
        )

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[dict] = None,
    ) -> RunnableConfig:
        """Save a checkpoint to MongoDB."""
        thread_id = self._get_thread_id(config)
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id") or checkpoint.get("id") or ""
        parent_id = config.get("configurable", {}).get("parent_checkpoint_id") or checkpoint.get("parent_id")

        # Compress data
        checkpoint_dict = dict(checkpoint) if checkpoint else {}
        try:
            compressed = lz4.frame.compress(json.dumps(checkpoint_dict).encode("utf-8"))
            checkpoint_to_save = compressed
            is_compressed = True
        except Exception as e:
            logger.warning(f"Compression failed, saving as dict: {e}")
            checkpoint_to_save = checkpoint_dict
            is_compressed = False

        doc = PipelineCheckpoint(
            thread_id=thread_id,
            checkpoint_id=checkpoint_id or "",
            parent_checkpoint_id=parent_id or "",
            checkpoint_data=checkpoint_to_save,
            metadata=dict(metadata) if metadata else {},
            is_compressed=is_compressed,
            created_at=get_now(),
        )
        
        # Upsert based on thread_id and checkpoint_id
        await PipelineCheckpoint.find_one(
            PipelineCheckpoint.thread_id == thread_id,
            PipelineCheckpoint.checkpoint_id == checkpoint_id,
        ).upsert(
            Set(doc.model_dump(exclude={"id", "created_at"})),
            on_insert=doc,
        )

        # PRUNING: Keep only last 3 checkpoints for this thread (Atomic cleanup)
        try:
            old_docs = await PipelineCheckpoint.find(
                PipelineCheckpoint.thread_id == thread_id
            ).sort("-created_at").skip(3).to_list()
            
            if old_docs:
                ids_to_delete = [doc.id for doc in old_docs]
                await PipelineCheckpoint.find({"_id": {"$in": ids_to_delete}}).delete()
                logger.debug(f"Pruned {len(ids_to_delete)} old checkpoints for thread {thread_id}")
        except Exception as e:
            logger.warning(f"Pruning failed for thread {thread_id}: {e}")

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }

    async def alist(
        self,
        config: Optional[RunnableConfig] = None,
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """List checkpoints for a thread."""
        thread_id = self._get_thread_id(config) if config else None

        query_filter = {}
        if thread_id:
            query_filter["thread_id"] = thread_id

        docs = await PipelineCheckpoint.find(
            PipelineCheckpoint.thread_id == thread_id if thread_id else {},
        ).sort("-created_at").limit(limit or 10).to_list()

        for doc in docs:
            parent_config = None
            if doc.parent_checkpoint_id:
                parent_config = {
                    "configurable": {
                        "thread_id": doc.thread_id,
                        "checkpoint_id": doc.parent_checkpoint_id,
                    }
                }

            yield CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": doc.thread_id,
                        "checkpoint_id": doc.checkpoint_id,
                    }
                },
                checkpoint=doc.checkpoint_data,
                metadata=doc.metadata,
                parent_config=parent_config,
            )

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Store intermediate writes (pending sends). Stored as metadata."""
        thread_id = self._get_thread_id(config)
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id") or ""

        if checkpoint_id:
            doc = await PipelineCheckpoint.find_one(
                PipelineCheckpoint.thread_id == thread_id,
                PipelineCheckpoint.checkpoint_id == checkpoint_id,
            )
            if doc:
                pending = doc.metadata.get("pending_writes", [])
                for channel, value in writes:
                    pending.append({
                        "task_id": task_id,
                        "channel": channel,
                        "value": str(value)[:5000],
                    })
                doc.metadata["pending_writes"] = pending
                await doc.save()

    # Sync versions (required by base class but we explicitly use async execution)
    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        logger.warning("Synchronous get_tuple() called on MongoDBCheckpointer. This should be aget_tuple() in async mode. Returning None to fail gracefully.")
        return None

    def put(self, config, checkpoint, metadata, new_versions=None) -> RunnableConfig:
        logger.warning("Synchronous put() called on MongoDBCheckpointer. Returning config silently.")
        return config

    def put_writes(self, config, writes, task_id):
        logger.warning("Synchronous put_writes() called on MongoDBCheckpointer.")

    def list(self, config=None, *, filter=None, before=None, limit=None):
        logger.warning("Synchronous list() called on MongoDBCheckpointer. Returning empty iterator.")
        return iter([])

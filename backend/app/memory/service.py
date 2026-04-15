"""
MemoryService — Unified access layer for all memory operations.

Composes vector store, user memory, and project memory into a single
interface used by the pipeline and agent groups.
"""

import logging
from typing import Any, Dict, List, Optional

from app.memory.vector_store import QdrantVectorStore
from app.memory.user_memory import UserMemoryStore
from app.memory.project_memory import ProjectMemoryStore
from app.memory.edit_detector import EditDetectionEngine

logger = logging.getLogger(__name__)

# Module-level singleton instances
_vector_store: Optional[QdrantVectorStore] = None
_user_memory: Optional[UserMemoryStore] = None
_project_memory: Optional[ProjectMemoryStore] = None
_edit_detector: Optional[EditDetectionEngine] = None

import threading

_init_lock = threading.Lock()

class MemoryService:
    """Unified access layer for all memory operations."""

    def __init__(self):
        self._init_internal()

    def _init_internal(self):
        global _vector_store, _user_memory, _project_memory, _edit_detector
        if _vector_store is None or _user_memory is None or _project_memory is None or _edit_detector is None:
            with _init_lock:
                if _vector_store is None:
                    _vector_store = QdrantVectorStore()
                if _user_memory is None:
                    _user_memory = UserMemoryStore()
                if _project_memory is None:
                    _project_memory = ProjectMemoryStore()
                if _edit_detector is None:
                    _edit_detector = EditDetectionEngine()
        
        self.vector_store = _vector_store
        self.user_memory = _user_memory
        self.project_memory = _project_memory
        self.edit_detector = _edit_detector

    # ── User preferences ────────────────────────────────────────

    async def get_user_preferences(self, user_id: str) -> Dict:
        """Load persistent user preferences from MongoDB."""
        return await self.user_memory.load(user_id)

    async def update_user_preferences(
        self, user_id: str, signals: Dict[str, float]
    ) -> None:
        """Update user preferences with new signals from edit detection."""
        await self.user_memory.update_from_signals(user_id, signals)

    # ── Project context ─────────────────────────────────────────

    async def get_project_context(self, project_id: str) -> Dict:
        """Load project-specific context from MongoDB."""
        return await self.project_memory.load(project_id)

    async def save_project_artifact(
        self,
        project_id: str,
        thread_id: str,
        artifact_type: str,
        content: Any,
        user_id: str = "",
    ) -> None:
        """Save a pipeline artifact (idea, hook, script, etc.)."""
        await self.project_memory.save_artifact(project_id, artifact_type, content)

        # Also store in vector memory for future semantic retrieval
        try:
            content_str = str(content)[:3000] if not isinstance(content, str) else content[:3000]
            await self.vector_store.upsert(
                content=content_str,
                user_id=user_id or "pipeline",
                thread_id=thread_id,
                project_id=project_id,
                content_type=artifact_type,
            )
        except Exception as e:
            logger.warning("MemoryService: vector upsert failed for %s — %s", artifact_type, e)

    # ── Semantic search ─────────────────────────────────────────

    async def search_similar(
        self,
        query: str,
        user_id: str,
        thread_id: str,
        project_id: Optional[str] = None,
        content_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict]:
        """Semantic search across user/project memory via Qdrant."""
        return await self.vector_store.search(
            query=query,
            user_id=user_id,
            thread_id=thread_id,
            project_id=project_id,
            content_type=content_type,
            top_k=top_k,
        )

    async def store_embedding(
        self,
        content: str,
        user_id: str,
        thread_id: str,
        project_id: Optional[str] = None,
        content_type: str = "",
        metadata: Optional[Dict] = None,
    ) -> str:
        """Store content embedding in Qdrant vector store."""
        return await self.vector_store.upsert(
            content=content,
            user_id=user_id,
            thread_id=thread_id,
            project_id=project_id,
            content_type=content_type,
            metadata=metadata,
        )

    # ── Edit detection + preference update ──────────────────────

    async def record_edit(
        self,
        user_id: str,
        project_id: str,
        stage: str,
        original: Any,
        edited: Any,
    ) -> Dict:
        """Analyze user edit, extract preference signals, update memory.

        Returns the EditRecord dict.
        """
        # 1. Analyze the edit
        analysis = await self.edit_detector.analyze_edit(
            str(original), str(edited)
        )

        # 2. Update user preferences via EMA
        signals = analysis.get("preference_signals", {})
        if any(abs(v) > 0.05 for v in signals.values()):
            await self.update_user_preferences(user_id, signals)

        # 3. Record in project memory
        from datetime import datetime
        edit_record = {
            "stage": stage,
            "original_content": original,
            "edited_content": edited,
            "diff_summary": analysis.get("diff_summary", ""),
            "preference_signals": signals,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.project_memory.append_edit(project_id, edit_record)

        logger.info(
            "MemoryService: recorded edit for stage '%s' — signals: %s",
            stage, signals
        )
        return edit_record

    # ── Initialization ──────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize vector store collection (call on app startup)."""
        await self.vector_store.init_collection()
        logger.info("MemoryService: initialized")

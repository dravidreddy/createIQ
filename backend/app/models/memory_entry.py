"""
Memory Embedding Document — MongoDB / Beanie

Stores text + vector embeddings for AI memory / retrieval-augmented generation.
Designed to work with MongoDB Atlas Vector Search or external FAISS.
"""

from datetime import datetime
from typing import List, Optional

from beanie import Document, Indexed
from pymongo import IndexModel, ASCENDING
from pydantic import Field


class MemoryEntry(Document):
    """A memory entry with optional embedding vector."""

    user_id: Indexed(str)  # type: ignore[valid-type]
    project_id: Optional[str] = None

    entry_type: str = "generation_summary"  # generation_summary | user_preference | ...
    content: str = ""

    # Vector embedding — populated by sentence-transformers or similar
    # Empty list when not yet embedded
    embedding: List[float] = Field(default_factory=list)

    metadata: dict = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "memory_embeddings"
        use_state_management = True
        indexes = [
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("entry_type", ASCENDING)]),
        ]

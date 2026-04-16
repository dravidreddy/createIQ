"""
Memory Schemas

Pydantic schemas for the memory subsystem — user preferences,
edit records, and vector search results.
"""

from app.utils.datetime_utils import utc_now
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserPreferencesSchema(BaseModel):
    """User preference profile returned by the memory service."""
    writing_style: str = "conversational"
    tone: str = "enthusiastic"
    preferred_length: str = "detailed"
    vocabulary_level: str = "moderate"
    engagement_style: str = "question-heavy"
    custom_signals: Dict[str, float] = {}


class EditRecordSchema(BaseModel):
    """Record of a user edit at a pipeline stage."""
    stage: str
    original_content: Any
    edited_content: Any
    diff_summary: str = ""
    preference_signals: Dict[str, float] = {}
    timestamp: str = Field(default_factory=lambda: utc_now().isoformat())


class PreferenceSignals(BaseModel):
    """Signals extracted from a user edit by the EditDetectionEngine."""
    tone_shift: float = 0.0       # -1 (more formal) to +1 (more casual)
    length_preference: float = 0.0  # -1 (shorter) to +1 (longer)
    complexity_shift: float = 0.0   # -1 (simpler) to +1 (more complex)
    engagement_shift: float = 0.0   # -1 (less interactive) to +1 (more interactive)


class EditAnalysisResult(BaseModel):
    """Full analysis output from EditDetectionEngine."""
    diff_summary: str
    changes: List[Dict[str, str]] = []
    preference_signals: PreferenceSignals = PreferenceSignals()


class MemorySearchResult(BaseModel):
    """A single result from semantic memory search."""
    content: str
    content_type: str = ""
    project_id: Optional[str] = None
    similarity_score: float = 0.0
    metadata: Dict[str, Any] = {}
    created_at: Optional[str] = None

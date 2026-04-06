"""
UserPreferences Beanie Document

Persistent storage for learned user preferences derived from
edit detection and explicit user feedback. Updated via EMA (exponential
moving average) as users make edits throughout the pipeline.
"""

from datetime import datetime
from typing import Dict

from beanie import Document, Indexed


class UserPreferencesModel(Document):
    """Persisted user preference profile, learned from edits."""

    user_id: Indexed(str, unique=True)
    writing_style: str = "conversational"        # conversational | formal | technical
    tone: str = "enthusiastic"                    # enthusiastic | neutral | professional
    preferred_length: str = "detailed"            # concise | detailed | mixed
    vocabulary_level: str = "moderate"            # simple | moderate | advanced
    engagement_style: str = "question-heavy"      # question-heavy | story-driven | data-driven
    custom_signals: Dict[str, float] = {}
    edit_count: int = 0
    updated_at: datetime = datetime.utcnow()

    class Settings:
        name = "user_preferences"

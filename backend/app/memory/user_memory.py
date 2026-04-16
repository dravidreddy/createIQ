"""
UserMemoryStore — Persistent user preference management via MongoDB.

Loads preferences from the UserPreferencesModel Beanie document and
updates them using exponential moving average (EMA) when new signals
arrive from the edit detection engine.
"""

from app.utils.datetime_utils import utc_now
import logging
from datetime import datetime
from typing import Dict

from app.config import get_settings
from app.models.user_preferences import UserPreferencesModel

logger = logging.getLogger(__name__)
settings = get_settings()

# Mapping from signal names to preference fields
_SIGNAL_TO_FIELD = {
    "tone_shift": "tone",
    "length_preference": "preferred_length",
    "complexity_shift": "vocabulary_level",
    "engagement_shift": "engagement_style",
}

# EMA value → label mappings
_TONE_MAP = {-1: "professional", 0: "neutral", 1: "enthusiastic"}
_LENGTH_MAP = {-1: "concise", 0: "mixed", 1: "detailed"}
_VOCAB_MAP = {-1: "simple", 0: "moderate", 1: "advanced"}
_ENGAGE_MAP = {-1: "data-driven", 0: "story-driven", 1: "question-heavy"}

_FIELD_LABEL_MAPS = {
    "tone": _TONE_MAP,
    "preferred_length": _LENGTH_MAP,
    "vocabulary_level": _VOCAB_MAP,
    "engagement_style": _ENGAGE_MAP,
}

_FIELD_TO_NUMERIC = {
    "tone": {"professional": -1, "neutral": 0, "enthusiastic": 1},
    "preferred_length": {"concise": -1, "mixed": 0, "detailed": 1},
    "vocabulary_level": {"simple": -1, "moderate": 0, "advanced": 1},
    "engagement_style": {"data-driven": -1, "story-driven": 0, "question-heavy": 1},
}


def _label_to_numeric(field: str, label: str) -> float:
    """Convert a label to a numeric value for EMA calculation."""
    mapping = _FIELD_TO_NUMERIC.get(field, {})
    return float(mapping.get(label, 0.0))


def _numeric_to_label(field: str, value: float) -> str:
    """Convert a numeric EMA value to the nearest label."""
    label_map = _FIELD_LABEL_MAPS.get(field, {})
    if not label_map:
        return "neutral"
    # Find nearest key
    nearest_key = min(label_map.keys(), key=lambda k: abs(k - value))
    return label_map[nearest_key]


class UserMemoryStore:
    """Manages persistent user preferences in MongoDB."""

    async def load(self, user_id: str) -> Dict:
        """Load user preferences, returning defaults if none exist."""
        doc = await UserPreferencesModel.find_one(
            UserPreferencesModel.user_id == user_id
        )
        if doc is None:
            return {
                "writing_style": "conversational",
                "tone": "enthusiastic",
                "preferred_length": "detailed",
                "vocabulary_level": "moderate",
                "engagement_style": "question-heavy",
                "custom_signals": {},
            }
        return {
            "writing_style": doc.writing_style,
            "tone": doc.tone,
            "preferred_length": doc.preferred_length,
            "vocabulary_level": doc.vocabulary_level,
            "engagement_style": doc.engagement_style,
            "custom_signals": doc.custom_signals,
        }

    async def update_from_signals(self, user_id: str, signals: Dict[str, float]) -> None:
        """Apply EMA to merge new preference signals into existing preferences.

        EMA formula: new_pref = alpha * signal + (1 - alpha) * old_pref
        alpha = settings.preference_learning_rate (default 0.3)
        """
        alpha = settings.preference_learning_rate
        doc = await UserPreferencesModel.find_one(
            UserPreferencesModel.user_id == user_id
        )
        if doc is None:
            doc = UserPreferencesModel(user_id=user_id)

        for signal_name, signal_value in signals.items():
            field_name = _SIGNAL_TO_FIELD.get(signal_name)
            if field_name:
                current_label = getattr(doc, field_name, "neutral")
                current_numeric = _label_to_numeric(field_name, current_label)
                new_numeric = alpha * signal_value + (1 - alpha) * current_numeric
                new_label = _numeric_to_label(field_name, new_numeric)
                setattr(doc, field_name, new_label)
            else:
                # Store as custom signal with EMA
                old_val = doc.custom_signals.get(signal_name, 0.0)
                doc.custom_signals[signal_name] = alpha * signal_value + (1 - alpha) * old_val

        doc.edit_count += 1
        doc.updated_at = utc_now()
        await doc.save()

        logger.info(
            "UserMemoryStore: updated preferences for user %s (edit #%d)",
            user_id, doc.edit_count
        )

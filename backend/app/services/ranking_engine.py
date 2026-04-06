"""
Ranking Engine — Deterministic multi-signal scorer with adaptive weights (MongoDB/Beanie).

Scoring formula:
  total = Σ (w_i × signal_i)   where w is per-user from RankingProfile

All IDs are strings (MongoDB ObjectId).
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from app.config import get_settings
from app.models.ranking_profile import RankingProfile

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Data Structures ────────────────────────────────────────────

@dataclass
class VariantScores:
    """Raw signal scores for a single variant (each 0-1)."""
    variant_id: str
    engagement: float = 0.0
    persona: float = 0.0
    novelty: float = 0.0
    trend: float = 0.0


@dataclass
class RankedVariant:
    """Fully scored variant with explainability."""
    variant_id: str
    total_score: float
    breakdown: Dict[str, float]


# ─── Core API ───────────────────────────────────────────────────

async def load_weights(user_id: str) -> Dict[str, float]:
    """Load per-user ranking weights, falling back to defaults."""
    row: Optional[RankingProfile] = await RankingProfile.find_one(
        RankingProfile.user_id == user_id
    )

    if row is None:
        return {"engagement": 0.40, "persona": 0.30, "novelty": 0.15, "trend": 0.15}

    return {
        "engagement": row.w_engagement,
        "persona": row.w_persona,
        "novelty": row.w_novelty,
        "trend": row.w_trend,
    }


def score_variant(scores: VariantScores, weights: Dict[str, float]) -> RankedVariant:
    """Compute a deterministic weighted score for a variant."""
    breakdown = {
        "engagement": weights["engagement"] * scores.engagement,
        "persona": weights["persona"] * scores.persona,
        "novelty": weights["novelty"] * scores.novelty,
        "trend": weights["trend"] * scores.trend,
    }
    total = sum(breakdown.values())
    return RankedVariant(
        variant_id=scores.variant_id,
        total_score=round(total, 4),
        breakdown={k: round(v, 4) for k, v in breakdown.items()},
    )


def rank_variants(variants: List[VariantScores], weights: Dict[str, float]) -> List[RankedVariant]:
    """Score and sort variants descending by total score."""
    ranked = [score_variant(v, weights) for v in variants]
    ranked.sort(key=lambda r: r.total_score, reverse=True)
    return ranked


def explain_score(ranked: RankedVariant) -> Dict:
    """Return a JSON-serialisable explanation for a ranking decision."""
    return {
        "variant_id": ranked.variant_id,
        "total_score": ranked.total_score,
        "breakdown": ranked.breakdown,
        "dominant_signal": max(ranked.breakdown, key=ranked.breakdown.get),
    }


# ─── Adaptive Weight Updates ────────────────────────────────────

async def micro_update_weights(
    user_id: str,
    chosen_variant: RankedVariant,
    performance_delta: Dict[str, float],
) -> None:
    """Apply a small real-time weight nudge after a user selects a variant."""
    lr = settings.ranking_learning_rate

    row: Optional[RankingProfile] = await RankingProfile.find_one(
        RankingProfile.user_id == user_id
    )

    if row is None:
        row = RankingProfile(user_id=user_id)
        await row.insert()

    row.w_engagement = _clamp(row.w_engagement + lr * performance_delta.get("engagement", 0))
    row.w_persona = _clamp(row.w_persona + lr * performance_delta.get("persona", 0))
    row.w_novelty = _clamp(row.w_novelty + lr * performance_delta.get("novelty", 0))
    row.w_trend = _clamp(row.w_trend + lr * performance_delta.get("trend", 0))

    total = row.w_engagement + row.w_persona + row.w_novelty + row.w_trend
    if total > 0:
        row.w_engagement /= total
        row.w_persona /= total
        row.w_novelty /= total
        row.w_trend /= total

    row.updated_at = datetime.utcnow()
    await row.save()

    logger.info(
        "ranking_engine: micro-updated weights for user %s → eng=%.3f pers=%.3f nov=%.3f trn=%.3f",
        user_id, row.w_engagement, row.w_persona, row.w_novelty, row.w_trend,
    )


def _clamp(value: float, lo: float = 0.05, hi: float = 0.80) -> float:
    """Clamp a weight between floor and ceiling to prevent collapse."""
    return max(lo, min(hi, value))

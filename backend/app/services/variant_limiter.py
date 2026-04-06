"""
Variant Limiter — Enforces tier-based variant caps.

Tier caps (from config):
  free:       2 variants
  pro:        4 variants
  enterprise: 5 variants

Usage:
  trimmed = enforce_tier_limits(variants, user_tier)
"""

import logging
from typing import Any, Dict, List

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_TIER_CAPS = {
    "free": settings.tier_variant_cap_free,
    "pro": settings.tier_variant_cap_pro,
    "enterprise": settings.tier_variant_cap_enterprise,
}


def enforce_tier_limits(
    variants: List[Dict[str, Any]],
    user_tier: str = "free",
) -> List[Dict[str, Any]]:
    """Trim a list of variant dicts to the configured cap for *user_tier*.

    If the tier is unrecognised, defaults to the free cap.
    Returns the first N variants (assumed to be pre-sorted by score).
    """
    cap = _TIER_CAPS.get(user_tier, _TIER_CAPS["free"])
    if len(variants) > cap:
        logger.info(
            "variant_limiter: trimming %d variants to %d (tier=%s)",
            len(variants), cap, user_tier,
        )
    return variants[:cap]


def get_variant_cap(user_tier: str = "free") -> int:
    """Return the maximum number of variants allowed for a tier."""
    return _TIER_CAPS.get(user_tier, _TIER_CAPS["free"])

"""
Niche Config Loader — Hybrid JSON seed → MongoDB runtime.

Provides:
  - load_niche_config(niche) — cached reads from MongoDB
  - seed_niche_configs() — startup seed from JSON files if not in DB
  - list_available_niches() — list all configured niches
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from app.models.niche_config import NicheConfigModel, PlatformHints

logger = logging.getLogger(__name__)

_SEED_DIR = Path(__file__).parent

# In-memory cache (refreshed on startup, TTL-free since niches change rarely)
_cache: Dict[str, NicheConfigModel] = {}


def _load_json_seed(niche_name: str) -> Optional[Dict]:
    """Load a niche config from the JSON seed file."""
    path = _SEED_DIR / f"{niche_name}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _list_seed_files() -> List[str]:
    """List all niche names from seed JSON files (excluding _base)."""
    return [
        p.stem for p in _SEED_DIR.glob("*.json")
        if p.stem != "_base" and not p.stem.startswith("__")
    ]


async def seed_niche_configs() -> int:
    """Seed niche configs from JSON files into MongoDB.

    Only inserts configs that don't already exist in MongoDB.
    Called on app startup.

    Returns:
        Number of newly seeded configs.
    """
    seeded = 0
    seed_names = _list_seed_files() + ["_base"]

    for name in seed_names:
        data = _load_json_seed(name)
        if not data:
            continue

        niche_key = data.get("niche", name)
        existing = await NicheConfigModel.find_one(
            NicheConfigModel.niche == niche_key
        )
        if existing:
            continue

        # Build platform hints
        hints_data = data.get("platform_hints", {})
        platform_hints = PlatformHints(**hints_data) if hints_data else PlatformHints()

        doc = NicheConfigModel(
            niche=niche_key,
            version=data.get("version", "v1"),
            display_name=data.get("display_name", name.title()),
            tone_guidelines=data.get("tone_guidelines", ""),
            vocabulary=data.get("vocabulary", []),
            avoid_vocabulary=data.get("avoid_vocabulary", []),
            content_patterns=data.get("content_patterns", []),
            audience_archetype=data.get("audience_archetype", ""),
            platform_hints=platform_hints,
            engagement_rules=data.get("engagement_rules", []),
            is_custom=False,
        )
        await doc.insert()
        seeded += 1
        logger.info("Seeded niche config: %s", niche_key)

    if seeded:
        logger.info("NAPOS: Seeded %d niche configs into MongoDB", seeded)

    # Warm the cache
    await _warm_cache()

    return seeded


async def _warm_cache() -> None:
    """Load all niche configs from MongoDB into the in-memory cache."""
    global _cache
    all_configs = await NicheConfigModel.find_all().to_list()
    _cache = {c.niche: c for c in all_configs}
    logger.info("NAPOS: Cached %d niche configs in memory", len(_cache))


async def load_niche_config(niche_name: str) -> NicheConfigModel:
    """Load a niche config by name.

    Resolution order:
    1. In-memory cache
    2. MongoDB query
    3. Fallback to '_base' config

    Args:
        niche_name: Niche identifier (e.g. 'fitness', 'tech')

    Returns:
        NicheConfigModel document
    """
    # Normalize niche name
    niche_key = niche_name.lower().strip() if niche_name else "_base"

    # 1. Check cache
    if niche_key in _cache:
        return _cache[niche_key]

    # 2. Check MongoDB
    doc = await NicheConfigModel.find_one(NicheConfigModel.niche == niche_key)
    if doc:
        _cache[niche_key] = doc
        return doc

    # 3. Fallback to _base
    if niche_key != "_base":
        logger.warning("NAPOS: Niche '%s' not found, falling back to _base", niche_key)
        return await load_niche_config("_base")

    # 4. If even _base doesn't exist (first run before seeding), return in-memory default
    logger.warning("NAPOS: _base niche config not found in DB — using hardcoded defaults")
    return NicheConfigModel(
        niche="_base",
        version="v1",
        display_name="General",
        tone_guidelines="Use clear, engaging language. Be informative and approachable.",
        vocabulary=[],
        avoid_vocabulary=[],
        content_patterns=["hook-first", "problem-solution"],
        audience_archetype="General audience",
        platform_hints=PlatformHints(),
        engagement_rules=["Deliver value quickly", "Include a call-to-action"],
    )


async def list_available_niches() -> List[Dict[str, str]]:
    """List all available niche configs with display names.

    Returns:
        List of {"niche": "fitness", "display_name": "Fitness & Health"}
    """
    configs = await NicheConfigModel.find_all().to_list()
    return [
        {"niche": c.niche, "display_name": c.display_name}
        for c in configs
        if c.niche != "_base"
    ]


def invalidate_cache(niche_name: Optional[str] = None) -> None:
    """Invalidate the in-memory cache for a specific niche or all niches."""
    global _cache
    if niche_name:
        _cache.pop(niche_name, None)
    else:
        _cache.clear()

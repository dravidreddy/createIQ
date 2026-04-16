"""
State Service — Compatibility shim for V3.3 routes.

Provides versioned read/write for ProjectAgentState (MongoDB/Beanie).
Retained as a thin module for backward compatibility with V3.3 API routes.
"""

from app.utils.datetime_utils import utc_now
import copy
import json
import logging
from typing import Any, Dict, Optional, Tuple

from app.config import get_settings
from app.models.project_agent_state import ProjectAgentState

logger = logging.getLogger(__name__)
settings = get_settings()


def deep_merge(base: dict, patch: dict) -> dict:
    """Recursively merge *patch* into a **copy** of *base*."""
    result = copy.deepcopy(base)
    for key, value in patch.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _validate_patch(patch: dict) -> None:
    unknown = set(patch.keys()) - ProjectAgentState.ALLOWED_DOMAINS
    if unknown:
        raise ValueError(f"Unknown state domains: {unknown}")


def _check_size(state: dict) -> bool:
    size_bytes = len(json.dumps(state).encode())
    return size_bytes > settings.state_max_size_kb * 1024


async def read_snapshot(project_id: str) -> Tuple[Optional[dict], int]:
    row = await ProjectAgentState.find_one(
        ProjectAgentState.project_id == project_id
    )
    if row is None:
        return None, 0
    return row.state, row.version


async def apply_patch(
    project_id: str,
    base_version: int,
    patch: Dict[str, Any],
) -> Tuple[dict, int]:
    _validate_patch(patch)

    row = await ProjectAgentState.find_one(
        ProjectAgentState.project_id == project_id
    )

    if row is None:
        new_state = deep_merge({}, patch)
        row = ProjectAgentState(
            project_id=project_id,
            version=1,
            state=new_state,
        )
        await row.insert()
        return new_state, 1

    if row.version != base_version:
        raise RuntimeError(
            f"Version conflict: expected {base_version}, found {row.version}"
        )

    new_state = deep_merge(row.state, patch)
    row.state = new_state
    row.version += 1

    from datetime import datetime
    row.updated_at = utc_now()
    await row.save()

    if _check_size(new_state):
        logger.warning(
            "state_service: state for project %s exceeds %d KB",
            project_id, settings.state_max_size_kb,
        )

    return new_state, row.version

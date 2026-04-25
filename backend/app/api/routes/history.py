"""
History Routes — Version history API for project content blocks.

Endpoints:
  GET  /projects/{id}/history              — list versions by block type
  GET  /projects/{id}/history/{version_id} — get specific version content
  GET  /projects/{id}/history/compare      — diff two versions
  POST /projects/{id}/history/{version_id}/restore — restore old version
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.history import BlockHistory, VersionDetail, VersionDiff
from app.services.history import HistoryService

router = APIRouter()


@router.get(
    "/{project_id}/history",
    response_model=List[BlockHistory],
    summary="Get version history for a project",
)
async def get_project_history(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    """List all content versions for a project, grouped by block type."""
    service = HistoryService()
    history = await service.get_project_history(project_id, str(current_user.id))
    return history


@router.get(
    "/{project_id}/history/compare",
    response_model=VersionDiff,
    summary="Compare two versions",
)
async def compare_versions(
    project_id: str,
    v1: str = Query(..., description="First version ID"),
    v2: str = Query(..., description="Second version ID"),
    current_user: User = Depends(get_current_user),
):
    """Generate a diff between two content versions."""
    service = HistoryService()
    diff = await service.compare_versions(
        project_id, v1, v2, str(current_user.id)
    )
    if not diff:
        raise HTTPException(status_code=404, detail="One or both versions not found")
    return diff


@router.get(
    "/{project_id}/history/{version_id}",
    response_model=VersionDetail,
    summary="Get a specific version",
)
async def get_version(
    project_id: str,
    version_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get the full content of a specific version."""
    service = HistoryService()
    version = await service.get_version(
        project_id, version_id, str(current_user.id)
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.post(
    "/{project_id}/history/{version_id}/restore",
    response_model=VersionDetail,
    summary="Restore an old version",
)
async def restore_version(
    project_id: str,
    version_id: str,
    current_user: User = Depends(get_current_user),
):
    """Restore an old version by creating a new version with its content.

    This follows append-only semantics — the old version is not modified,
    a new version is created copying the old content.
    """
    service = HistoryService()
    result = await service.restore_version(
        project_id, version_id, str(current_user.id)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Version not found or unauthorized")
    return result

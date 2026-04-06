"""
Versions Routes (V4)

Manage project content pipeline iterations.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import User
from app.schemas.version import ProjectVersionResponse
from app.services.version import VersionService
from app.api.deps import get_current_user

router = APIRouter()

def _version_to_response(v) -> ProjectVersionResponse:
    return ProjectVersionResponse(
        id=str(v.id),
        project_id=str(v.project_id),
        version_number=v.version_number,
        is_saved=v.is_saved,
        ideas=v.ideas,
        selected_idea=v.selected_idea,
        hook=v.hook,
        script=v.script,
        screenplay_guidance=v.screenplay_guidance,
        expires_at=v.expires_at,
        created_at=v.created_at,
        updated_at=v.updated_at
    )

@router.get("/{project_id}/versions", response_model=List[ProjectVersionResponse])
async def get_project_versions(project_id: str, current_user: User = Depends(get_current_user)):
    service = VersionService()
    versions = await service.get_versions(project_id, str(current_user.id))
    return [_version_to_response(v) for v in versions]

@router.post("/versions/{version_id}/save", response_model=ProjectVersionResponse)
async def save_version(version_id: str, current_user: User = Depends(get_current_user)):
    service = VersionService()
    version = await service.save_version(version_id, str(current_user.id))
    if not version:
        raise HTTPException(status_code=404, detail="Version not found or unauthorised")
    return _version_to_response(version)

"""
Project Routes (V4)

Project management and collaborator endpoints.
"""

from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path

from app.models.user import User
from app.models.project import ProjectStatus, CollaboratorRole, Project
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectList,
    CollaboratorCreate,
    CollaboratorResponse
)
from app.services.project import ProjectService
from app.api.deps import get_current_user
from app.api.middleware_rbac import verify_project_editor, verify_project_owner
from app.schemas.base import CreatorResponse, wrap_response

router = APIRouter()

def _project_to_response(project) -> ProjectResponse:
    collaborators = [
        CollaboratorResponse(user_id=c.user_id, role=c.role, added_at=c.added_at)
        for c in project.collaborators
    ]
    return ProjectResponse(
        id=str(project.id),
        user_id=project.user_id,
        title=project.title,
        topic=project.topic,
        niche=project.niche,
        status=project.status,
        parent_project_id=str(project.parent_project_id) if project.parent_project_id else None,
        strategy_plan_id=str(project.strategy_plan_id) if project.strategy_plan_id else None,
        platform=project.platform,
        goal=project.goal,
        collaborators=collaborators,
        current_agent=project.current_agent,
        error_message=project.error_message,
        created_at=project.created_at,
        updated_at=project.updated_at,
        completed_at=project.completed_at,
        completed_stages=getattr(project, 'completed_stages', []),
    )

@router.post("", response_model=CreatorResponse[ProjectResponse], status_code=status.HTTP_201_CREATED)
async def create_project(project_data: ProjectCreate, current_user: User = Depends(get_current_user)):
    project_service = ProjectService()
    project = await project_service.create_project(str(current_user.id), project_data)
    return wrap_response(_project_to_response(project))

@router.get("", response_model=CreatorResponse[ProjectList])
async def list_projects(page: int = Query(1, ge=1), per_page: int = Query(10, ge=1, le=100), status_filter: Optional[ProjectStatus] = Query(None, alias="status"), current_user: User = Depends(get_current_user)):
    project_service = ProjectService()
    projects, total = await project_service.get_projects(str(current_user.id), page=page, per_page=per_page, status=status_filter)
    return wrap_response(ProjectList(projects=[_project_to_response(p) for p in projects], total=total, page=page, per_page=per_page))

@router.get("/{project_id}", response_model=CreatorResponse[ProjectResponse])
async def get_project(project_id: str, current_user: User = Depends(get_current_user)):
    project_service = ProjectService()
    project = await project_service.get_project(project_id, str(current_user.id))
    if not project: raise HTTPException(status_code=404, detail="Project not found")
    return wrap_response(_project_to_response(project))

@router.put("/{project_id}", response_model=CreatorResponse[ProjectResponse])
async def update_project(project_data: ProjectUpdate, project_id: str = Path(...), project: Project = Depends(verify_project_editor), current_user: User = Depends(get_current_user)):
    project_service = ProjectService()
    project = await project_service.update_project(project_id, str(current_user.id), project_data)
    if not project: raise HTTPException(status_code=404, detail="Project not found")
    return wrap_response(_project_to_response(project))

@router.delete("/{project_id}", response_model=CreatorResponse[dict[str, str]])
async def delete_project(project_id: str = Path(...), project: Project = Depends(verify_project_owner), current_user: User = Depends(get_current_user)):
    project_service = ProjectService()
    deleted = await project_service.delete_project(project_id, str(current_user.id))
    if not deleted: raise HTTPException(status_code=404, detail="Project not found or unauthorised")
    return wrap_response({"message": "Project deleted successfully"})

@router.post("/{project_id}/collaborators", response_model=CreatorResponse[ProjectResponse])
async def add_collaborator(payload: CollaboratorCreate, project_id: str = Path(...), project: Project = Depends(verify_project_owner), current_user: User = Depends(get_current_user)):
    project_service = ProjectService()
    project = await project_service.add_collaborator(project_id, str(current_user.id), payload.user_id, payload.role)
    if not project: raise HTTPException(status_code=404, detail="Project not found or unauthorised")
    return wrap_response(_project_to_response(project))

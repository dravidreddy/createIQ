from fastapi import Depends, HTTPException, Path, status
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import CollaboratorRole, Project
from app.services.project import ProjectService

async def verify_project_editor(
    project_id: str = Path(...),
    current_user: User = Depends(get_current_user),
) -> Project:
    """
    Middleware dependency verifying the authenticated user has OWNER or EDITOR
    privileges on the target Project before allowing destructive mutations.
    """
    project_service = ProjectService()
    project = await project_service.get_project(project_id, str(current_user.id))
    
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found or unauthorised")

    # Authorise explicit owner
    if project.user_id == str(current_user.id):
        return project

    # Authorise collaborative editor
    for collab in project.collaborators:
        if collab.user_id == str(current_user.id):
            if collab.role in [CollaboratorRole.OWNER, CollaboratorRole.EDITOR]:
                return project
                
    # Reject viewers
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorised. Must be an OWNER or EDITOR to mutate this project.")

async def verify_project_owner(
    project_id: str = Path(...),
    current_user: User = Depends(get_current_user),
) -> Project:
    """
    Middleware dependency verifying the authenticated user has OWNER
    privileges before allowing supreme mutations like deletion or inviting.
    """
    project_service = ProjectService()
    project = await project_service.get_project(project_id, str(current_user.id))
    
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found or unauthorised")

    if project.user_id == str(current_user.id):
        return project
        
    for collab in project.collaborators:
        if collab.user_id == str(current_user.id) and collab.role == CollaboratorRole.OWNER:
            return project
            
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorised. Must be an OWNER. Editors cannot perform this action.")

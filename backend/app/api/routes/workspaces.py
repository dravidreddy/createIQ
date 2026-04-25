"""
Workspace Routes — Multi-tenant team management
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_current_workspace
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceTier

router = APIRouter()


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    tier: str
    role: str


class InviteMemberRequest(BaseModel):
    email: str
    role: str = Field(default="editor", pattern="^(admin|editor|viewer)$")


@router.get(
    "/",
    response_model=List[WorkspaceResponse],
    summary="List user's workspaces",
)
async def list_workspaces(current_user: User = Depends(get_current_user)):
    """Get all workspaces the current user is a member of."""
    workspaces = await Workspace.find({"members.user_id": str(current_user.id)}).to_list()
    
    result = []
    for ws in workspaces:
        # Find user's role in this workspace
        role = "viewer"
        for member in ws.members:
            if member.user_id == str(current_user.id):
                role = member.role
                break
                
        result.append(
            WorkspaceResponse(
                id=str(ws.id),
                name=ws.name,
                tier=ws.tier.value,
                role=role
            )
        )
        
    return result


@router.post(
    "/{workspace_id}/invite",
    summary="Invite user to workspace",
)
async def invite_user(
    workspace_id: str,
    body: InviteMemberRequest,
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    """Invite a user to the workspace by email."""
    # Enforce RBAC: Only owner or admin can invite
    is_admin = any(
        m.user_id == str(current_user.id) and m.role in ["owner", "admin"]
        for m in current_workspace.members
    )
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace admins can invite new members."
        )
        
    # Lookup target user by email
    target_user = await User.find_one(User.email == body.email)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. They must sign up first."
        )
        
    # Check if already a member
    if any(m.user_id == str(target_user.id) for m in current_workspace.members):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this workspace."
        )
        
    # Enforce tier limits (mocked logic)
    if current_workspace.tier == WorkspaceTier.FREE and len(current_workspace.members) >= 1:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Free tier allows only 1 member. Please upgrade to the Agency plan."
        )
        
    # Add member
    current_workspace.members.append(
        WorkspaceMember(user_id=str(target_user.id), role=body.role)
    )
    await current_workspace.save()
    
    return {"status": "success", "message": f"Invited {body.email} as {body.role}"}

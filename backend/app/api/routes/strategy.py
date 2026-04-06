"""
Strategy Routes (V4)

Manage series and growth plans.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import User
from app.schemas.strategy import StrategyPlanCreate, StrategyPlanResponse, StrategyPlanInstantiateRequest
from app.schemas.project import ProjectResponse
from app.services.strategy import StrategyService
from app.api.deps import get_current_user
from app.api.routes.projects import _project_to_response

router = APIRouter()

def _strategy_to_response(s) -> StrategyPlanResponse:
    return StrategyPlanResponse(
        id=str(s.id),
        user_id=str(s.user_id),
        title=s.title,
        focus_niche=s.focus_niche,
        series_plan=s.series_plan,
        created_at=s.created_at,
        updated_at=s.updated_at
    )

@router.post("", response_model=StrategyPlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_strategy_plan(plan_data: StrategyPlanCreate, current_user: User = Depends(get_current_user)):
    service = StrategyService()
    plan = await service.generate_plan(str(current_user.id), plan_data)
    return _strategy_to_response(plan)

@router.get("/{plan_id}", response_model=StrategyPlanResponse)
async def get_strategy_plan(plan_id: str, current_user: User = Depends(get_current_user)):
    service = StrategyService()
    plan = await service.get_plan(plan_id, str(current_user.id))
    if not plan: raise HTTPException(status_code=404, detail="Strategy Plan not found")
    return _strategy_to_response(plan)

@router.post("/{plan_id}/instantiate", response_model=List[ProjectResponse])
async def instantiate_strategy(
    plan_id: str,
    parent_project_id: str,
    payload: StrategyPlanInstantiateRequest,
    current_user: User = Depends(get_current_user)
):
    service = StrategyService()
    projects = await service.instantiate_sub_projects(
        plan_id=plan_id,
        user_id=str(current_user.id),
        parent_project_id=parent_project_id,
        indices=payload.series_indices
    )
    return [_project_to_response(p) for p in projects]

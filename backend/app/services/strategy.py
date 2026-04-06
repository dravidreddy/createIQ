"""
Strategy Service (V4)

Engine for generating series and growth plans.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import PydanticObjectId
from app.models.strategy import StrategyPlan
from app.schemas.strategy import StrategyPlanCreate
from app.services.project import ProjectService
from app.schemas.project import ProjectCreate
from app.llm.base import LLMMessage
from app.llm.router import get_llm_router
import json
import logging

logger = logging.getLogger(__name__)

class StrategyService:
    def __init__(self):
        self.project_service = ProjectService()
        self.llm = get_llm_router()

    async def generate_plan(self, user_id: str, plan_data: StrategyPlanCreate) -> StrategyPlan:
        # LLM prompt to generate a series plan
        prompt = f"""You are a top-tier digital strategist. Create a highly engaging 5-part content series plan for the niche: "{plan_data.focus_niche}".
The series title is: "{plan_data.title}".

For each part in the series, provide:
- "title": A compelling title
- "topic": The core subject matter
- "hook_idea": A high-level hook concept
- "goal": The goal of the piece (e.g., Engagement, Education, Conversion)

Return ONLY a valid JSON object matching this structure:
{{
  "series_plan": [
    {{"title": "...", "topic": "...", "hook_idea": "...", "goal": "..."}}
  ]
}}
"""
        try:
            messages = [LLMMessage(role="user", content=prompt)]
            response = await self.llm.generate(messages, task_type="quality", temperature=0.7)
            
            # Parse JSON
            text = response.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            
            data = json.loads(text)
            series_plan = data.get("series_plan", [])
        except Exception as e:
            logger.error(f"Strategy engine failed to parse LLM response: {e}")
            series_plan = []

        plan = StrategyPlan(
            user_id=user_id,
            title=plan_data.title,
            focus_niche=plan_data.focus_niche,
            series_plan=series_plan
        )
        await plan.insert()
        return plan

    async def get_plan(self, plan_id: str, user_id: str) -> Optional[StrategyPlan]:
        try:
            plan = await StrategyPlan.get(PydanticObjectId(plan_id))
        except Exception:
            return None
            
        if plan and plan.user_id != user_id: return None
        return plan

    async def instantiate_sub_projects(self, plan_id: str, user_id: str, parent_project_id: str, indices: List[int] = None):
        plan = await self.get_plan(plan_id, user_id)
        if not plan or not plan.series_plan: return []
        
        created_projects = []
        for i, item in enumerate(plan.series_plan):
            if indices is not None and i not in indices: continue
                
            project_data = ProjectCreate(
                title=item.get("title", f"Part {i+1}"),
                topic=item.get("topic", "Unknown"),
                parent_project_id=parent_project_id,
                strategy_plan_id=plan_id,
                goal=item.get("goal")
            )
            p = await self.project_service.create_project(user_id, project_data)
            created_projects.append(p)
            
        return created_projects

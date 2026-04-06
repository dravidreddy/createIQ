"""
Agent Routes (V4 — Legacy Compatibility)

Individual agent execution endpoints for backward compatibility.
The primary interface is now the pipeline routes (/api/v1/pipeline/*).
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
import logging

logger = logging.getLogger(__name__)

from app.models.user import User
from app.models.project import ProjectStatus
from app.services.project import ProjectService
from app.services.version import VersionService
from app.services.user import UserService
from app.agents.sub_agents.trend_researcher import TrendResearcherAgent
from app.agents.sub_agents.idea_generator import IdeaGeneratorAgent
from app.agents.sub_agents.hook_creator import HookCreatorAgent
from app.agents.sub_agents.script_drafter import ScriptDrafterAgent
from app.agents.sub_agents.deep_researcher import DeepResearcherAgent
from app.api.deps import get_current_user
from app.schemas.base import CreatorResponse, wrap_response

router = APIRouter()

async def get_user_context(user_id: str):
    user_service = UserService()
    return await user_service.get_profile_context(user_id)

@router.post("/{project_id}/discover-ideas")
async def discover_ideas(project_id: str, current_user: User = Depends(get_current_user)):
    project_service = ProjectService()
    version_service = VersionService()

    project = await project_service.get_project(project_id, str(current_user.id))
    if not project: raise HTTPException(status_code=404, detail="Project not found")

    user_context = await get_user_context(str(current_user.id))
    await project_service.update_project_status(project_id, ProjectStatus.IDEA_DISCOVERY, current_agent="idea_discovery")

    try:
        # Stage 1: Trend Research → Idea Generation
        researcher = TrendResearcherAgent(user_context=user_context)
        research = await researcher.execute({
            "topic": project.topic,
            "niche": getattr(project, "niche", "general"),
            "platforms": getattr(project, "platforms", ["YouTube"]),
        })

        generator = IdeaGeneratorAgent(user_context=user_context)
        ideas_result = await generator.execute({
            "research_results": research.get("research_results", []),
            "project_context": {"topic": project.topic},
        })

        ideas = ideas_result.get("ideas", [])

        # Save to a new version block
        version = await version_service.create_version(project_id, str(current_user.id), is_saved=False, pipeline_data={"ideas": ideas})

        return wrap_response({
            "project_id": project_id,
            "version_id": str(version.id),
            "ideas": ideas,
        })

    except Exception as e:
        await project_service.update_project_status(project_id, ProjectStatus.FAILED, error_message=str(e))
        raise HTTPException(status_code=500, detail=f"Idea discovery failed: {e}")

@router.post("/{project_id}/generate-hooks")
async def generate_hooks(project_id: str, idea_index: int = Query(...), current_user: User = Depends(get_current_user)):
    project_service = ProjectService()
    version_service = VersionService()

    project = await project_service.get_project(project_id, str(current_user.id))
    if not project: raise HTTPException(status_code=404, detail="Project not found")

    # Get latest version to find ideas
    versions = await version_service.get_versions(project_id, str(current_user.id))
    if not versions or not versions[0].ideas:
        raise HTTPException(status_code=400, detail="No ideas found in project versions.")

    selected_idea = versions[0].ideas[idea_index]

    user_context = await get_user_context(str(current_user.id))

    try:
        agent = HookCreatorAgent(user_context=user_context)
        result = await agent.execute({"selected_idea": selected_idea})

        # Branch a new version from the Idea
        version = await version_service.create_version(
            project_id,
            str(current_user.id),
            is_saved=False,
            pipeline_data={"ideas": versions[0].ideas, "selected_idea": selected_idea, "hook": result.get("hooks")}
        )

        return wrap_response({
            "project_id": project_id,
            "version_id": str(version.id),
            "hooks": result.get("hooks", []),
        })

    except Exception as e:
        await project_service.update_project_status(project_id, ProjectStatus.FAILED, error_message=str(e))
        raise HTTPException(status_code=500, detail=f"Hook generation failed: {e}")

@router.post("/{project_id}/generate-script")
async def generate_script(project_id: str, hook_index: int = Query(...), current_user: User = Depends(get_current_user)):
    project_service = ProjectService()
    version_service = VersionService()

    project = await project_service.get_project(project_id, str(current_user.id))
    if not project: raise HTTPException(status_code=404, detail="Project not found")

    versions = await version_service.get_versions(project_id, str(current_user.id))
    if not versions or not versions[0].selected_idea or not versions[0].hook:
        raise HTTPException(status_code=400, detail="Missing idea or hooks in current version.")

    selected_hook = versions[0].hook[hook_index] if isinstance(versions[0].hook, list) else versions[0].hook
    selected_idea = versions[0].selected_idea

    user_context = await get_user_context(str(current_user.id))
    await project_service.update_project_status(project_id, ProjectStatus.RESEARCHING, current_agent="research_script")

    try:
        # Deep Research + Script Drafting
        researcher = DeepResearcherAgent(user_context=user_context)
        research = await researcher.execute({
            "selected_idea": selected_idea,
            "selected_hook": selected_hook if isinstance(selected_hook, dict) else {"text": str(selected_hook)},
        })

        drafter = ScriptDrafterAgent(user_context=user_context)
        result = await drafter.execute({
            "selected_idea": selected_idea,
            "selected_hook": selected_hook if isinstance(selected_hook, dict) else {"text": str(selected_hook)},
            "research": research.get("research", []),
            "project_context": {"topic": selected_idea.get("title", "")},
        })

        script_data = result

        version = await version_service.create_version(
            project_id,
            str(current_user.id),
            is_saved=False,
            pipeline_data={
                "ideas": versions[0].ideas,
                "selected_idea": selected_idea,
                "hook": selected_hook,
                "script": script_data.get("full_script")
            }
        )

        return wrap_response({"project_id": project_id, "version_id": str(version.id), "script": script_data})

    except Exception as e:
        await project_service.update_project_status(project_id, ProjectStatus.FAILED, error_message=str(e))
        raise HTTPException(status_code=500, detail=f"Script generation failed: {e}")

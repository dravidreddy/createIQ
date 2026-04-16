"""
Shadow Execution — Pre-computes script drafts in the background.

This module provides the logic to start generating a script draft while
the user is still reviewing and selecting a hook.
"""

from app.utils.datetime_utils import utc_now
import logging
from typing import Any, Dict
from app.agents.sub_agents.deep_researcher import DeepResearcherAgent
from app.agents.sub_agents.script_drafter import ScriptDrafterAgent
from app.memory.service import MemoryService

logger = logging.getLogger(__name__)

async def trigger_shadow_script_generation(state: Dict[str, Any], config: Dict[str, Any]) -> None:
    """
    Background task to pre-generate a script for the top-ranked hook.
    """
    project_id = state.get("project_id")
    hooks = state.get("hooks", [])
    if not hooks or not project_id:
        return

    # Pick the top hook
    top_hook = hooks[0]
    hook_text = top_hook.get("text", "")
    
    logger.info(f"ShadowExecution: Starting background script generation for project {project_id}")
    
    try:
        memory = MemoryService()
        project_ctx = state.get("project_context", {})
        user_prefs = state.get("user_preferences", {})
        
        # 1. Deep Research (Shadow)
        researcher = DeepResearcherAgent(user_context=project_ctx)
        research = await researcher.execute({
            "selected_idea": state.get("selected_idea", {}),
            "selected_hook": top_hook,
        })
        
        # 2. Script Drafting (Shadow)
        drafter = ScriptDrafterAgent(user_context=project_ctx)
        script = await drafter.execute({
            "selected_idea": state.get("selected_idea", {}),
            "selected_hook": top_hook,
            "research": research.get("research", []),
            "user_preferences": user_prefs,
            "project_context": project_ctx,
        })
        
        # 3. Store as shadow artifact
        # We include the hook_text to ensure we only use it if the user actually picks this hook
        shadow_data = {
            "hook_text": hook_text,
            "script": script,
            "research": research.get("research", []),
            "timestamp": _timestamp()
        }
        
        await memory.save_project_artifact(
            project_id,
            state.get("thread_id", ""),
            "shadow_script",
            shadow_data,
            user_id=state.get("user_id", ""),
        )
        logger.info(f"ShadowExecution: Successfully saved shadow script for hook: {hook_text[:30]}...")
        
    except Exception as e:
        logger.error(f"ShadowExecution: Failed — {e}")

def _timestamp() -> str:
    from datetime import datetime
    return utc_now().isoformat() + "Z"

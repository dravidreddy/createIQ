"""
Script Writing Group — Stage 3 LangGraph node.

Orchestrates: DeepResearcher → ScriptDrafter → FactChecker
"""

import logging
from typing import Any, Dict

from app.agents.sub_agents.deep_researcher import DeepResearcherAgent
from app.agents.sub_agents.script_drafter import ScriptDrafterAgent
from app.agents.sub_agents.fact_checker import FactCheckerAgent
from app.memory.service import MemoryService
from app.llm.base import ErrorCode

logger = logging.getLogger(__name__)


async def deep_research_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sub-node: Deep Research for script."""
    memory = MemoryService()
    project_ctx = state.get("project_context") or {}
    selected_idea = state.get("selected_idea") or {}
    selected_hook = state.get("selected_hook") or {}

    trace = state.get("execution_trace", [])
    trace.append("node_started:script_deep_research")

    # Check for Shadow Cache Hit
    current_hook_text = selected_hook.get("text", "")
    try:
        shadow_artifact = await memory.get_project_artifact(state.get("project_id", ""), "shadow_script")
        if shadow_artifact and shadow_artifact.get("hook_text") == current_hook_text:
            logger.info("ShadowExecution: Cache HIT — Using pre-generated research/script")
            trace.append("node_cache_hit:script_deep_research")
            return {
                "script": shadow_artifact.get("script", {}),
                "research_results": shadow_artifact.get("research", []),
                "shadow_hit": True,
                "current_stage": "script_deep_research",
                "execution_trace": trace
            }
    except Exception as shadow_e:
        logger.debug(f"ShadowExecution Check failed: {shadow_e}")

    researcher = DeepResearcherAgent(user_context=project_ctx)
    research = await researcher.execute({
        "selected_idea": selected_idea,
        "selected_hook": selected_hook,
        "execution_trace": trace
    })

    results = research.get("research", [])
    if not results:
        trace.append("node_warning:script_deep_research:empty_results")
    else:
        trace.append("node_success:script_deep_research")

    return {
        "script_research_results": results,
        "total_cost_cents": state.get("total_cost_cents", 0) + researcher.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + researcher.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + researcher.token_usage.get("output", 0),
        },
        "current_stage": "script_deep_research",
        "shadow_hit": False,
        "execution_trace": trace,
        "last_model_used": researcher.last_model_used
    }


async def script_drafting_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sub-node: Script Drafting."""
    trace = state.get("execution_trace", [])
    trace.append("node_started:script_drafting")
    
    if state.get("shadow_hit"):
        trace.append("node_skipped:script_drafting:shadow_hit")
        return {"current_stage": "script_drafting", "execution_trace": trace}

    project_ctx = state.get("project_context") or {}
    user_prefs = state.get("user_preferences") or {}
    selected_idea = state.get("selected_idea") or {}
    selected_hook = state.get("selected_hook") or {}
    research = state.get("script_research_results") or []

    drafter = ScriptDrafterAgent(user_context=project_ctx)
    script = await drafter.execute({
        "selected_idea": selected_idea,
        "selected_hook": selected_hook,
        "research": research,
        "user_preferences": user_prefs,
        "project_context": project_ctx,
        "execution_trace": trace
    })

    if not script or not script.get("full_script"):
        trace.append("node_failed:script_drafting:critical")
        return {
            "status": "failed",
            "error_code": ErrorCode.CRITICAL_NODE_FAILURE,
            "execution_trace": trace,
            "current_stage": "script_drafting"
        }

    trace.append("node_success:script_drafting")
    return {
        "raw_script": script,
        "total_cost_cents": state.get("total_cost_cents", 0) + drafter.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + drafter.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + drafter.token_usage.get("output", 0),
        },
        "current_stage": "script_drafting",
        "execution_trace": trace,
        "last_model_used": drafter.last_model_used
    }


async def fact_checking_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sub-node: Fact Checking."""
    project_ctx = state.get("project_context") or {}
    script = state.get("raw_script") or state.get("script") or {}
    memory = MemoryService()

    checker = FactCheckerAgent(user_context=project_ctx)
    checked = await checker.execute({
        "script": script,
    })

    # Merge fact-checked script
    final_script = checked.get("corrected_script") or script.get("full_script", "")
    script["full_script"] = final_script
    script["verified_claims"] = checked.get("verified_claims", [])
    script["unverified_claims"] = checked.get("unverified_claims", [])

    try:
        await memory.save_project_artifact(
            state.get("project_id", ""),
            state.get("thread_id", ""),
            "script",
            script
        )
    except Exception as e:
        logger.warning("fact_checking_node: failed to save artifacts — %s", e)

    return {
        "script": script,
        "total_cost_cents": state.get("total_cost_cents", 0) + checker.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + checker.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + checker.token_usage.get("output", 0),
        },
        "current_stage": "fact_checking",
        "completed_stages": state.get("completed_stages", []) + ["script_writing"],
    }

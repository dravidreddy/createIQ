"""
Editing Group — Stage 5 LangGraph node.

Orchestrates: LineEditor → EngagementBooster → FinalReviewer
"""

import logging
from typing import Any, Dict

from app.agents.sub_agents.line_editor import LineEditorAgent
from app.agents.sub_agents.engagement_booster import EngagementBoosterAgent
from app.agents.sub_agents.final_reviewer import FinalReviewerAgent
from app.memory.service import MemoryService
from app.llm.base import ErrorCode

logger = logging.getLogger(__name__)


async def line_editing_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sub-node: Line Editing."""
    ctx = state.get("project_context")
    user_prefs = state.get("user_preferences") or {}
    script = state.get("script") or {}
    structure_guidance = state.get("structure_guidance") or {}

    trace = state.get("execution_trace", [])
    trace.append("node_started:line_editing")

    editor = LineEditorAgent(user_context=ctx)
    edited = await editor.execute({
        "script": script,
        "structure_guidance": structure_guidance,
        "user_preferences": user_prefs,
        "execution_trace": trace
    })

    if not edited:
        trace.append("node_warning:line_editing:empty_results")
    else:
        trace.append("node_success:line_editing")

    return {
        "line_edited_script": edited.get("edited_script", ""),
        "line_edits": edited.get("edits", []),
        "total_cost_cents": state.get("total_cost_cents", 0) + editor.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + editor.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + editor.token_usage.get("output", 0),
        },
        "current_stage": "line_editing",
        "execution_trace": trace,
        "last_model_used": editor.last_model_used
    }


async def engagement_boosting_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sub-node: Engagement Boosting."""
    ctx = state.get("project_context")
    line_edited = state.get("line_edited_script") or ""

    trace = state.get("execution_trace", [])
    trace.append("node_started:engagement_boosting")

    booster = EngagementBoosterAgent(user_context=ctx)
    boosted = await booster.execute({
        "edited_script": line_edited,
        "execution_trace": trace
    })

    enhanced = boosted.get("enhanced_script") or line_edited
    
    if not boosted:
        trace.append("node_warning:engagement_boosting:empty_results")
    else:
        trace.append("node_success:engagement_boosting")

    return {
        "enhanced_script": enhanced,
        "boosters_added": boosted.get("boosters_added", []),
        "total_cost_cents": state.get("total_cost_cents", 0) + booster.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + booster.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + booster.token_usage.get("output", 0),
        },
        "current_stage": "engagement_boosting",
        "execution_trace": trace,
        "last_model_used": booster.last_model_used
    }


async def final_review_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sub-node: Final Review."""
    ctx = state.get("project_context")
    user_prefs = state.get("user_preferences") or {}
    enhanced_script = state.get("enhanced_script") or ""
    memory = MemoryService()

    trace = state.get("execution_trace", [])
    trace.append("node_started:final_review")

    reviewer = FinalReviewerAgent(user_context=ctx)
    reviewed = await reviewer.execute({
        "enhanced_script": enhanced_script,
        "user_preferences": user_prefs,
        "execution_trace": trace
    })

    edited_script = {
        "edits": state.get("line_edits", []),
        "boosters_added": state.get("boosters_added", []),
        "quality_score": reviewed.get("quality_score", 0.7),
        "improvement_summary": reviewed.get("improvement_summary", ""),
        "final_script": reviewed.get("final_script", ""),
    }

    if not reviewed:
        trace.append("node_warning:final_review:empty_results")
    else:
        trace.append("node_success:final_review")

    try:
        await memory.save_project_artifact(
            state.get("project_id", ""),
            state.get("thread_id", ""),
            "final_script",
            edited_script
        )
    except Exception as e:
        logger.warning("final_review_node: failed to save artifacts — %s", e)

    return {
        "edited_script": edited_script,
        "total_cost_cents": state.get("total_cost_cents", 0) + reviewer.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + reviewer.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + reviewer.token_usage.get("output", 0),
        },
        "current_stage": "final_review",
        "completed_stages": state.get("completed_stages", []) + ["editing"],
        "execution_trace": trace,
        "last_model_used": reviewer.last_model_used
    }

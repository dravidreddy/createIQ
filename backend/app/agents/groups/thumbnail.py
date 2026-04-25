"""
Thumbnail Group — Post-pipeline thumbnail brief generation node.

Runs after save_results to auto-generate a thumbnail concept brief.
Non-critical: if it fails, the pipeline still succeeds.
"""

import logging
from typing import Any, Dict

from app.agents.sub_agents.thumbnail_brief import ThumbnailBriefAgent
from app.agents.context import build_agent_context

logger = logging.getLogger(__name__)


async def thumbnail_brief_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a thumbnail concept brief from the completed script."""
    trace = state.get("execution_trace", [])
    trace.append("node_started:thumbnail_brief")

    agent_ctx = build_agent_context(state)
    agent = ThumbnailBriefAgent(user_context=agent_ctx)

    # Extract script and hook content
    script_obj = state.get("edited_script") or state.get("script") or {}
    if isinstance(script_obj, dict):
        script_text = script_obj.get("full_script", str(script_obj))
    else:
        script_text = str(script_obj)

    hook_obj = state.get("selected_hook") or {}
    if isinstance(hook_obj, dict):
        hook_text = hook_obj.get("hook_text", str(hook_obj))
    else:
        hook_text = str(hook_obj)

    topic = state.get("project_context", {}).get("topic", "")

    try:
        result = await agent.execute({
            "script": script_text,
            "hook": hook_text,
            "topic": topic,
        })
        # Remove internal metadata
        result.pop("_meta", None)

        trace.append("node_success:thumbnail_brief")
        return {
            "thumbnail_brief": result,
            "current_stage": "thumbnail_brief",
            "total_cost_cents": state.get("total_cost_cents", 0) + agent.get_cost_cents(),
            "total_tokens": {
                "input": state.get("total_tokens", {}).get("input", 0) + agent.token_usage.get("input", 0),
                "output": state.get("total_tokens", {}).get("output", 0) + agent.token_usage.get("output", 0),
            },
            "execution_trace": trace,
            "last_model_used": agent.last_model_used,
        }
    except Exception as e:
        logger.warning("thumbnail_brief_node: failed (non-fatal) — %s", e)
        trace.append(f"node_warning:thumbnail_brief:{e}")
        return {
            "thumbnail_brief": None,
            "current_stage": "thumbnail_brief",
            "execution_trace": trace,
        }

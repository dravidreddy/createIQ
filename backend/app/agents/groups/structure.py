"""
Structure Group — Stage 4 LangGraph node.

Orchestrates: StructureAnalyzer → PacingOptimizer
"""

import logging
from typing import Any, Dict

from app.agents.sub_agents.structure_analyzer import StructureAnalyzerAgent
from app.agents.sub_agents.pacing_optimizer import PacingOptimizerAgent
from app.llm.base import ErrorCode

logger = logging.getLogger(__name__)


async def structure_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sub-node: Structure Analysis."""
    ctx = state.get("project_context")
    project_ctx = state.get("project_context") or {}
    script = state.get("script") or {}

    trace = state.get("execution_trace", [])
    trace.append("node_started:structure_analysis")

    analyzer = StructureAnalyzerAgent(user_context=ctx)
    analysis = await analyzer.execute({
        "script": script,
        "platforms": project_ctx.get("platforms", ["YouTube"]),
        "video_length": project_ctx.get("video_length", "Medium (1-10 min)"),
        "execution_trace": trace
    })

    if not analysis:
        trace.append("node_warning:structure_analysis:empty_results")
    else:
        trace.append("node_success:structure_analysis")

    return {
        "structure_analysis": analysis,
        "total_cost_cents": state.get("total_cost_cents", 0) + analyzer.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + analyzer.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + analyzer.token_usage.get("output", 0),
        },
        "current_stage": "structure_analysis",
        "execution_trace": trace,
        "last_model_used": analyzer.last_model_used
    }


async def pacing_optimization_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sub-node: Pacing Optimization."""
    ctx = state.get("project_context")
    user_prefs = state.get("user_preferences") or {}
    script = state.get("script") or {}
    analysis = state.get("structure_analysis") or {}

    trace = state.get("execution_trace", [])
    trace.append("node_started:pacing_optimization")

    optimizer = PacingOptimizerAgent(user_context=ctx)
    pacing = await optimizer.execute({
        "script": script,
        "structure_analysis": analysis,
        "user_preferences": user_prefs,
        "execution_trace": trace
    })

    structure_guidance = {
        **analysis,
        "pacing_adjustments": pacing.get("pacing_adjustments", []),
        "retention_hooks_to_add": pacing.get("retention_hooks_to_add", []),
        "restructured_script": pacing.get("restructured_script", ""),
    }

    if not pacing:
        trace.append("node_warning:pacing_optimization:empty_results")
    else:
        trace.append("node_success:pacing_optimization")

    return {
        "structure_guidance": structure_guidance,
        "total_cost_cents": state.get("total_cost_cents", 0) + optimizer.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + optimizer.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + optimizer.token_usage.get("output", 0),
        },
        "current_stage": "pacing_optimization",
        "completed_stages": state.get("completed_stages", []) + ["structure"],
        "execution_trace": trace,
        "last_model_used": optimizer.last_model_used
    }

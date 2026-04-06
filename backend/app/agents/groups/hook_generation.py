"""
Hook Generation Group — Stage 2 LangGraph node.

Orchestrates: HookCreator → HookEvaluator
"""

import logging
from typing import Any, Dict

from app.agents.sub_agents.hook_creator import HookCreatorAgent
from app.agents.sub_agents.hook_evaluator import HookEvaluatorAgent
from app.memory.service import MemoryService
from app.llm.base import ErrorCode

logger = logging.getLogger(__name__)


import asyncio
import time
from typing import Any, Dict, List

async def hook_creation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sub-node: Hook Creation (with Parallel Execution)."""
    project_ctx = state.get("project_context") or {}
    user_prefs = state.get("user_preferences") or {}
    selected_idea = state.get("selected_idea") or {}
    
    if not selected_idea and state.get("ideas"):
        selected_idea = state["ideas"][0]

    trace = state.get("execution_trace", [])
    trace.append("node_started:hook_creation")
    
    # Parallelize generation: Curiosity vs Contrarian vs Story Loop
    frameworks = ["curiosity_gap", "contrarian", "story_loop"]
    
    async def generate_variation(framework: str):
        creator = HookCreatorAgent(user_context=project_ctx)
        res = await creator.execute({
            "selected_idea": selected_idea,
            "user_preferences": user_prefs,
            "framework": framework,
            "execution_trace": trace
        })
        return res.get("hooks", []), creator

    start_parallel = time.perf_counter()
    results = await asyncio.gather(*[generate_variation(f) for f in frameworks])
    latency_parallel = (time.perf_counter() - start_parallel) * 1000

    all_hooks = []
    total_new_cost = 0.0
    token_usage = state.get("total_tokens", {"input": 0, "output": 0}).copy()
    latency_metrics = state.get("latency_metrics", {})

    for hooks, agent in results:
        all_hooks.extend(hooks)
        total_new_cost += agent.get_cost_cents()
        token_usage["input"] += agent.token_usage.get("input", 0)
        token_usage["output"] += agent.token_usage.get("output", 0)

    latency_metrics["hook_creation_parallel"] = latency_parallel

    if not all_hooks:
        trace.append("node_failed:hook_creation:critical")
        return {
            "status": "failed",
            "error_code": ErrorCode.CRITICAL_NODE_FAILURE,
            "execution_trace": trace,
            "current_stage": "hook_creation"
        }

    trace.append(f"node_success:hook_creation:count_{len(all_hooks)}")
    return {
        "raw_hooks": all_hooks,
        "total_cost_cents": state.get("total_cost_cents", 0) + total_new_cost,
        "total_tokens": token_usage,
        "latency_metrics": latency_metrics,
        "current_stage": "hook_creation",
        "execution_trace": trace,
        "last_model_used": results[0][1].last_model_used if results else "unknown"
    }


async def hook_evaluation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sub-node: Hook Evaluation."""
    memory = MemoryService()
    project_ctx = state.get("project_context") or {}
    raw_hooks = state.get("raw_hooks") or []
    
    evaluator = HookEvaluatorAgent(user_context=project_ctx)
    evaluated = await evaluator.execute({
        "hooks": raw_hooks,
    })
    
    evaluated_hooks = evaluated.get("evaluated_hooks", [])
    
    try:
        await memory.save_project_artifact(
            state.get("project_id", ""),
            state.get("thread_id", ""),
            "hooks",
            evaluated_hooks
        )
    except Exception as e:
        logger.warning("hook_evaluation_node: failed to save artifacts — %s", e)
        
    return {
        "hooks": evaluated_hooks,
        "total_cost_cents": state.get("total_cost_cents", 0) + evaluator.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + evaluator.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + evaluator.token_usage.get("output", 0),
        },
        "current_stage": "hook_evaluation",
        "completed_stages": state.get("completed_stages", []) + ["hook_generation"],
    }

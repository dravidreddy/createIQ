"""
Strategy Group — Stage 6 LangGraph node (OPTIONAL — skippable).

Orchestrates: SeriesPlanner → GrowthAdvisor
"""

import logging
from typing import Any, Dict

from app.agents.sub_agents.series_planner import SeriesPlannerAgent
from app.agents.sub_agents.growth_advisor import GrowthAdvisorAgent
from app.llm.base import ErrorCode
from app.agents.context import build_agent_context

logger = logging.getLogger(__name__)


async def series_planning_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sub-node: Series Planning."""
    ctx = build_agent_context(state)
    project_ctx = state.get("project_context") or {}
    edited_script = state.get("edited_script") or {}
    selected_idea = state.get("selected_idea") or {}
    
    final_script = edited_script.get("final_script", "")
    
    trace = state.get("execution_trace", [])
    trace.append("node_started:series_planning")

    planner = SeriesPlannerAgent(user_context=ctx)
    series = await planner.execute({
        "final_script": final_script,
        "selected_idea": selected_idea,
        "project_context": project_ctx,
        "execution_trace": trace
    })

    if not series:
        trace.append("node_warning:series_planning:empty_results")
    else:
        trace.append("node_success:series_planning")

    return {
        "series_plan": series.get("series_plan", []),
        "total_cost_cents": state.get("total_cost_cents", 0) + planner.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + planner.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + planner.token_usage.get("output", 0),
        },
        "current_stage": "series_planning",
        "execution_trace": trace,
        "last_model_used": planner.last_model_used
    }


async def growth_advisory_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sub-node: Growth Advisory."""
    ctx = build_agent_context(state)
    user_prefs = state.get("user_preferences") or {}
    series_plan = state.get("series_plan") or []

    trace = state.get("execution_trace", [])
    trace.append("node_started:growth_advisory")

    advisor = GrowthAdvisorAgent(user_context=ctx)
    growth = await advisor.execute({
        "series_plan": series_plan,
        "user_preferences": user_prefs,
        "execution_trace": trace
    })

    strategy_plan = {
        "series_plan": series_plan,
        "posting_schedule": growth.get("posting_schedule", {}),
        "growth_tips": growth.get("growth_tips", []),
        "cross_promotion_ideas": growth.get("cross_promotion_ideas", []),
        "audience_growth_projections": growth.get("audience_growth_projections", {}),
    }

    if not growth:
        trace.append("node_warning:growth_advisory:empty_results")
    else:
        trace.append("node_success:growth_advisory")

    return {
        "strategy_plan": strategy_plan,
        "total_cost_cents": state.get("total_cost_cents", 0) + advisor.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + advisor.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + advisor.token_usage.get("output", 0),
        },
        "current_stage": "growth_advisory",
        "completed_stages": state.get("completed_stages", []) + ["strategy"],
        "execution_trace": trace,
        "last_model_used": advisor.last_model_used
    }

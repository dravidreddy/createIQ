"""
Idea Discovery Group — Stage 1 LangGraph node.

Orchestrates: TrendResearcher → IdeaGenerator → IdeaRanker
"""

import logging
from typing import Any, Dict

from app.agents.sub_agents.trend_researcher import TrendResearcherAgent
from app.agents.sub_agents.idea_generator import IdeaGeneratorAgent
from app.agents.sub_agents.idea_ranker import IdeaRankerAgent
from app.memory.service import MemoryService
from app.llm.base import ErrorCode
from app.agents.context import build_agent_context

logger = logging.getLogger(__name__)





async def trend_research_node(state: Dict[str, Any]) -> Dict[str, Any]:
    trace = state.get("execution_trace", [])
    trace.append("node_started:trend_research")
    
    project_ctx = state.get("project_context") or {}
    agent_ctx = build_agent_context(state)
    user_prefs = state.get("user_preferences") or {}
    
    researcher = TrendResearcherAgent(user_context=agent_ctx)
    research = await researcher.execute({
        "topic": project_ctx.get("topic", ""),
        "niche": project_ctx.get("niche", "general"),
        "platforms": project_ctx.get("platforms", ["YouTube"]),
        "target_audience": project_ctx.get("target_audience", "general"),
        "user_preferences": user_prefs,
        "execution_trace": trace # Pass trace to execution layer
    })
    
    # Non-critical: If research fails, we can still generate ideas from basic topic
    results = research.get("research_results", [])
    if not results:
        trace.append("node_warning:trend_research:empty_results")
    else:
        trace.append("node_success:trend_research")

    return {
        "research_results": results,
        "total_cost_cents": state.get("total_cost_cents", 0) + researcher.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + researcher.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + researcher.token_usage.get("output", 0),
        },
        "current_stage": "trend_research",
        "execution_trace": trace,
        "last_model_used": researcher.last_model_used
    }


async def idea_generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    trace = state.get("execution_trace", [])
    trace.append("node_started:idea_generation")
    
    project_ctx = state.get("project_context") or {}
    agent_ctx = build_agent_context(state)
    user_prefs = state.get("user_preferences") or {}
    research_results = state.get("research_results") or []
    
    generator = IdeaGeneratorAgent(user_context=agent_ctx)
    ideas_res = await generator.execute({
        "research_results": research_results,
        "user_preferences": user_prefs,
        "project_context": project_ctx,
        "execution_trace": trace
    })
    
    ideas = ideas_res.get("ideas", [])
    if not ideas:
        trace.append("node_failed:idea_generation:critical")
        return {
            "status": "failed",
            "error_code": ErrorCode.CRITICAL_NODE_FAILURE,
            "execution_trace": trace,
            "current_stage": "idea_generation"
        }

    trace.append("node_success:idea_generation")
    return {
        "raw_ideas": ideas,
        "total_cost_cents": state.get("total_cost_cents", 0) + generator.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + generator.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + generator.token_usage.get("output", 0),
        },
        "current_stage": "idea_generation",
        "execution_trace": trace,
        "last_model_used": generator.last_model_used
    }


async def idea_ranking_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Sub-node: Idea Ranking."""
    memory = MemoryService()
    project_ctx = state.get("project_context") or {}
    agent_ctx = build_agent_context(state)
    user_prefs = state.get("user_preferences") or {}
    raw_ideas = state.get("raw_ideas") or []
    
    ranker = IdeaRankerAgent(user_context=agent_ctx)
    ranked = await ranker.execute({
        "ideas": raw_ideas,
        "user_preferences": user_prefs,
    })
    
    ranked_ideas = ranked.get("ranked_ideas", [])
    
    # Store in project memory
    try:
        await memory.save_project_artifact(
            state.get("project_id", ""),
            state.get("thread_id", ""),
            "ideas",
            ranked_ideas,
            user_id=state.get("user_id", ""),
        )
    except Exception as e:
        logger.warning("idea_ranking_node: failed to save artifacts — %s", e)
        
    return {
        "ideas": ranked_ideas,
        "total_cost_cents": state.get("total_cost_cents", 0) + ranker.get_cost_cents(),
        "total_tokens": {
            "input": state.get("total_tokens", {}).get("input", 0) + ranker.token_usage.get("input", 0),
            "output": state.get("total_tokens", {}).get("output", 0) + ranker.token_usage.get("output", 0),
        },
        "current_stage": "idea_ranking",
        "completed_stages": state.get("completed_stages", []) + ["idea_discovery"],
    }

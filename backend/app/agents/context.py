"""Shared helpers for passing pipeline context into agents."""

from typing import Any, Dict


def build_agent_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """Return project context enriched with runtime IDs and preferences."""
    project_context = dict(state.get("project_context") or {})
    return {
        **project_context,
        "user_id": state.get("user_id"),
        "project_id": state.get("project_id"),
        "thread_id": state.get("thread_id"),
        "job_id": state.get("job_id"),
        "user_preferences": state.get("user_preferences") or {},
        "total_cost_cents": state.get("total_cost_cents", 0.0),
        "project_budget_limit": state.get("project_budget_limit", 50.0),
    }

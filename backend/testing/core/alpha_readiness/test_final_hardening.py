import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.pipeline.graph import budget_guard, state_sentinel_node
from app.utils.text import truncate_text

@pytest.mark.asyncio
async def test_budget_guard_cost_logging():
    """Verify that budget_guard correctly logs cost diffs to cost_log."""
    async def mock_node(state):
        # Simulate a node that adds 0.5 cents
        state["total_cost_cents"] = state.get("total_cost_cents", 0.0) + 0.5258
        return state
        
    guarded_node = budget_guard(mock_node)
    
    # 1. First execution
    state = {"total_cost_cents": 0.0, "cost_log": []}
    res = await guarded_node(state)
    
    assert res["total_cost_cents"] == 0.5258
    assert len(res["cost_log"]) == 1
    assert res["cost_log"][0] == 0.5258
    
    # 2. Second execution (incremental)
    res2 = await guarded_node(res)
    assert res2["total_cost_cents"] == 1.0516
    assert len(res2["cost_log"]) == 2
    assert res2["cost_log"][1] == 0.5258

@pytest.mark.asyncio
async def test_semantic_truncation_ux():
    """Verify that truncation preserves head, tail, and cuts at sentences."""
    text = (
        "This is the first sentence. " * 50 + 
        "This is the IMPORTANT MIDDLE. " + 
        "This is the last sentence. " * 50
    )
    
    # max_chars=500 for testing
    truncated = truncate_text(text, max_chars=500)
    
    # Check Head preservation
    assert "This is the first sentence." in truncated
    # Check Tail preservation
    assert "This is the last sentence." in truncated
    # Check marker
    assert "[SAFE TRUNCATED BY SENTINEL]" in truncated
    # Check semantic boundary (should end with a period)
    head_part = truncated.split("\n\n...")[0]
    assert head_part.endswith(".") or head_part.endswith("\n")

@pytest.mark.asyncio
async def test_cost_drift_no_double_count():
    """Verify no cost is logged if the node doesn't increase total_cost_cents."""
    async def failing_node(state):
        # Node fails or budget hit, cost doesn't increase
        return state
        
    guarded_node = budget_guard(failing_node)
    state = {"total_cost_cents": 1.0, "cost_log": [1.0]}
    res = await guarded_node(state)
    
    assert len(res["cost_log"]) == 1 # No change
    assert res["total_cost_cents"] == 1.0

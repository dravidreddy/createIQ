import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from app.schemas.pipeline import PipelineEvent

logger = logging.getLogger(__name__)


def format_sse(event: PipelineEvent) -> str:
    """Format a PipelineEvent as an SSE data line with model_dump_json for Pydantic v2."""
    payload = event.model_dump_json()
    return f"data: {payload}\n\n"


def heartbeat_event(thread_id: str, request_id: str, seq: int) -> str:
    """Periodic heartbeat to keep connection alive."""
    return format_sse(PipelineEvent(
        type="heartbeat",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
    ))


def token_event(thread_id: str, request_id: str, seq: int, token: str, node: str = None) -> str:
    """Incremental token update (Real-time typing)."""
    return format_sse(PipelineEvent(
        type="token",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
        node=node,
        content=token
    ))


def group_start_event(thread_id: str, request_id: str, seq: int, stage: str, message: str = None) -> str:
    """Signal the start of a pipeline stage."""
    return format_sse(PipelineEvent(
        type="group_start",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
        stage=stage,
        content=message or f"Starting {stage}..."
    ))


def group_complete_event(thread_id: str, request_id: str, seq: int, stage: str, summary: str = "") -> str:
    """Signal the completion of a pipeline stage."""
    return format_sse(PipelineEvent(
        type="group_complete",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
        stage=stage,
        content=summary or f"Completed {stage}"
    ))


def thinking_event(thread_id: str, request_id: str, seq: int, message: str, node: str = None) -> str:
    """Explicitly emit an agent thinking event."""
    return format_sse(PipelineEvent(
        type="thinking",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
        node=node,
        content=message
    ))


def agent_start_event(thread_id: str, request_id: str, seq: int, node: str, stage: str = None, message: str = None) -> str:
    """Signal that a specific agent/node has started."""
    return format_sse(PipelineEvent(
        type="agent_start",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
        node=node,
        stage=stage,
        content=message or f"Running {node}..."
    ))


def agent_complete_event(
    thread_id: str,
    request_id: str,
    seq: int,
    node: str,
    tokens: Dict[str, int] = None,
    cost_cents: float = 0,
    model: str = None,
    status: str = "success",
    fallback_used: bool = False
) -> str:
    """Signal that an agent has finished with metrics and status."""
    return format_sse(PipelineEvent(
        type="agent_complete",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
        node=node,
        tokens=tokens,
        cost_cents=cost_cents,
        model=model,
        status=status,
        fallback_used=fallback_used
    ))


def interrupt_event(thread_id: str, request_id: str, seq: int, stage: str, message: str, data: Any = None) -> str:
    """Signal a HITL interrupt point."""
    return format_sse(PipelineEvent(
        type="interrupt",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
        stage=stage,
        content={"message": message, "output": data, "interrupt_version": 1}
    ))


def fallback_event(thread_id: str, request_id: str, seq: int, from_provider: str, to_provider: str, node: str = None) -> str:
    """Identify when a provider fallback occurs."""
    return format_sse(PipelineEvent(
        type="fallback",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
        node=node,
        content={"from": from_provider, "to": to_provider}
    ))


def node_complete_event(thread_id: str, request_id: str, seq: int, node: str, status: str = "success") -> str:
    """Signal that a specific graph node has finished its complete execution."""
    return format_sse(PipelineEvent(
        type="node_complete",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
        node=node,
        status=status
    ))


def metrics_event(
    thread_id: str, 
    request_id: str, 
    seq: int, 
    ttft_ms: float = None, 
    total_latency_ms: float = None, 
    tps: float = None,
    cost_cents: float = None
) -> str:
    """Consolidated performance telemetry event."""
    return format_sse(PipelineEvent(
        type="metrics",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
        ttft_ms=ttft_ms,
        total_latency_ms=total_latency_ms,
        tokens_per_second=tps,
        cost_cents=cost_cents
    ))


def stream_start_event(thread_id: str, request_id: str, seq: int) -> str:
    """Initial event to synchronize frontend timing and sequencing."""
    return format_sse(PipelineEvent(
        type="stream_start",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
    ))


def stream_end_event(thread_id: str, request_id: str, seq: int, status: str = "success") -> str:
    """Standardized final event. The single source of truth for stopping loaders."""
    return format_sse(PipelineEvent(
        type="stream_end",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
        status=status,
        final=True,
        content=f"Pipeline stream terminated with status: {status}"
    ))


def error_event(thread_id: str, request_id: str, seq: int, message: str, error_type: str = "UNKNOWN", node: str = None, recoverable: bool = True) -> str:
    """Standardized error event with traceability."""
    return format_sse(PipelineEvent(
        type="error",
        seq=seq,
        thread_id=thread_id,
        request_id=request_id,
        node=node,
        error_type=error_type,
        content=message,
        retryable=recoverable
    ))


def format_state_update_as_sse(event: Dict[str, Any], thread_id: str, request_id: str, seq: int) -> List[str]:
    """
    Convert a LangGraph state update event to SSE lines.
    Ensures agent_complete is emitted with correct cost/token metadata.
    """
    sse_lines = []
    
    # LangGraph emits: {node_name: {state_delta}}
    for node_name, state_update in event.items():
        if not isinstance(state_update, dict):
            continue

        # If it's a major stage boundary, update tracking
        current_stage = state_update.get("current_stage", "")
        if current_stage:
            sse_lines.append(group_complete_event(thread_id, request_id, seq, current_stage))
            seq += 1

        # Emit agent completion if metrics are updated
        cost = state_update.get("total_cost_cents")
        tokens = state_update.get("total_tokens")
        if cost is not None or tokens is not None:
            sse_lines.append(agent_complete_event(
                thread_id=thread_id,
                request_id=request_id,
                seq=seq,
                node=node_name,
                tokens=tokens,
                cost_cents=cost or 0.0
            ))
            seq += 1

    return sse_lines


def get_interrupt_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract minimal interrupt data for recovery."""
    stage = state.get("current_stage", "")
    stage_data_map = {
        "idea_discovery": {
            "type": "idea_selection",
            "message": "Select an idea",
            "current_output": state.get("ideas", []),
            "options": ["approve", "edit", "regenerate"],
            "node": "process_idea_selection"
        },
        "hook_generation": {
            "type": "hook_selection",
            "message": "Select a hook",
            "current_output": state.get("hooks", []),
            "options": ["approve", "edit", "regenerate"],
            "node": "process_hook_selection"
        },
        "script_writing": {
            "type": "script_review",
            "message": "Review script",
            "current_output": state.get("script", {}),
            "options": ["approve", "edit", "regenerate"],
            "node": "process_script_edit"
        },
        "editing": {
            "type": "final_review",
            "message": "Final Review",
            "current_output": state.get("edited_script", {}),
            "options": ["approve", "edit", "regenerate", "skip"],
            "node": "process_final_review"
        }
    }
    return stage_data_map.get(stage, {
        "type": stage,
        "message": f"Review required for {stage}",
        "current_output": {},
        "options": ["approve"],
        "node": "unknown"
    })

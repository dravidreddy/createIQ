"""
SSE Streaming Utilities

Server-Sent Events helpers for real-time agent updates.
"""

from app.utils.datetime_utils import utc_now
import json
from datetime import datetime
from typing import Any, Dict, AsyncGenerator
from app.schemas.agent import AgentStreamEvent


def format_sse_event(event: AgentStreamEvent) -> str:
    """
    Format an event for SSE transmission.
    
    Args:
        event: AgentStreamEvent to format
        
    Returns:
        SSE-formatted string
    """
    data = event.model_dump()
    # Convert datetime to ISO format string
    if isinstance(data.get("timestamp"), datetime):
        data["timestamp"] = data["timestamp"].isoformat()
    
    return f"data: {json.dumps(data)}\n\n"


def create_event(
    event_type: str,
    agent_name: str = None,
    data: Dict[str, Any] = None
) -> AgentStreamEvent:
    """
    Create a stream event.
    
    Args:
        event_type: Type of event
        agent_name: Name of the agent
        data: Event data
        
    Returns:
        AgentStreamEvent instance
    """
    return AgentStreamEvent(
        event_type=event_type,
        agent_name=agent_name,
        timestamp=utc_now(),
        data=data or {}
    )


def agent_start_event(agent_name: str, input_summary: str = None) -> str:
    """Create agent start SSE event."""
    event = create_event(
        event_type="agent_start",
        agent_name=agent_name,
        data={"message": f"Starting {agent_name}", "input_summary": input_summary}
    )
    return format_sse_event(event)


def agent_complete_event(agent_name: str, summary: str = None) -> str:
    """Create agent complete SSE event."""
    event = create_event(
        event_type="agent_complete",
        agent_name=agent_name,
        data={"message": f"Completed {agent_name}", "summary": summary}
    )
    return format_sse_event(event)


def tool_call_event(
    agent_name: str,
    tool_name: str,
    tool_input: Dict[str, Any],
    status: str = "started"
) -> str:
    """Create tool call SSE event."""
    event = create_event(
        event_type="tool_call",
        agent_name=agent_name,
        data={
            "tool_name": tool_name,
            "tool_input": tool_input,
            "status": status
        }
    )
    return format_sse_event(event)


def tool_result_event(
    agent_name: str,
    tool_name: str,
    result_summary: str,
    duration_ms: int = None
) -> str:
    """Create tool result SSE event."""
    event = create_event(
        event_type="tool_result",
        agent_name=agent_name,
        data={
            "tool_name": tool_name,
            "result_summary": result_summary,
            "duration_ms": duration_ms
        }
    )
    return format_sse_event(event)


def reasoning_event(agent_name: str, step: int, thought: str, action: str = None) -> str:
    """Create reasoning SSE event."""
    event = create_event(
        event_type="reasoning",
        agent_name=agent_name,
        data={
            "step": step,
            "thought": thought,
            "action": action
        }
    )
    return format_sse_event(event)


def token_update_event(
    agent_name: str,
    input_tokens: int,
    output_tokens: int
) -> str:
    """Create token usage update SSE event."""
    total = input_tokens + output_tokens
    # Gemini 2.0 Flash pricing (approximate)
    estimated_cost = (input_tokens * 0.000000075) + (output_tokens * 0.0000003)
    
    event = create_event(
        event_type="token_update",
        agent_name=agent_name,
        data={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total,
            "estimated_cost_usd": round(estimated_cost, 6)
        }
    )
    return format_sse_event(event)


def output_event(agent_name: str, content: str, is_complete: bool = False) -> str:
    """Create output chunk SSE event."""
    event = create_event(
        event_type="output",
        agent_name=agent_name,
        data={
            "content": content,
            "is_complete": is_complete
        }
    )
    return format_sse_event(event)


def error_event(agent_name: str, error_message: str, recoverable: bool = True) -> str:
    """Create error SSE event."""
    event = create_event(
        event_type="error",
        agent_name=agent_name,
        data={
            "error": error_message,
            "recoverable": recoverable
        }
    )
    return format_sse_event(event)


def done_event(project_id: int = None, status: str = "completed") -> str:
    """Create stream complete SSE event."""
    event = create_event(
        event_type="done",
        data={
            "project_id": project_id,
            "status": status,
            "message": "Pipeline execution complete"
        }
    )
    return format_sse_event(event)


class StreamValidator:
    """
    Validates streaming chunks for consistency, order, and deduplication.
    """
    def __init__(self):
        self.last_chunk_content = ""
        self.total_length = 0
        self.chunk_count = 0

    def validate_chunk(self, content: str) -> bool:
        """
        Check if the chunk is valid (non-duplicate, consistent).
        """
        if not content:
            return True
            
        # Deduplication check (some providers repeat the last chunk or send empty and then full)
        if content == self.last_chunk_content and len(content) > 1:
            return False
            
        self.last_chunk_content = content
        self.total_length += len(content)
        self.chunk_count += 1
        return True

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "total_chars": self.total_length,
            "chunk_count": self.chunk_count
        }

"""
Agent Schemas

Pydantic schemas for agent execution and streaming events.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class AgentExecutionRequest(BaseModel):
    """Schema for agent execution request."""
    project_id: int
    agent_name: str = Field(..., pattern="^(idea_discovery|research_script|screenplay_structure|editing_improvement|full_pipeline)$")
    additional_input: Optional[Dict[str, Any]] = None


class AgentStreamEvent(BaseModel):
    """
    Schema for SSE stream events.
    
    Event types:
    - agent_start: Agent execution started
    - agent_complete: Agent execution completed
    - tool_call: Tool is being called
    - tool_result: Tool returned result
    - reasoning: LLM is reasoning/thinking
    - token_update: Token usage update
    - output: Partial output chunk
    - error: Error occurred
    - done: Stream complete
    """
    event_type: Literal[
        "agent_start",
        "agent_complete", 
        "tool_call",
        "tool_result",
        "reasoning",
        "token_update",
        "output",
        "error",
        "done"
    ]
    agent_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = {}


class ToolCallEvent(BaseModel):
    """Schema for tool call events."""
    tool_name: str
    tool_input: Dict[str, Any]
    status: Literal["started", "completed", "failed"]
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class ReasoningEvent(BaseModel):
    """Schema for reasoning/thinking events."""
    step: int
    thought: str
    action: Optional[str] = None


class TokenUsageEvent(BaseModel):
    """Schema for token usage tracking."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class AgentSessionResponse(BaseModel):
    """Schema for agent session API response."""
    id: int
    project_id: int
    agent_name: str
    status: str
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    execution_logs: List[Dict[str, Any]] = []
    input_tokens: int = 0
    output_tokens: int = 0
    execution_time_seconds: Optional[float] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PipelineStatus(BaseModel):
    """Schema for full pipeline status."""
    project_id: int
    status: str
    current_agent: Optional[str] = None
    completed_agents: List[str] = []
    pending_agents: List[str] = []
    progress_percentage: float
    estimated_time_remaining: Optional[str] = None

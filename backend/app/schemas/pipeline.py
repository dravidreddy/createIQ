"""
Pipeline Schemas

Request/response schemas for the LangGraph pipeline API endpoints.
Also contains output schemas for each pipeline stage.
"""

from app.utils.datetime_utils import utc_now
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ─── Existing stage output schemas (kept for backward compat) ────

class IdeaSchema(BaseModel):
    title: str
    description: str
    trending_reason: str
    unique_angle: str
    engagement_potential: str
    source_urls: List[str] = []
    keywords: List[str] = []


class IdeaDiscoveryOutput(BaseModel):
    ideas: List[IdeaSchema]
    analysis_summary: str = ""


class HookSchema(BaseModel):
    text: str
    framework: str
    explanation: str
    target_emotion: str = ""
    quality_score: Optional[float] = None
    refined_text: Optional[str] = None


class HookCreationOutput(BaseModel):
    hooks: List[HookSchema]


class HookAnalysisSchema(BaseModel):
    current_hook: str
    hook_strength: str
    improvement_suggestions: List[str] = []


class StructureBreakdownSchema(BaseModel):
    timestamp_or_position: str
    section_name: str
    current_content_summary: str
    recommendation: str
    pacing_note: str


class RetentionCheckpointSchema(BaseModel):
    position: str
    technique: str
    implementation: str


class VisualAudioCueSchema(BaseModel):
    position: str
    cue_type: str
    suggestion: str


class CTAPlacementSchema(BaseModel):
    recommended_position: str
    cta_script: str


class PlatformSpecificTipSchema(BaseModel):
    platform: str
    tip: str


class ScreenplayGuidanceSchema(BaseModel):
    overall_assessment: str
    hook_analysis: HookAnalysisSchema
    structure_breakdown: List[StructureBreakdownSchema] = []
    retention_checkpoints: List[RetentionCheckpointSchema] = []
    visual_audio_cues: List[VisualAudioCueSchema] = []
    cta_placement: Optional[CTAPlacementSchema] = None
    platform_specific_tips: List[PlatformSpecificTipSchema] = []


# ─── Pipeline API Schemas ────────────────────────────────────────


class PipelineStartRequest(BaseModel):
    """Request body to start a new pipeline execution."""
    project_id: str = Field(..., description="MongoDB project ID")
    topic: str = Field(..., description="Content topic to explore")
    niche: str = Field(default="general", description="Content niche")
    platforms: List[str] = Field(default=["YouTube"], description="Target platforms")
    platform: str = Field(default="YouTube", description="Primary target platform for this run")
    execution_mode: str = Field(default="auto", description="Execution mode: auto, guided, manual")
    video_length: str = Field(default="Medium (1-10 min)", description="Target video length")
    target_audience: str = Field(default="general audience", description="Target audience")
    language: str = Field(default="English", description="Content language")
    style_overrides: Dict[str, str] = Field(default={}, description="Optional style overrides")


class PipelineResumeRequest(BaseModel):
    """Request body to resume pipeline after a human-in-the-loop interrupt."""
    action: Literal["approve", "edit", "regenerate", "skip"] = Field(
        ..., description="User action at interrupt"
    )
    stage: str = Field(..., description="Which stage this resume applies to")
    edited_content: Optional[Any] = Field(
        None, description="User-edited content (when action='edit')"
    )
    selected_content: Optional[Any] = Field(
        None, description="User-selected item (idea, hook, etc.)"
    )


class PipelineStatusResponse(BaseModel):
    """Response for pipeline status query with production metrics."""
    thread_id: str
    current_stage: Optional[str] = None
    completed_stages: List[str] = []
    next_nodes: List[str] = []
    total_cost_cents: float = 0.0
    total_tokens: Dict[str, int] = {"input": 0, "output": 0}
    errors: List[str] = []
    
    # Production Hardening
    interrupt_data: Optional["PipelineInterruptData"] = None
    interrupt_version: int = 1
    config_version: int = 1
    ttft_ms: Optional[float] = None
    total_latency_ms: Optional[float] = None
    tokens_per_second: Optional[float] = None


class PipelineInterruptData(BaseModel):
    """Data sent to frontend when pipeline interrupts for user input."""
    stage: str
    message: str
    output: Any = None
    options: List[str] = ["approve", "edit", "regenerate"]
    timestamp: datetime = Field(default_factory=utc_now)
    interrupt_version: int = 1


class PipelineEvent(BaseModel):
    """Canonical SSE Event Schema (Single Source of Truth)."""
    type: str  # token | agent_start | agent_complete | group_start | group_complete | interrupt | cost_update | error | stream_start | stream_end | heartbeat | fallback | node_complete | metrics
    seq: int
    thread_id: str
    request_id: str
    node: Optional[str] = None
    stage: Optional[str] = None
    content: Optional[Any] = None
    tokens: Optional[Dict[str, int]] = None
    cost_cents: Optional[float] = None
    model: Optional[str] = None
    status: Optional[str] = None  # success | fallback | failed | interrupted | error
    fallback_used: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
    
    # Metrics / Resilience
    final: bool = False  # True only for stream_end
    ttft_ms: Optional[float] = None
    total_latency_ms: Optional[float] = None
    tokens_per_second: Optional[float] = None

    # Specific error context
    error_type: Optional[str] = None  # RATE_LIMIT | TIMEOUT | AUTH | UNKNOWN
    retryable: bool = False

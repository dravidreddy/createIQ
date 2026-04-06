"""
PipelineState — TypedDict schema for the LangGraph state graph.

Defines the shape of data flowing through the entire pipeline,
including stage outputs, edit history, execution tracking, and
human-in-the-loop control signals.
"""

from typing import Any, Dict, List, Optional, TypedDict


class UserPreferences(TypedDict):
    """Learned user preferences from edit detection."""
    writing_style: str           # "conversational" | "formal" | "technical"
    tone: str                    # "enthusiastic" | "neutral" | "professional"
    preferred_length: str        # "concise" | "detailed" | "mixed"
    vocabulary_level: str        # "simple" | "moderate" | "advanced"
    engagement_style: str        # "question-heavy" | "story-driven" | "data-driven"
    custom_signals: Dict[str, float]


class ProjectContext(TypedDict):
    """Project-level configuration for the pipeline."""
    topic: str
    niche: str
    platforms: List[str]
    platform: Optional[str]      # Target platform for the current run
    video_length: str
    target_audience: str
    language: str
    style_overrides: Dict[str, str]


class EditRecord(TypedDict):
    """Record of a user edit at a pipeline interrupt."""
    stage: str
    diff_summary: str
    preference_signals: Dict[str, float]
    timestamp: str


class PipelineState(TypedDict):
    """Complete state flowing through the LangGraph pipeline."""

    # ── Identity ────────────────────────────────────────────────
    user_id: str
    project_id: str
    thread_id: str
    job_id: str

    # ── Memory (loaded at start, refreshed at interrupts) ──────
    user_preferences: Optional[UserPreferences]
    project_context: ProjectContext

    # ── Stage outputs (accumulated through pipeline) ───────────
    ideas: Optional[List[Dict[str, Any]]]
    selected_idea: Optional[Dict[str, Any]]
    hooks: Optional[List[Dict[str, Any]]]
    selected_hook: Optional[Dict[str, Any]]
    script: Optional[Dict[str, Any]]
    structure_guidance: Optional[Dict[str, Any]]
    edited_script: Optional[Dict[str, Any]]
    strategy_plan: Optional[Dict[str, Any]]

    # ── Edit history ───────────────────────────────────────────
    edit_history: List[EditRecord]

    # ── Execution tracking ─────────────────────────────────────
    current_stage: str
    completed_stages: List[str]
    errors: List[str]
    total_cost_cents: float
    cost_log: List[float]         # Audit trail of individual call costs
    total_tokens: Dict[str, int]  # {"input": N, "output": M}
    execution_mode: str          # "auto" | "guided" | "manual"
    node_confidence: Dict[str, float]
    
    # ── Tier 2 Hardening ───────────────────────────────────────
    compressed_state: Dict[str, str]    # {stage: summary}
    context_metadata: Dict[str, Any]     # budget tracking, pruning logs
    evaluator_scores: Dict[str, float]   # {node_name: quality_score}
    prompt_versions: Dict[str, str]      # {node_name: version_id}
    
    # ── V4 Production Refinements ──────────────────────────────
    latency_metrics: Dict[str, float]    # {node_name: latency_ms}
    feedback: List[Dict[str, Any]]       # [{node: str, rating: int, comment: str}]
    project_budget_limit: float          # budget cap in cents
    iteration_count: int                 # global loop protection

    # ── Human-in-the-loop control ──────────────────────────────
    user_action: Optional[str]           # "approve" | "edit" | "regenerate" | "skip"
    _last_action: Optional[str]          # preserved for routing
    user_edited_content: Optional[Any]
    should_terminate: bool

    # ── SSE streaming buffer ───────────────────────────────────
    stream_events: List[Dict[str, Any]]
    
    # ── V4 Production Hardening ────────────────────────────────
    status: str                          # "idle" | "running" | "success" | "failed" | "timeout"
    error_code: Optional[str]            # Standardized error code
    execution_trace: List[str]           # Step-by-step lifecycle log
    last_model_used: Optional[str]       # Name of the last model that responded
    fallback_triggered: bool             # Whether a fallback occurred during execution

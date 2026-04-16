"""
LangGraph Pipeline Graph — 6-stage content creation pipeline with HITL.

Defines the complete StateGraph with 18 nodes, interrupt_before at each
stage boundary for human-in-the-loop, and a MongoDB-backed checkpointer.
"""

import logging
from typing import Any, Dict, Literal

from langgraph.graph import END, StateGraph

from app.memory.service import MemoryService
from app.pipeline.state import PipelineState
from app.pipeline.checkpointer import MongoDBCheckpointer

# Import atomic nodes
from app.agents.groups.idea_discovery import trend_research_node, idea_generation_node, idea_ranking_node
from app.agents.groups.hook_generation import hook_creation_node, hook_evaluation_node
from app.agents.groups.script_writing import deep_research_node, script_drafting_node, fact_checking_node
from app.agents.groups.structure import structure_analysis_node, pacing_optimization_node
from app.agents.groups.editing import line_editing_node, engagement_boosting_node, final_review_node
from app.agents.groups.strategy import series_planning_node, growth_advisory_node

# Tier 2 Utilities
from app.agents.sub_agents.evaluator import EvaluatorAgent
from app.utils.context_manager import get_context_manager
from app.utils.text import truncate_text
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


_GENERIC_CONTEXT_VALUES = {
    "",
    "general",
    "general audience",
    "medium (1-10 min)",
    "english",
    "youtube",
    "other",
    "mixed",
}


def _is_generic_context_value(value: Any) -> bool:
    """Return True when a request default should yield to saved profile context."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in _GENERIC_CONTEXT_VALUES
    if isinstance(value, list):
        lowered = [str(v).strip().lower() for v in value if v]
        return not lowered or lowered == ["youtube"]
    return False



# ── Utility nodes and Guards ─────────────────────────────────────

def budget_guard(node_func):
    """
    Decorator for LangGraph nodes to enforce global budget limits.
    Stops execution instantly if budget is exceeded or termination requested.
    """
    from functools import wraps
    @wraps(node_func)
    async def wrapper(state: PipelineState, *args, **kwargs) -> PipelineState:
        # 1. Global Safety Check
        if state.get("should_terminate") or state.get("errors") and "unrecoverable" in str(state.get("errors")[-1]):
            logger.warning(f"BudgetGuard: Skipping node {node_func.__name__} (Termination requested or unrecoverable error)")
            return state
            
        # 2. Check local flag (set by ExecutionLayer or Sentinel)
        if state.get("context_metadata", {}).get("error") == "budget_exceeded":
            logger.error(f"BudgetGuard: Skipping node {node_func.__name__} (Budget exceeded)")
            return {**state, "should_terminate": True}
            
        # 3. Execution + Cost Logging
        prev_cost = state.get("total_cost_cents", 0.0)
        
        # Call the node
        new_state = await node_func(state, *args, **kwargs)
        
        # Calculate cost diff and log it
        new_cost = new_state.get("total_cost_cents", 0.0)
        cost_diff = new_cost - prev_cost
        
        if cost_diff > 0:
            log = new_state.get("cost_log")
            if log is None: log = []
            log.append(round(cost_diff, 4)) # Preserve precision
            new_state["cost_log"] = log
            
        return new_state
    return wrapper



async def load_memory_node(state: PipelineState) -> PipelineState:
    """Load UserPreferences + ProjectContext from memory service, then resolve NAPOS niche."""
    memory = MemoryService()
    from app.services.user import UserService
    user_service = UserService()

    user_prefs = await memory.get_user_preferences(state.get("user_id", ""))

    # If project_context isn't set from the request, load from DB
    project_ctx = state.get("project_context") or {}
    if not project_ctx.get("topic"):
        db_ctx = await memory.get_project_context(state.get("project_id", ""))
        project_ctx = {**db_ctx, **project_ctx}

    # Merge User Profile Context (Brand Voice, Persona)
    user_profile_ctx = await user_service.get_profile_context(state.get("user_id", ""))
    if user_profile_ctx:
        profile_dict = user_profile_ctx.model_dump()
        profile_field_map = {
            "content_niche": "niche",
            "platforms": "platforms",
            "video_length": "video_length",
            "language": "language",
        }
        for key, value in profile_dict.items():
            if not value:
                continue
            target_key = profile_field_map.get(key, key)
            existing = project_ctx.get(target_key)
            if _is_generic_context_value(existing):
                project_ctx[target_key] = value

        if profile_dict.get("platforms") and _is_generic_context_value(project_ctx.get("platform")):
            project_ctx["platform"] = profile_dict["platforms"][0]

        style_overrides = dict(project_ctx.get("style_overrides") or {})
        for style_key in (
            "content_style",
            "additional_context",
            "vocabulary",
            "avoid_words",
            "formality_level",
            "hook_framework",
            "default_cta",
            "pacing_style",
        ):
            value = profile_dict.get(style_key)
            if value and not style_overrides.get(style_key):
                style_overrides[style_key] = value
            if value and _is_generic_context_value(project_ctx.get(style_key)):
                project_ctx[style_key] = value
        project_ctx["style_overrides"] = style_overrides

    # NAPOS: Resolve niche via inference if not explicitly set
    from app.utils.niche_inference import infer_niche
    napos_niche = state.get("napos_niche") or project_ctx.get("niche")
    if not napos_niche or napos_niche.lower() in ("general", "other", ""):
        profile_niche = None
        if user_profile_ctx:
            profile_niche = user_profile_ctx.content_niche
        napos_niche = infer_niche(
            topic=project_ctx.get("topic", ""),
            user_profile_niche=profile_niche,
        )
    else:
        napos_niche = napos_niche.lower().strip()

    # Ensure niche is also in project_context for downstream agents
    project_ctx["niche"] = napos_niche

    # Initialize NAPOS orchestrator with memory service
    from app.utils.prompt_orchestrator import get_prompt_orchestrator
    get_prompt_orchestrator(memory_service=memory)

    return {
        **state,
        "user_preferences": user_prefs,
        "project_context": project_ctx,
        "napos_niche": napos_niche,
        "current_stage": "load_memory",
    }


async def validate_inputs_node(state: PipelineState) -> PipelineState:
    """
    Scan inputs for prompt injection or policy violations using weighted heuristics.
    Alpha Upgrade: Advanced pattern matching + scoring.
    """
    ctx = state.get("project_context", {})
    topic = ctx.get("topic", "")
    audience = ctx.get("target_audience", "")
    combined_input = f"{topic} {audience}"
    
    score = 0
    # 1. Jailbreak Patterns
    jailbreak_patterns = ["ignore previous", "bypass", "system prompt", "override instructions", "forget everything", "DAN", "developer mode"]
    for p in jailbreak_patterns:
        if p.lower() in combined_input.lower():
            score += 40
            
    # 2. Command Injection
    cmd_patterns = ["rm -rf", "curl ", "wget ", "sudo ", "chmod ", ".sh"]
    for p in cmd_patterns:
        if p.lower() in combined_input.lower():
            score += 30
            
    # 3. HTML/Script Injection
    script_patterns = ["<script", "javascript:", "onload=", "onerror="]
    for p in script_patterns:
        if p.lower() in combined_input.lower():
            score += 50

    # 4. Long context / character repetition (DDoS-style)
    if len(combined_input) > 2000:
        score += 20

    if score >= 50:
        logger.warning(f"validate_inputs: High safety score ({score}) for input: {topic[:50]}...")
        errors = state.get("errors", [])
        errors.append(f"unauthorized unrecoverable: policy violation or prompt injection detected (score: {score})")
        return {
            **state,
            "errors": errors,
            "current_stage": "validate_inputs",
            "should_terminate": True,
        }
        
    return {
        **state,
        "current_stage": "validate_inputs"
    }


async def state_sentinel_node(state: PipelineState) -> PipelineState:
    """
    Enforces state size limits (200KB) and iteration caps (20).
    Alpha Readiness: Prevents DB payload errors and infinite loops.
    """
    import json
    
    # 1. Iteration Protection
    count = state.get("iteration_count", 0) + 1
    state["iteration_count"] = count
    if count > 20:
        logger.error(f"State Sentinel: Global iteration cap (20) exceeded for job {state.get('job_id')}. Terminating.")
        errors = state.get("errors", [])
        errors.append("unrecoverable: iteration_cap_exceeded - pipeline exceeds 20 iterations.")
        return {**state, "errors": errors, "should_terminate": True}

    # 2. Size Enforcement (Safe Truncation)
    try:
        state_json = json.dumps(state)
        size_kb = len(state_json.encode('utf-8')) / 1024
        
        if size_kb > settings.state_max_size_kb:
            logger.warning(f"State Sentinel: State size ({size_kb:.2f}KB) exceeds limit. Safe Pruning...")
            
            # Pruning Step 1: Truncate message context (keep last 3)
            # Assuming state['messages'] or similar exists in some agents, 
            # but for the global state we prune common large fields.
            if len(state.get("errors", [])) > 5:
                state["errors"] = state["errors"][-5:]
                
            # Pruning Step 2: Semantic-Aware Truncation of large output fields
            # New 9.9/10 hardening: preserve Head/Tail and cut at sentence boundaries.
            large_fields = ["edited_script", "strategy_plan", "script", "selected_idea"]
            for field in large_fields:
                val = state.get(field)
                if val:
                    if isinstance(val, str):
                        state[field] = truncate_text(val, 3000) # Increased budget for semantic head/tail
                    elif isinstance(val, dict):
                        # Truncate large string values within dicts (e.g. 'full_script')
                        for k, v in val.items():
                            if isinstance(v, str) and len(v) > 2000:
                                val[k] = truncate_text(v, 2000)
                    elif isinstance(val, list):
                        # Keep only first 2 items of large lists (ideas, hooks)
                        if len(val) > 2:
                            state[field] = val[:2]
            
            # Pruning Step 3: Clear transient stream events
            state["stream_events"] = []
            
            # Final Check
            new_size_kb = len(json.dumps(state).encode('utf-8')) / 1024
            if new_size_kb > settings.state_max_size_kb:
                logger.error(f"State Sentinel: State still too large ({new_size_kb:.2f}KB). Terminating.")
                errors = state.get("errors", [])
                errors.append("unrecoverable: state_too_large - exceeds limit even after truncation.")
                return {**state, "errors": errors, "should_terminate": True}
                
    except Exception as e:
        logger.error(f"State Sentinel check failed: {e}")
        
    return {
        **state,
        "current_stage": "state_sentinel"
    }


async def save_results_node(state: PipelineState) -> PipelineState:
    """Persist final outputs to project and user memory."""
    memory = MemoryService()

    try:
        # Save final script as project artifact
        if state.get("edited_script"):
            await memory.save_project_artifact(
                state.get("project_id", ""),
                state.get("thread_id", ""),
                "final_output",
                {
                    "edited_script": state["edited_script"],
                    "strategy_plan": state.get("strategy_plan"),
                    "total_cost_cents": state.get("total_cost_cents", 0),
                },
                user_id=state.get("user_id", ""),
            )
    except Exception as e:
        logger.warning("save_results: failed — %s", e)

    return {
        **state,
        "current_stage": "save_results",
        "completed_stages": state.get("completed_stages", []) + ["save_results"],
        "should_terminate": True,
    }


async def error_handler_node(state: PipelineState) -> PipelineState:
    """Handle errors and classify as recoverable vs unrecoverable."""
    errors = state.get("errors", [])
    last_error = errors[-1] if errors else "Unknown error"

    # Classify error
    unrecoverable_patterns = [
        "invalid_api_key", "authentication", "unauthorized",
        "quota_exceeded", "billing",
    ]
    is_unrecoverable = any(p in str(last_error).lower() for p in unrecoverable_patterns)

    if is_unrecoverable:
        return {
            **state,
            "should_terminate": True,
            "current_stage": "error",
        }

    return {
        **state,
        "current_stage": "error_recovery",
    }


async def detect_edits_node(state: PipelineState) -> PipelineState:
    """Detect writing style and tone preferences from manual user edits."""
    user_id = state.get("user_id", "")
    current_content = state.get("user_edited_content")
    stage = state.get("current_stage", "")
    
    # Identify which block we are editing
    block_type = "script"
    if "structure" in stage:
        block_type = "structure"
    elif "hook" in stage:
        block_type = "hook"

    if current_content:
        memory = MemoryService()
        # Find original content to compare
        original = ""
        if block_type == "script":
            orig_obj = state.get("script") or state.get("edited_script") or {}
            original = orig_obj.get("full_script", "") if isinstance(orig_obj, dict) else str(orig_obj)
        elif block_type == "structure":
            orig_obj = state.get("structure_guidance") or {}
            original = orig_obj.get("outline", "") if isinstance(orig_obj, dict) else str(orig_obj)

        if original and original != current_content:
            # Analyze user edit and extract preference signals
            await memory.record_edit(user_id, state.get("project_id", ""), stage, original, current_content)

    return {
        **state,
        "current_stage": "detect_edits",
    }


# ── Tier 2 Nodes ──────────────────────────────────────────────────


async def summarize_context_node(state: PipelineState) -> PipelineState:
    """Summarize the previous stage and prune raw context."""
    cm = get_context_manager()
    stage = state.get("current_stage", "unknown")
    
    # Identify what to summarize
    content_map = {
        "idea_ranking": state.get("ideas"),
        "hook_evaluation": state.get("hooks"),
        "fact_checking": state.get("script"),
        "final_review": state.get("edited_script")
    }
    
    content = content_map.get(stage)
    if content:
        summary = await cm.summarize_stage(stage, content)
        comp_state = state.get("compressed_state") or {}
        comp_state[stage] = summary
        state["compressed_state"] = comp_state
        
    # Prune state
    state = cm.prune_state(state, stage)
    return state


async def evaluate_node(state: PipelineState) -> PipelineState:
    """Systematically evaluate the output of the current stage."""
    evaluator = EvaluatorAgent(user_context=state.get("project_context"))
    stage = state.get("current_stage", "unknown")
    
    # Identify content to evaluate (Aligned with atomic node output keys)
    content_map = {
        "idea_generation": state.get("raw_ideas"),
        "idea_ranking": state.get("ideas"),
        "hook_creation": state.get("raw_hooks"),
        "hook_evaluation": state.get("hooks"),
        "script_drafting": state.get("raw_script"),
        "fact_checking": state.get("script"),
        "final_review": state.get("edited_script"),
    }
    
    content = content_map.get(stage)
    if not content:
        return state
        
    res = await evaluator.execute({
        "output_content": str(content),
        "stage_name": stage,
        "project_context": state.get("project_context")
    })
    
    scores = state.get("evaluator_scores") or {}
    scores[stage] = res.get("score", 0.5)
    
    return {
        **state,
        "evaluator_scores": scores,
        "last_evaluation": res
    }


# ── Process nodes (HITL interrupt points) ────────────────────────


def _make_process_node(stage_name: str):
    """Factory to create identical HITL processing nodes for each stage."""

    async def process_node(state: PipelineState) -> PipelineState:
        action = state.get("user_action", "approve")

        if action == "edit":
            # Update the relevant output with user's edited content
            edited = state.get("user_edited_content")
            if edited and stage_name == "idea_selection":
                state["selected_idea"] = edited
            elif edited and stage_name == "hook_selection":
                state["selected_hook"] = edited

        elif action == "approve":
            # Auto-select best item if none explicitly selected
            if stage_name == "idea_selection" and not state.get("selected_idea"):
                ideas = state.get("ideas", [])
                if ideas:
                    state["selected_idea"] = ideas[0]
            elif stage_name == "hook_selection" and not state.get("selected_hook"):
                hooks = state.get("hooks", [])
                if hooks:
                    state["selected_hook"] = hooks[0]

        elif action == "skip":
            state["should_terminate"] = True

        # Preserve action for router, then clear for next stage
        return {
            **state,
            "_last_action": action,
            "user_action": None,
            "user_edited_content": None,
            "current_stage": stage_name,
        }

    process_node.__name__ = f"process_{stage_name}"
    return process_node


# Create process nodes
process_idea_selection = _make_process_node("idea_selection")
process_hook_selection = _make_process_node("hook_selection")
process_script_edit = _make_process_node("script_edit")
process_structure_edit = _make_process_node("structure_edit")
process_final_review = _make_process_node("final_review")
process_strategy_approval = _make_process_node("strategy_approval")


# ── HITL Logic ──────────────────────────────────────────────────

def should_interrupt(state: PipelineState, stage_name: str) -> bool:
    """
    Decide if the pipeline should interrupt for user input.
    
    Rules:
    1. Manual Mode: Always interrupt at every stage.
    2. Guided Mode: Interrupt only at 'idea_selection' and 'final_review'.
    3. Auto Mode: Never interrupt unless confidence is dangerously low (< 0.4).
    4. Confidence: If stage confidence > 0.85, skip interrupt in Guided/Auto.
    """
    mode = state.get("execution_mode", "auto")
    confidence = state.get("node_confidence", {}).get(stage_name, 1.0)
    
    if mode == "manual":
        return True
    
    if confidence < 0.4:
        return True
    
    if mode == "guided":
        return stage_name in ["idea_selection", "final_review"] and confidence < 0.85
    
    if mode == "auto":
        return False
        
    return True


async def auto_approve_node(state: PipelineState) -> PipelineState:
    """Automatically perform the 'approve' action for the current stage."""
    stage = state.get("current_stage", "")
    
    # Logic mirrors _make_process_node's 'approve' case
    if "idea_discovery" in stage or stage == "idea_selection":
        if not state.get("selected_idea"):
            ideas = state.get("ideas", [])
            state["selected_idea"] = ideas[0] if ideas else None
    elif "hook_generation" in stage or stage == "hook_selection":
        if not state.get("selected_hook"):
            hooks = state.get("hooks", [])
            state["selected_hook"] = hooks[0] if hooks else None
            
    return {
        **state,
        "_last_action": "approve",
        "user_action": None,
        "current_stage": f"{stage}_auto",
    }


# ── Routing functions ────────────────────────────────────────────

# ── Stage 1: Ideas (Atomic) ───────────────

def route_after_trend_research(state: PipelineState) -> str:
    return "idea_generation"


def route_after_idea_generation(state: PipelineState) -> str:
    return "idea_ranking"

def route_after_evaluation(state: PipelineState) -> str:
    """Feedback loop: route back if quality is too low in Auto mode."""
    stage = state.get("current_stage", "")
    score = state.get("evaluator_scores", {}).get(stage, 10.0)
    mode = state.get("execution_mode", "auto")
    
    # Auto-regeneration logic (Tier 2 requirement)
    if score < 4.0 and mode == "auto":
        # Check if we already retried this stage once to avoid infinite loops
        metadata = state.get("context_metadata", {})
        retries = metadata.get("auto_retries", {})
        count = retries.get(stage, 0)
        
        if count < 1:
            logger.warning(f"Quality too low ({score}) for {stage}. Triggering auto-regeneration.")
            retries[stage] = count + 1
            state["context_metadata"]["auto_retries"] = retries
            return stage  # Route back to the node that generated the output
            
    # Success (> 4.0) or Manual mode — Move to summarization then to next step
    # We return 'summarize_context' as the next node. 
    # summarize_context will then use ITS router to find the next stage node.
    return "summarize_context"


def route_after_idea_ranking(state: PipelineState) -> str:
    return "evaluate"


def route_after_idea_summarize(state: PipelineState) -> str:
    if should_interrupt(state, "idea_selection"):
        return "process_idea_selection"
    return "auto_approve_ideas"


def route_after_idea_selection(state: PipelineState) -> str:
    action = state.get("_last_action")
    if action == "regenerate":
        return "trend_research"
    if state.get("errors"):
        return "error_handler"
    return "hook_creation"


# ── Stage 2: Hooks (Atomic) ───────────────

def route_after_hook_creation(state: PipelineState) -> str:
    return "hook_evaluation"


def route_after_hook_evaluation(state: PipelineState) -> str:
    return "evaluate"


def route_after_hook_summarize(state: PipelineState) -> str:
    if should_interrupt(state, "hook_selection"):
        return "process_hook_selection"
    return "auto_approve_hooks"


def route_after_hook_selection(state: PipelineState) -> str:
    action = state.get("_last_action")
    if action == "regenerate":
        return "hook_creation"
    if state.get("errors"):
        return "error_handler"
    return "deep_research"


def route_after_deep_research(state: PipelineState) -> str:
    if state.get("shadow_hit"):
        return "fact_checking"
    return "script_drafting"


def route_after_validation(state: PipelineState) -> str:
    if state.get("should_terminate"):
        return "error_handler"
    return "trend_research"


def route_after_script_drafting(state: PipelineState) -> str:
    return "fact_checking"


def route_after_fact_checking(state: PipelineState) -> str:
    return "evaluate"


def route_after_script_summarize(state: PipelineState) -> str:
    """Route after script writing, considering platform and HITL."""
    platform = state.get("project_context", {}).get("platform", "YouTube").lower()
    
    # HITL check
    if should_interrupt(state, "script_edit"):
        return "process_script_edit"
    
    # Path branching based on platform
    if platform == "linkedin":
        return "series_planning"  # LinkedIn skips structure and editing
    if platform == "tiktok":
        return "line_editing"    # TikTok skips structure guidance
        
    return "structure_analysis"


def route_after_script_edit(state: PipelineState) -> str:
    action = state.get("_last_action")
    if action == "regenerate":
        return "script_writing_group"
    if action == "edit":
        return "detect_edits"
    if state.get("errors"):
        return "error_handler"
        
    # Same platform logic as above
    platform = state.get("project_context", {}).get("platform", "YouTube").lower()
    if platform == "linkedin":
        return "strategy_group"
    if platform == "tiktok":
        return "editing_group"
        
    return "structure_group"


# ── Stage 4: Structure (Atomic) ───────────

def route_after_structure_analysis(state: PipelineState) -> str:
    return "pacing_optimization"


def route_after_pacing_optimization(state: PipelineState) -> str:
    if should_interrupt(state, "structure_edit"):
        return "process_structure_edit"
    return "line_editing"


def route_after_structure_edit(state: PipelineState) -> str:
    action = state.get("_last_action")
    if action == "regenerate":
        return "structure_analysis"
    if action == "edit":
        return "detect_edits"
    if state.get("errors"):
        return "error_handler"
    return "line_editing"


# ── Stage 5: Editing (Atomic) ─────────────

def route_after_line_editing(state: PipelineState) -> str:
    return "engagement_boosting"


def route_after_engagement_boosting(state: PipelineState) -> str:
    return "final_review"


def route_after_final_review(state: PipelineState) -> str:
    # Tier 2 requirement: Evaluate the final script
    return "evaluate"


def route_after_final_review_summarize(state: PipelineState) -> str:
    """Corrected router for final review summarization with HITL."""
    if should_interrupt(state, "final_review"):
        return "process_final_review"
    return "series_planning"


def route_after_final_review_hitl(state: PipelineState) -> str:
    action = state.get("_last_action")
    if action == "regenerate":
        return "line_editing"
    if action == "edit":
        return "detect_edits"
    if action == "skip" or state.get("should_terminate"):
        return "save_results"
    if state.get("errors"):
        return "error_handler"
    return "series_planning"


# ── Stage 6: Strategy (Atomic) ────────────

def route_after_series_planning(state: PipelineState) -> str:
    return "growth_advisory"


def route_after_growth_advisory(state: PipelineState) -> str:
    if should_interrupt(state, "strategy_approval"):
        return "process_strategy_approval"
    return "save_results"


def route_after_strategy_approval(state: PipelineState) -> str:
    action = state.get("_last_action")
    if action == "regenerate":
        return "series_planning"
    if state.get("errors"):
        return "error_handler"
    return "save_results"


def route_after_detect_edits(state: PipelineState) -> str:
    """Route to the correct next stage after edit detection."""
    stage = state.get("current_stage", "")
    platform = state.get("project_context", {}).get("platform", "YouTube").lower()
    
    if "script" in stage:
        if platform == "linkedin": return "series_planning"
        if platform == "tiktok": return "line_editing"
        return "structure_analysis"
    
    if "structure" in stage:
        return "line_editing"
        
    return "series_planning"


def route_summarize(state: PipelineState) -> str:
    """Consolidated router for all summarization paths."""
    stage = state.get("current_stage", "unknown")
    
    if stage == "idea_ranking":
        return route_after_idea_summarize(state)
    if stage == "hook_evaluation":
        return route_after_hook_summarize(state)
    if stage == "fact_checking":
        return route_after_script_summarize(state)
    if stage == "final_review":
        return route_after_final_review_summarize(state)
        
    return "save_results" # Safe fallback


def route_error(state: PipelineState) -> str:
    if state.get("should_terminate"):
        return END
    # Route back to the last failed stage
    current = state.get("current_stage", "")
    stage_node_map = {
        "idea_discovery": "idea_discovery_group",
        "hook_generation": "hook_generation_group",
        "script_writing": "script_writing_group",
        "structure": "structure_group",
        "editing": "editing_group",
        "strategy": "strategy_group",
    }
    return stage_node_map.get(current, END)


# ── Graph builder ────────────────────────────────────────────────


def build_graph() -> StateGraph:
    """Build and return the uncompiled LangGraph StateGraph."""
    # 1. Initialize Graph
    graph = StateGraph(PipelineState)

    # Core Utility Nodes
    graph.add_node("load_memory", budget_guard(load_memory_node))
    graph.add_node("validate_inputs", budget_guard(validate_inputs_node))
    graph.add_node("save_results", budget_guard(save_results_node))
    graph.add_node("error_handler", budget_guard(error_handler_node))
    graph.add_node("detect_edits", budget_guard(detect_edits_node))
    graph.add_node("state_sentinel", budget_guard(state_sentinel_node))
    
    # Tier 2 Utility Nodes
    graph.add_node("evaluate", budget_guard(evaluate_node))
    graph.add_node("summarize_context", budget_guard(summarize_context_node))

    # Stage 1: Ideas
    graph.add_node("trend_research", budget_guard(trend_research_node))
    graph.add_node("idea_generation", budget_guard(idea_generation_node))
    graph.add_node("idea_ranking", budget_guard(idea_ranking_node))
    graph.add_node("auto_approve_ideas", budget_guard(auto_approve_node))
    graph.add_node("process_idea_selection", budget_guard(process_idea_selection))

    # Stage 2: Hooks
    graph.add_node("hook_creation", budget_guard(hook_creation_node))
    graph.add_node("hook_evaluation", budget_guard(hook_evaluation_node))
    graph.add_node("auto_approve_hooks", budget_guard(auto_approve_node))
    graph.add_node("process_hook_selection", budget_guard(process_hook_selection))

    # Stage 3: Script
    graph.add_node("deep_research", budget_guard(deep_research_node))
    graph.add_node("script_drafting", budget_guard(script_drafting_node))
    graph.add_node("fact_checking", budget_guard(fact_checking_node))
    graph.add_node("process_script_edit", budget_guard(process_script_edit))

    # Stage 4: Structure
    graph.add_node("structure_analysis", budget_guard(structure_analysis_node))
    graph.add_node("pacing_optimization", budget_guard(pacing_optimization_node))
    graph.add_node("process_structure_edit", budget_guard(process_structure_edit))

    # Stage 5: Editing
    graph.add_node("line_editing", budget_guard(line_editing_node))
    graph.add_node("engagement_boosting", budget_guard(engagement_boosting_node))
    graph.add_node("final_review", budget_guard(final_review_node))
    graph.add_node("process_final_review", budget_guard(process_final_review))

    # Stage 6: Strategy
    graph.add_node("series_planning", budget_guard(series_planning_node))
    graph.add_node("growth_advisory", budget_guard(growth_advisory_node))
    graph.add_node("process_strategy_approval", budget_guard(process_strategy_approval))

    # ── Edges ──────────────────────────────────────────────────

    graph.set_entry_point("load_memory")
    graph.add_edge("load_memory", "validate_inputs")
    graph.add_conditional_edges("validate_inputs", route_after_validation)
    
    # Final check before saving
    graph.add_edge("save_results", END) # This is already there further down, I'll move sentinel before it
    
    # Tier 2 evaluation router (shared)
    graph.add_conditional_edges("evaluate", route_after_evaluation)
    
    # Stage 1-2
    graph.add_conditional_edges("trend_research", route_after_trend_research)
    graph.add_conditional_edges("idea_generation", route_after_idea_generation)
    graph.add_conditional_edges("idea_ranking", route_after_idea_ranking)

    # Granular summarize routing
    graph.add_conditional_edges("summarize_context", route_summarize)

    graph.add_edge("auto_approve_ideas", "hook_creation")
    graph.add_conditional_edges("process_idea_selection", route_after_idea_selection)

    graph.add_conditional_edges("hook_creation", route_after_hook_creation)
    graph.add_conditional_edges("hook_evaluation", route_after_hook_evaluation)
    graph.add_edge("auto_approve_hooks", "deep_research")
    graph.add_conditional_edges("process_hook_selection", route_after_hook_selection)

    # Stage 3-6
    graph.add_conditional_edges("deep_research", route_after_deep_research)
    graph.add_conditional_edges("script_drafting", route_after_script_drafting)
    graph.add_conditional_edges("fact_checking", route_after_fact_checking)
    graph.add_conditional_edges("process_script_edit", route_after_script_edit)

    graph.add_conditional_edges("structure_analysis", route_after_structure_analysis)
    graph.add_conditional_edges("pacing_optimization", route_after_pacing_optimization)
    graph.add_conditional_edges("process_structure_edit", route_after_structure_edit)

    graph.add_conditional_edges("line_editing", route_after_line_editing)
    graph.add_conditional_edges("engagement_boosting", route_after_engagement_boosting)
    graph.add_conditional_edges("final_review", route_after_final_review)
    graph.add_conditional_edges("process_final_review", route_after_final_review_hitl)

    graph.add_conditional_edges("series_planning", route_after_series_planning)
    graph.add_conditional_edges("growth_advisory", route_after_growth_advisory)
    graph.add_conditional_edges("process_strategy_approval", route_after_strategy_approval)

    graph.add_conditional_edges("detect_edits", route_after_detect_edits)
    
    # State Sentinel injection before saving results
    graph.add_edge("growth_advisory", "state_sentinel")
    graph.add_edge("state_sentinel", "save_results")
    
    graph.add_edge("save_results", END)
    graph.add_conditional_edges("error_handler", route_error)

    return graph


def get_compiled_graph():
    """Build, compile, and return the pipeline graph with checkpointing."""
    graph = build_graph()
    checkpointer = MongoDBCheckpointer()

    compiled = graph.compile(
        interrupt_before=[
            "process_idea_selection",
            "process_hook_selection",
            "process_script_edit",
            "process_structure_edit",
            "process_final_review",
            "process_strategy_approval",
        ],
        checkpointer=checkpointer,
    )

    logger.info("Pipeline graph compiled with dynamic HITL and Platform-aware routing")
    return compiled


# Module-level singleton
_compiled_graph = None


def get_graph():
    """Get the singleton compiled graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = get_compiled_graph()
    return _compiled_graph

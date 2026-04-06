"""
Context Manager — Tier 2 Efficiency Layer.

Handles:
- Stage-level summarization (context compression)
- State pruning (sliding window for raw data)
- Context budget enforcement
"""

import logging
from typing import Any, Dict, List, Optional
from app.llm.router import get_llm_router
from app.llm.base import LLMMessage

logger = logging.getLogger(__name__)

# Max tokens allowed for a stage summary
SUMMARY_BUDGET = 500

class ContextManager:
    """Manages the lifecycle of PipelineState context to prevent bloat."""

    def __init__(self):
        self.router = get_llm_router()

    async def summarize_stage(self, stage_name: str, raw_data: Any) -> str:
        """Generate a concise summary of a completed stage's output."""
        if not raw_data:
            return ""

        prompt = f"""
        Summarize the following AI output from the stage '{stage_name}'.
        Keep it under 150 words. Focus on:
        1. Key decisions made.
        2. Important constraints or facts discovered.
        3. Core content snippets (e.g. the selected idea/hook).
        
        Raw Data:
        {str(raw_data)[:4000]}  # Truncate if extreme
        """

        messages = [
            LLMMessage(role="system", content="You are a context compression assistant. Be concise and precise."),
            LLMMessage(role="user", content=prompt),
        ]

        try:
            response = await self.router.generate(messages, task_type="fast")
            return response.content.strip()
        except Exception as e:
            logger.error(f"summarize_stage failed: {e}")
            return f"[Error summarizing {stage_name}]"

    def prune_state(self, state: Dict[str, Any], current_stage: str) -> Dict[str, Any]:
        """
        Prunes raw data from the state based on a sliding window.
        Keeps the 'Essential Context' and the 'Immediate Previous' raw stage.
        """
        # Stages in order
        stages = [
            "trend_research", "idea_generation", "idea_ranking",
            "hook_creation", "hook_evaluation",
            "structure_analysis", "pacing_optimization",
            "line_editing", "engagement_boosting", "final_review",
            "series_planning", "growth_advisory"
        ]
        
        try:
            idx = stages.index(current_stage)
        except ValueError:
            return state

        # Define what to keep raw (current + 1 back)
        keep_raw = set(stages[max(0, idx-1) : idx+1])
        
        # Mapping of stage names to state keys
        stage_to_key = {
            "trend_research": "research_results",
            "idea_generation": "raw_ideas",
            "idea_ranking": "ideas",
            "hook_creation": "raw_hooks",
            "hook_evaluation": "hooks",
            "script_drafting": "raw_script",
            "fact_checking": "script",
            "structure_analysis": "structure_analysis", # pipeline state currently uses structure_guidance for pacing
            "pacing_optimization": "structure_guidance",
            "line_editing": "edited_script",
            "engagement_boosting": "edited_script",
            "final_review": "edited_script",
            "series_planning": "strategy_plan",
            "growth_advisory": "strategy_plan"
        }

        updates = {}
        pruned_logs = state.get("context_metadata", {}).get("pruned_logs", [])

        # PROTECTED KEYS (NEVER PRUNE)
        protected_keys = {"project_context", "user_preferences", "user_id", "project_id", "job_id", "execution_mode"}

        for stage, key in stage_to_key.items():
            if key in protected_keys:
                continue
                
            if stage not in keep_raw and state.get(key):
                # Check if we have a summary before deleting
                comp_state = state.get("compressed_state", {})
                if stage in comp_state:
                    logger.info(f"ContextManager: Pruning raw data for {stage} (key: {key})")
                    updates[key] = None  # Prune raw data
                    pruned_logs.append({"stage": stage, "key": key, "timestamp": "now"})
        
        if updates:
            state.update(updates)
            state["context_metadata"] = {
                **state.get("context_metadata", {}),
                "pruned_logs": pruned_logs[-10:] # Keep last 10
            }
            
        return state

def get_context_manager():
    return ContextManager()

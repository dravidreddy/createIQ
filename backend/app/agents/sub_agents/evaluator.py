"""
EvaluatorAgent — Tier 2 Quality Control Layer.

Scores agent outputs for:
- Clarity
- Engagement
- Platform-Fit (LinkedIn, TikTok, YouTube)
- Audience-Fit
"""

import logging
from typing import Any, Dict, List
from app.agents.base_executor import BaseAgentExecutor, Priority
from app.llm.base import LLMMessage
from app.utils.json_parser import parse_llm_json
from app.utils.prompt_loader import load_system_prompt, load_user_prompt

logger = logging.getLogger(__name__)

class EvaluatorAgent(BaseAgentExecutor):
    """Systematic evaluator for pipeline stage quality."""

    @property
    def name(self) -> str:
        return "EvaluatorAgent"

    @property
    def description(self) -> str:
        return "Scores AI outputs for quality and platform fit"

    @property
    def priority(self) -> Priority:
        return Priority.HIGH

    async def execute_core(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate an AI output against its target platform and niche.
        
        Input:
            output_content: The text/data to evaluate.
            stage_name: The name of the stage being evaluated.
            project_context: The project-level configuration.
        """
        content = input_data.get("output_content", "")
        stage = input_data.get("stage_name", "unknown")
        project_ctx = input_data.get("project_context", {})
        
        if not content:
            return {"score": 0.0, "reasoning": "No content provided."}

        system_prompt = load_system_prompt(
            "evaluator",
            platform=project_ctx.get("platform", "YouTube"),
            stage_name=stage,
        )
        
        user_prompt = load_user_prompt(
            "evaluator",
            content=content,
            niche=project_ctx.get("niche", "general"),
            target_audience=project_ctx.get("target_audience", "general"),
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        # Use quality (smartest) model for evaluation — critical for reliability
        # [V4 UPDATE] Hardened with model override and non-critical error handling
        try:
            response = await self.llm_generate(
                messages, 
                task_type="quality", 
                temperature=0.1,
                model_override="gemini-1.5-flash"
            )
            result = parse_llm_json(response.content, fallback={"score": 0.5, "reasoning": "Parse failed"})
        except Exception as e:
            logger.error(f"EvaluatorAgent: non-critical failure during evaluation: {e}")
            result = {"score": 0.5, "reasoning": f"Evaluation error: {str(e)}"}
        
        self.log(f"Evaluation for '{stage}': Score={result.get('score')} Reasoning={result.get('reasoning')[:100]}...")
        
        return result

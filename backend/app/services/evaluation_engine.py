"""
Evaluation Engine — Bounded refinement loop with fast + deep scoring.

Strategy:
  1. Fast score each variant using an LLM-lite call (Gemini Flash / GPT-4o-mini).
  2. If the best score is below the quality threshold, invoke a deep LLM refinement.
  3. Repeat at most MAX_EVAL_ITER times (default 2).
  4. Return the final variant set with scores, or flag as "degraded" if
     the threshold was never met.

The fast scorer is a lightweight prompt asking for a 0-1 quality score.
When a custom ML model is trained (Phase 2), it replaces this prompt.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.llm.router import get_llm_router
from app.llm.base import LLMMessage

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Data Structures ────────────────────────────────────────────

@dataclass
class EvalResult:
    variant_id: str
    content: str
    fast_score: float = 0.0
    deep_refined: bool = False
    iteration: int = 0


@dataclass
class EvalOutcome:
    variants: List[EvalResult] = field(default_factory=list)
    best_score: float = 0.0
    iterations_used: int = 0
    degraded: bool = False


# ─── Fast Scoring (LLM-lite) ───────────────────────────────────

FAST_SCORE_PROMPT = """You are a content quality evaluator. Rate the following content on a scale of 0.0 to 1.0 across these dimensions:
- hook_strength: How compelling is the opening hook?
- clarity: How clear and well-structured is the content?
- engagement: How likely is this to retain viewer attention?

Content:
\"\"\"
{content}
\"\"\"

Respond with ONLY a JSON object:
{{"hook_strength": 0.0, "clarity": 0.0, "engagement": 0.0, "overall": 0.0}}"""


async def fast_score(content: str) -> float:
    """Return a 0-1 quality score using an LLM-lite call."""
    router = get_llm_router()
    try:
        messages = [
            LLMMessage(role="user", content=FAST_SCORE_PROMPT.format(content=content[:2000]))
        ]
        response = await router.generate(messages, task_type="scoring", temperature=0.0, max_tokens=200)
        # Try to parse the overall score from the JSON response
        import json
        import re
        text = response.content.strip()
        try:
            # Force extract anything enclosed in braces, regardless of conversational fluff
            match = re.search(r'(\{.*\})', text, re.DOTALL)
            if not match:
                raise ValueError("No JSON object found in response.")
            data = json.loads(match.group(1))
            return float(data.get("overall", 0.0))
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("evaluation_engine: fast_score failed parsing — %s | Raw: %s", e, text)
            return 0.5  # neutral fallback
    except Exception as e:
        logger.warning("evaluation_engine: fast_score failed completely — %s", e)
        return 0.5  # neutral fallback


# ─── Deep Refinement (Full LLM) ────────────────────────────────

REFINE_PROMPT = """You are an expert content editor. The following content scored {score:.2f}/1.0 on quality.

Content:
\"\"\"
{content}
\"\"\"

Improve this content to score above {threshold}. Focus on:
1. Making the hook more compelling and attention-grabbing
2. Improving clarity and structure
3. Increasing engagement and viewer retention

Return ONLY the improved content, nothing else."""


async def deep_refine(content: str, current_score: float) -> str:
    """Use a full LLM call to refine content that failed the quality threshold."""
    router = get_llm_router()
    try:
        messages = [
            LLMMessage(
                role="user",
                content=REFINE_PROMPT.format(
                    content=content[:4000],
                    score=current_score,
                    threshold=settings.eval_quality_threshold,
                ),
            )
        ]
        response = await router.generate(messages, task_type="quality", temperature=0.4, max_tokens=4096)
        return response.content.strip()
    except Exception as e:
        logger.warning("evaluation_engine: deep_refine failed — %s", e)
        return content  # return original on failure


# ─── Evaluation Loop Controller ─────────────────────────────────

async def evaluate_variants(
    variants: List[Dict[str, Any]],
) -> EvalOutcome:
    """Run the bounded evaluation loop on a list of variant dicts.

    Each variant dict should have::

        {"variant_id": "...", "content": "..."}

    Returns an :class:`EvalOutcome` with scored (and possibly refined) variants.
    """

    max_iter = settings.eval_max_iterations
    threshold = settings.eval_quality_threshold
    outcome = EvalOutcome()

    # Build initial EvalResult objects
    results: List[EvalResult] = [
        EvalResult(variant_id=v["variant_id"], content=v["content"])
        for v in variants
    ]

    for iteration in range(1, max_iter + 1):
        # Score all variants
        for r in results:
            r.fast_score = await fast_score(r.content)
            r.iteration = iteration

        best = max(results, key=lambda r: r.fast_score)
        outcome.best_score = best.fast_score
        outcome.iterations_used = iteration

        logger.info(
            "evaluation_engine: iter %d — best score %.3f (threshold %.2f)",
            iteration, best.fast_score, threshold,
        )

        if best.fast_score >= threshold:
            break  # Good enough

        # Refine the worst-scoring variants
        if iteration < max_iter:
            for r in results:
                if r.fast_score < threshold:
                    r.content = await deep_refine(r.content, r.fast_score)
                    r.deep_refined = True

    # If we exhausted iterations without meeting threshold, flag as degraded
    if outcome.best_score < threshold:
        outcome.degraded = True
        logger.warning(
            "evaluation_engine: quality threshold not met after %d iterations (best=%.3f)",
            max_iter, outcome.best_score,
        )

    outcome.variants = results
    return outcome

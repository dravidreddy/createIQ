"""
Budget Enforcer — Pre-flight estimation + runtime cost guard + adaptive degradation.

Main entry points:
  - estimate_cost(steps, model_tier)  → CostEstimate
  - check_and_deduct(job_id, cost)    → bool (allowed?)
  - degrade(remaining_cents, ...)     → DegradedConfig

The runtime guard is designed for atomic Redis Lua execution.
When Redis is unavailable it falls back to a DB-based check (MongoDB/Beanie).
"""

from app.utils.datetime_utils import utc_now
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

from app.config import get_settings
from app.models.budget_allocation import BudgetAllocation
from app.models.job_metrics import JobMetrics

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Cost table (cents per 1 K tokens) ──────────────────────────

COST_TABLE = {
    "flash": {
        "input": settings.cost_per_1k_input_flash,
        "output": settings.cost_per_1k_output_flash,
    },
    "pro": {
        "input": settings.cost_per_1k_input_pro,
        "output": settings.cost_per_1k_output_pro,
    },
}


# ─── Data Structures ────────────────────────────────────────────

@dataclass
class StepEstimate:
    step: str
    model_tier: str              # "flash" | "pro"
    est_input_tokens: int
    est_output_tokens: int

    @property
    def cost_cents(self) -> float:
        tier = COST_TABLE.get(self.model_tier, COST_TABLE["flash"])
        return (
            (self.est_input_tokens / 1000) * tier["input"]
            + (self.est_output_tokens / 1000) * tier["output"]
        )


@dataclass
class CostEstimate:
    steps: List[StepEstimate] = field(default_factory=list)

    @property
    def total_cents(self) -> float:
        return sum(s.cost_cents for s in self.steps)

    @property
    def within_budget(self) -> bool:
        return self.total_cents <= settings.budget_default_per_job_cents


@dataclass
class DegradedConfig:
    """Config returned when a job must be degraded to stay within budget."""
    model_tier: str = "flash"
    variant_count: int = 1
    context_truncation_pct: float = 50.0  # keep only top 50 %
    reason: str = ""


# ─── Pre-flight Estimation ──────────────────────────────────────

def estimate_cost(
    steps: List[Dict],
    model_tier: str = "pro",
) -> CostEstimate:
    """Estimate the total cost of a job given its planned steps.

    Each step dict should have::

        {"name": "research", "est_input_tokens": 2000, "est_output_tokens": 800}

    Missing token counts default to conservative estimates.
    """
    estimates = []
    for s in steps:
        estimates.append(
            StepEstimate(
                step=s.get("name", "unknown"),
                model_tier=model_tier,
                est_input_tokens=s.get("est_input_tokens", 1500),
                est_output_tokens=s.get("est_output_tokens", 500),
            )
        )
    return CostEstimate(steps=estimates)


# ─── Runtime Guard (DB fallback) ────────────────────────────────

async def check_and_deduct(
    job_id: str,
    step_name: str,
    actual_cost_cents: float,
) -> bool:
    """Deduct *actual_cost_cents* from the remaining budget of *job_id*.

    Returns ``True`` if the deduction was allowed, ``False`` if budget is exhausted.
    In production, this should be an atomic Redis Lua script.
    """
    alloc: Optional[BudgetAllocation] = await BudgetAllocation.find_one(
        BudgetAllocation.job_id == job_id
    )

    if alloc is None:
        # Auto-create with default budget
        alloc = BudgetAllocation(
            job_id=job_id,
            remaining=float(settings.budget_default_per_job_cents),
            step_costs={},
        )
        await alloc.insert()

    if alloc.remaining < actual_cost_cents:
        logger.warning("budget_enforcer: budget exceeded for job %s", job_id)
        # Record in job_metrics
        await _mark_budget_exceeded(job_id)
        return False

    alloc.remaining = float(alloc.remaining - actual_cost_cents)
    costs = dict(alloc.step_costs) if alloc.step_costs else {}
    costs[step_name] = costs.get(step_name, 0) + actual_cost_cents
    alloc.step_costs = costs
    alloc.updated_at = utc_now()
    await alloc.save()
    return True


# ─── Degradation API ────────────────────────────────────────────

def degrade(remaining_cents: float, current_variant_count: int) -> DegradedConfig:
    """Return a DegradedConfig that fits within *remaining_cents*."""

    if remaining_cents <= 0:
        return DegradedConfig(
            model_tier="flash",
            variant_count=1,
            context_truncation_pct=30.0,
            reason="Budget exhausted — minimum viable execution",
        )

    # Switch to flash and reduce variants
    new_variants = max(1, current_variant_count // 2)
    return DegradedConfig(
        model_tier="flash",
        variant_count=new_variants,
        context_truncation_pct=50.0,
        reason=f"Budget low ({remaining_cents:.1f}¢ remaining) — degraded mode",
    )


# ─── Helpers ─────────────────────────────────────────────────────

async def _mark_budget_exceeded(job_id: str) -> None:
    row: Optional[JobMetrics] = await JobMetrics.find_one(
        JobMetrics.job_id == job_id
    )
    if row is None:
        row = JobMetrics(job_id=job_id, budget_exceeded=True)
        await row.insert()
    else:
        row.budget_exceeded = True
        row.updated_at = utc_now()
        await row.save()

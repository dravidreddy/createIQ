"""
Budget Allocation Document — MongoDB / Beanie

Per-job budget tracking for the V3.3 cost enforcement engine.
"""

from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class BudgetAllocation(Document):
    """Tracks remaining budget and step-level costs for a single job."""

    job_id: Indexed(str, unique=True)  # type: ignore[valid-type]

    remaining: float = 0.0  # cents remaining
    step_costs: dict = Field(default_factory=dict)  # {step_name: cost_cents}

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "budget_allocations"
        use_state_management = True

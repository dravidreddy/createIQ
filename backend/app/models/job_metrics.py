"""
Job Metrics Document — MongoDB / Beanie

Operational metrics for job execution (budget exceeded flags, timing, etc.).
"""

from datetime import datetime

from beanie import Document, Indexed
from pydantic import Field


class JobMetrics(Document):
    """Operational metrics for a single job execution."""

    job_id: Indexed(str, unique=True)  # type: ignore[valid-type]

    budget_exceeded: bool = False
    total_cost_cents: float = 0.0
    total_latency_ms: int = 0
    variant_count: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "job_metrics"
        use_state_management = True

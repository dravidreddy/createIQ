"""
V3.3 API Routes — State, Simulation, and Metrics endpoints (MongoDB/Beanie).

All endpoints are gated behind the `v3_3_enabled` feature flag.
project_id is now a string (ObjectId). db: AsyncSession removed.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.config import get_settings
from app.models.user import User
from app.api.deps import get_current_user
from app.services import state_service
from app.services.budget_enforcer import estimate_cost, CostEstimate, StepEstimate
from app.services.variant_limiter import get_variant_cap

router = APIRouter()
settings = get_settings()


# ─── Guards ─────────────────────────────────────────────────────

def _require_v33():
    if not settings.v3_3_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="V3.3 endpoints are not enabled",
        )


# ─── Schemas ────────────────────────────────────────────────────

class StatePatchRequest(BaseModel):
    base_version: int = Field(..., description="Expected current version (optimistic lock)")
    patch: Dict[str, Any] = Field(..., description="Partial state diff to merge")


class StateResponse(BaseModel):
    project_id: str
    version: int
    state: Optional[Dict[str, Any]]


class SimulateRequest(BaseModel):
    quality_mode: str = Field(default="balanced", description="quality | balanced | speed")
    variant_cnt: int = Field(default=2, ge=1, le=10)
    user_tier: str = Field(default="free", description="free | pro | enterprise")
    steps: Optional[List[Dict[str, Any]]] = None


class SimulateResponse(BaseModel):
    estimated_cost_cents: float
    within_budget: bool
    variant_cap: int
    effective_variant_count: int
    model_tier: str
    steps: List[Dict[str, Any]]


class MetricEntry(BaseModel):
    name: str
    value: float
    labels: Dict[str, str] = {}


# ─── Endpoints ──────────────────────────────────────────────────

@router.get("/projects/{project_id}/state", response_model=StateResponse)
async def get_project_state(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    """Read the current versioned agent state for a project."""
    _require_v33()
    state_dict, version = await state_service.read_snapshot(project_id)
    return StateResponse(project_id=project_id, version=version, state=state_dict)


@router.patch("/projects/{project_id}/state", response_model=StateResponse)
async def patch_project_state(
    project_id: str,
    body: StatePatchRequest,
    current_user: User = Depends(get_current_user),
):
    """Apply a partial state patch with optimistic locking."""
    _require_v33()

    try:
        new_state, new_version = await state_service.apply_patch(
            project_id, body.base_version, body.patch
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return StateResponse(project_id=project_id, version=new_version, state=new_state)


@router.post("/jobs/simulate", response_model=SimulateResponse)
async def simulate_job(
    body: SimulateRequest,
    current_user: User = Depends(get_current_user),
):
    """Pre-flight simulation: estimate cost and effective config before job submission."""
    _require_v33()

    model_tier = "pro" if body.quality_mode == "quality" else "flash"
    default_steps = [
        {"name": "research", "est_input_tokens": 2000, "est_output_tokens": 800},
        {"name": "generation", "est_input_tokens": 3000, "est_output_tokens": 1500},
        {"name": "evaluation", "est_input_tokens": 1000, "est_output_tokens": 300},
    ]
    steps = body.steps or default_steps
    est = estimate_cost(steps, model_tier)
    variant_cap = get_variant_cap(body.user_tier)
    effective_variants = min(body.variant_cnt, variant_cap)

    return SimulateResponse(
        estimated_cost_cents=round(est.total_cents, 4),
        within_budget=est.within_budget,
        variant_cap=variant_cap,
        effective_variant_count=effective_variants,
        model_tier=model_tier,
        steps=[{"name": s.step, "cost_cents": round(s.cost_cents, 4)} for s in est.steps],
    )


@router.get("/metrics")
async def get_metrics():
    """Lightweight Prometheus-compatible metrics endpoint."""
    _require_v33()
    
    from app.models.job_metrics import JobMetrics
    
    try:
        total_jobs = await JobMetrics.count()
        budget_exceeded = await JobMetrics.find(JobMetrics.budget_exceeded == True).count()
        
        # Average latency via aggregation
        avg_latency = 0
        if total_jobs > 0:
            agg = await JobMetrics.aggregate([
                {"$group": {"_id": None, "avg_lat": {"$avg": "$total_latency_ms"}}}
            ]).to_list()
            if agg:
                avg_latency = agg[0].get("avg_lat", 0)

        lines = [
            f"# HELP createiq_jobs_total Total jobs processed",
            f"# TYPE createiq_jobs_total counter",
            f"createiq_jobs_total {total_jobs}",
            "",
            f"# HELP createiq_budget_exceeded_total Jobs that exceeded budget",
            f"# TYPE createiq_budget_exceeded_total counter",
            f"createiq_budget_exceeded_total {budget_exceeded}",
            "",
            f"# HELP createiq_avg_latency_ms Average job latency in milliseconds",
            f"# TYPE createiq_avg_latency_ms gauge",
            f"createiq_avg_latency_ms {round(avg_latency, 2)}",
            "",
        ]
    except Exception as e:
        logger.error("Failed to collect metrics: %s", e)
        return PlainTextResponse(f"# Error collecting metrics: {e}", status_code=500)

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("\n".join(lines), media_type="text/plain; version=0.0.4")

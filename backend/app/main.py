"""
CreateIQ Backend - FastAPI Application Entry Point

V4 redesign: LangGraph pipeline replaces ARQ worker.
Qdrant vector store replaces FAISS.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import uuid
import time
from contextvars import ContextVar

from app.config import get_settings
from app.models.database import init_db, close_db
from app.models.infrastructure import (
    init_infrastructure, 
    close_infrastructure, 
    redis_cb, 
    qdrant_cb,
    CircuitState
)
from app.memory.vector_store import initialize_vector_store
from app.api.routes import auth, users, projects, agents, chat
from app.utils.logging import logger, trace_var
from app.utils.determinism import get_now, get_uuid

# logging already set up in app.utils.logging


# --- Global Observability Context (Moved to app.utils.logging) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — connect MongoDB + Qdrant on startup, close on shutdown."""
    settings = get_settings()
    logger.info("Starting %s v4.0...", settings.app_name)

    # Validate LLM API keys
    required_keys = {
        "GROQ_API_KEY": settings.groq_api_key,
        "GEMINI_API_KEY": settings.gemini_api_key,
        "OPENAI_API_KEY": settings.openai_api_key,
        "ANTHROPIC_API_KEY": settings.anthropic_api_key,
        "DEEPSEEK_API_KEY": settings.deepseek_api_key,
        "TOGETHER_API_KEY": settings.together_api_key,
        "TAVILY_API_KEY": settings.tavily_api_key,
    }
    
    missing_keys = [k for k, v in required_keys.items() if not v or "your_" in v.lower()]
    if missing_keys:
        logger.warning(
            "Missing or placeholder API keys detected: %s. "
            "Some providers may be unavailable during testing.",
            ", ".join(missing_keys)
        )

    # Initialise Core Infrastructure (MongoDB Atlas + Upstash Redis + Qdrant Cloud)
    await init_infrastructure()
    
    # Eagerly initialize core application collections (Moved from infrastructure.py)
    await initialize_vector_store()

    # NAPOS: Seed niche configs from JSON → MongoDB
    try:
        from app.niche_configs import seed_niche_configs
        seeded = await seed_niche_configs()
        logger.info("NAPOS: Niche config seeding complete (%d new configs)", seeded)
    except Exception as e:
        logger.warning("NAPOS: Niche config seeding failed (non-fatal): %s", e)

    # 4. Model Warmup (Phase 3)
    try:
        from app.llm.router import get_llm_router
        router = get_llm_router()
        # Non-blocking warmup
        asyncio.create_task(router.warmup())
    except Exception as e:
        logger.error("LLMRouter: warmup task failed: %s", e)

    if settings.v3_3_enabled:
        logger.info("V3.3 adaptive engine: ENABLED")
    else:
        logger.info("V3.3 adaptive engine: DISABLED (set V3_3_ENABLED=true to activate)")

    yield

    await close_db()
    await close_infrastructure()
    logger.info("Shutting down %s...", settings.app_name)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-powered content creator platform with multi-agent LangGraph pipeline",
        version="4.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    # --- Middleware Configuration (Outer layers) ---
    # Note: We avoid @app.middleware decorators (BaseHTTPMiddleware) for stability.

    # --- Tier 4 Global Exception Handlers ---
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from app.schemas.base import wrap_response
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Standardized handler for FastAPIs built-in HTTPExceptions."""
        logger.error(f"HTTP Error: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content=wrap_response(
                status="error",
                error={
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail
                }
            ).model_dump()
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Standardized handler for Pydantic validation errors."""
        logger.error(f"Validation Error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=wrap_response(
                status="error",
                error={
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters",
                    "details": exc.errors()
                }
            ).model_dump()
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Standardized handler for all unhandled system exceptions."""
        logger.exception("UNHANDLED SYSTEM EXCEPTION")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=wrap_response(
                status="error",
                error={
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later."
                }
            ).model_dump()
        )

    # ─── Core Routes ─────────────────────────────────────────────
    app.include_router(auth.router, prefix=f"{settings.api_v1_prefix}/auth", tags=["Authentication"])
    app.include_router(users.router, prefix=f"{settings.api_v1_prefix}/users", tags=["Users"])
    app.include_router(projects.router, prefix=f"{settings.api_v1_prefix}/projects", tags=["Projects"])
    app.include_router(agents.router, prefix=f"{settings.api_v1_prefix}/agents", tags=["Agents"])
    app.include_router(chat.router, prefix=f"{settings.api_v1_prefix}/chat", tags=["Chat"])

    # V4 Routes
    from app.api.routes import versions, strategy
    app.include_router(versions.router, prefix=f"{settings.api_v1_prefix}/projects", tags=["Versions"])
    app.include_router(strategy.router, prefix=f"{settings.api_v1_prefix}/strategy", tags=["Strategy"])

    # ─── V3.3 Routes ─────────────────────────────────────────────
    if settings.v3_3_enabled:
        from app.api.routes import v3 as v3_routes
        app.include_router(v3_routes.router, prefix=f"{settings.api_v1_prefix}", tags=["V3.3 Adaptive Engine"])

    # ─── V4 Pipeline Routes ──────────────────────────────────────
    from app.api.routes import pipeline as pipeline_routes
    from app.api.routes import stt as stt_routes
    from app.api.routes import pipeline_history
    app.include_router(
        pipeline_routes.router,
        prefix=f"{settings.api_v1_prefix}/pipeline",
        tags=["Pipeline"],
    )
    app.include_router(
        pipeline_history.router,
        prefix=f"{settings.api_v1_prefix}/pipeline",
        tags=["Pipeline History"],
    )
    app.include_router(
        stt_routes.router,
        prefix=f"{settings.api_v1_prefix}/stt",
        tags=["Speech-to-Text"],
    )

    @app.get("/health")
    async def liveness_check():
        """Liveness probe - quickly confirms the process is alive."""
        return {"status": "alive", "timestamp": time.time()}

    @app.get("/ready")
    async def readiness_check():
        """Readiness probe - confirms all core dependencies are functional for traffic."""
        settings = get_settings()
        mongo_status = "ok"
        mongo_latency = 0.0
        try:
            from app.models.database import _client
            if _client:
                start = time.time()
                await _client.admin.command("ping")
                mongo_latency = (time.time() - start) * 1000
        except Exception:
            mongo_status = "down"

        # State mapping from Circuit Breakers
        redis_status = "ok" if redis_cb.state == CircuitState.CLOSED else "down" if redis_cb.state == CircuitState.OPEN else "degraded"
        qdrant_status = "ok" if qdrant_cb.state == CircuitState.CLOSED else "down" if qdrant_cb.state == CircuitState.OPEN else "degraded"

        # Overall logic: Mongo failure is CRITICAL for readiness
        overall = "ready"
        if mongo_status == "down":
            overall = "not_ready"
        elif redis_status == "down" or qdrant_status == "down":
            overall = "degraded"
        
        status_code = 200 if overall != "not_ready" else 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": overall,
                "trace_id": trace_var.get(),
                "version": "4.0.0",
                "environment": settings.env,
                "services": {
                    "mongo": {"status": mongo_status, "latency_ms": f"{mongo_latency:.2f}"},
                    "redis": {
                        "status": redis_status,
                        "latency_ms": f"{redis_cb.metrics.latency_ms:.2f}",
                        "trips": redis_cb.metrics.trips
                    },
                    "qdrant": {
                        "status": qdrant_status,
                        "latency_ms": f"{qdrant_cb.metrics.latency_ms:.2f}",
                        "trips": qdrant_cb.metrics.trips
                    }
                }
            }
        )

    # --- CORS (The absolute outermost layer to preserve credentials/headers) ---
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

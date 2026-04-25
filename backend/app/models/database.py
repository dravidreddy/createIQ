import asyncio
import logging
from typing import Optional

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None


async def init_db() -> None:
    """
    Connect to MongoDB with singleton guard, retries, and ping validation.
    Initialises all Beanie document models.
    """
    global _client

    if _client is not None:
        logger.debug("MongoDB client already initialised (singleton).")
        return

    settings = get_settings()
    max_retries = 3
    retry_delay = 3  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Connecting to MongoDB (Attempt %d/%d)...", attempt, max_retries)
            _client = AsyncIOMotorClient(
                settings.mongo_uri,
                maxPoolSize=settings.mongodb_max_pool_size,
                minPoolSize=settings.mongodb_min_pool_size,
                serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
                connectTimeoutMS=settings.mongodb_connect_timeout_ms,
            )

            # Verification: Ping the deployment (Fail-Fast)
            await _client.admin.command("ping")
            logger.info("✓ MongoDB Connection Verified (Atlas Cloud)")
            break
        except Exception as e:
            _client = None
            if attempt == max_retries:
                logger.critical("FATAL: Failed to connect to MongoDB Atlas after %d attempts: %s", max_retries, e)
                raise ConnectionError(f"CRITICAL INFRASTRUCTURE FAILURE: Could not connect to MongoDB Atlas: {e}")
            logger.warning("Connection attempt %d failed. Retrying in %ds...", attempt, retry_delay)
            await asyncio.sleep(retry_delay)

    db = _client[settings.mongodb_db_name]

    db = _client[settings.mongodb_db_name]

    # Import all document models
    from app.models.user import User
    from app.models.profile import UserProfile
    from app.models.workspace import Workspace
    from app.models.project import Project
    from app.models.content_block import ContentBlock
    from app.models.content_version import ContentVersion
    from app.models.ai_generation import AIGeneration
    from app.models.strategy import StrategyPlan
    from app.models.conversation import Conversation
    from app.models.message import Message
    from app.models.memory_entry import MemoryEntry
    from app.models.project_agent_state import ProjectAgentState
    from app.models.budget_allocation import BudgetAllocation
    from app.models.job_metrics import JobMetrics
    from app.models.ranking_profile import RankingProfile
    from app.models.variant_log import VariantLog
    from app.models.template import ContentTemplate
    # Legacy (deprecated) — kept for backward compat
    from app.models.artifact import ProjectArtifact
    from app.models.session import AgentSession
    from app.models.project_version import ProjectVersion
    # V4 Pipeline
    from app.models.user_preferences import UserPreferencesModel
    from app.models.pipeline_checkpoint import PipelineCheckpoint
    # NAPOS
    from app.models.niche_config import NicheConfigModel
    # Billing
    from app.models.transaction import Transaction

    await init_beanie(
        database=db,
        document_models=[
            # ─── Core ───────────────────────────────────
            User,
            UserProfile,
            Workspace,
            Project,
            # ─── Content (block-based versioning) ───────
            ContentBlock,
            ContentVersion,
            # ─── AI ─────────────────────────────────────
            AIGeneration,
            StrategyPlan,
            Conversation,
            Message,
            MemoryEntry,
            # ─── V3.3 Engine ────────────────────────────
            ProjectAgentState,
            BudgetAllocation,
            JobMetrics,
            RankingProfile,
            VariantLog,
            # ─── Other ──────────────────────────────────
            ContentTemplate,
            # ─── V4 Pipeline ────────────────────────────
            UserPreferencesModel,
            PipelineCheckpoint,
            # ─── NAPOS ──────────────────────────────────
            NicheConfigModel,
            # ─── Billing ─────────────────────────────────
            Transaction,
            # ─── Legacy (deprecated) ────────────────────
            ProjectArtifact,
            AgentSession,
            ProjectVersion,
        ],
    )

    logger.info(
        "Beanie initialised — %s @ %s  (21 document models registered)",
        settings.mongodb_db_name,
        settings.mongo_uri.split("@")[-1] if "@" in settings.mongo_uri else settings.mongo_uri,
    )


async def close_db() -> None:
    """Close the Motor client connection."""
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed")

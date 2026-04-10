"""
CreatorIQ Backend Configuration

Centralized configuration management using Pydantic Settings.
Loads from environment variables and .env file.

V4 redesign: Removed Redis/ARQ/FAISS, added Qdrant + preference learning.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import json
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ─── Application ─────────────────────────────────────────────
    app_name: str = "CreateIQ"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # ─── CORS ────────────────────────────────────────────────────
    cors_origins: str = '["http://localhost:5173","http://localhost:3000","http://localhost","http://127.0.0.1:5173","http://127.0.0.1:3000","http://127.0.0.1"]'

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string and filter localhost in production."""
        try:
            origins = json.loads(self.cors_origins) if self.cors_origins else []
        except (json.JSONDecodeError, TypeError):
            # Fallback: treat as comma-separated string or single origin
            origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()] if self.cors_origins else []
        # Strip trailing slashes — CORS matching is strict
        origins = [o.rstrip("/") for o in origins]
        if self.env.lower() == "prod":
            # Filter out localhost and 127.0.0.1 for production
            origins = [o for o in origins if "localhost" not in o and "127.0.0.1" not in o]
        return origins

    # ─── Database — MongoDB ──────────────────────────────────────
    mongo_uri: str = Field(
        default="",
        description="MongoDB connection URI (Cloud Atlas required)",
        alias="MONGO_URI",
    )
    mongodb_max_pool_size: int = Field(default=100, alias="MONGODB_MAX_POOL_SIZE")
    mongodb_min_pool_size: int = Field(default=10, alias="MONGODB_MIN_POOL_SIZE")
    mongodb_server_selection_timeout_ms: int = Field(default=5000, alias="MONGODB_SERVER_TIMEOUT")
    mongodb_connect_timeout_ms: int = Field(default=10000, alias="MONGODB_CONNECT_TIMEOUT")

    @property
    def mongodb_db_name(self) -> str:
        """Dynamically determine database name based on environment."""
        suffix = self.env.lower()
        if suffix not in ["dev", "test", "prod"]:
            suffix = "dev"
        return f"creatoriq_{suffix}"

    # ─── Cache & Real-time — Redis ───────────────────────────────
    redis_url: str = Field(
        default="",
        description="Redis connection URL for real-time tracking and caching",
        alias="REDIS_URL",
    )

    # ─── JWT Authentication ──────────────────────────────────────
    secret_key: str = Field(default="dev_secret_key_change_me", description="JWT secret key")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    refresh_token_expire_days: int = 7

    # ─── Cookie security ─────────────────────────────────────────
    cookie_secure: bool = Field(
        default=False,
        description="Set True in production behind HTTPS",
    )
    cookie_samesite: str = Field(
        default="lax",
        description="Cookie SameSite attribute (lax for local, none for production cross-domain)",
    )

    # ─── LLM Providers ───────────────────────────────────────────
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    openai_api_key: str = Field(default="", description="OpenAI API key")
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    deepseek_api_key: str = Field(default="", description="DeepSeek API key")
    together_api_key: str = Field(default="", description="Together AI API key")
    groq_api_key: str = Field(default="", description="Groq API key")
    groq_api_key_2: str = Field(default="", description="Groq fallback API key 2")
    groq_api_key_3: str = Field(default="", description="Groq fallback API key 3")

    # ─── Global Overrides ────────────────────────────────────────
    llm_provider: Optional[str] = Field(default=None, description="Global LLM provider override (e.g. groq)")
    llm_model: Optional[str] = Field(default=None, description="Global LLM model override (e.g. llama-3.3-70b)")
    stt_provider: str = Field(default="groq", description="Default Speech-to-Text provider")

    # ─── Search Provider ─────────────────────────────────────────
    tavily_api_key: str = Field(default="", description="Tavily search API key")

    # ─── Vector Store — Qdrant ───────────────────────────────────
    qdrant_url: str = Field(
        default="",
        description="Qdrant vector database URL",
        alias="QDRANT_URL",
    )
    qdrant_api_key: str = Field(
        default="",
        description="API Key for cloud-managed Qdrant",
        alias="QDRANT_API_KEY",
    )

    # ─── LLM Settings ────────────────────────────────────────────
    gemini_model: str = "gemini-1.5-pro"
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-sonnet-20240620"
    deepseek_model: str = "deepseek-chat"
    groq_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096

    # ─── Preference Learning ─────────────────────────────────────
    preference_learning_rate: float = Field(
        default=0.3,
        description="EMA alpha for user preference updates from edits",
    )

    # ─── V3.3 Feature Flag ───────────────────────────────────────
    v3_3_enabled: bool = Field(default=False, description="Enable V3.3 adaptive engine")
    load_test_mode: bool = Field(default=False, description="Enable mock providers for architectural load testing")

    # ─── V3.3 Budget Enforcement ─────────────────────────────────
    budget_default_per_job_cents: int = Field(default=100, description="Hard cap in USD cents ($1.00)")
    budget_warning_threshold_cents: int = Field(default=80, description="Soft cap for warnings in USD cents")
    budget_daily_user_cap_cents: int = Field(default=500, description="Daily per-user cap in USD cents")

    # ─── V3.3 Tier Variant Caps ──────────────────────────────────
    tier_variant_cap_free: int = Field(default=2, description="Max variants for free tier")
    tier_variant_cap_pro: int = Field(default=4, description="Max variants for pro tier")
    tier_variant_cap_enterprise: int = Field(default=5, description="Max variants for enterprise tier")

    # ─── V3.3 Evaluation Engine ──────────────────────────────────
    eval_max_iterations: int = Field(default=2, description="Max evaluation refinement iterations")
    eval_quality_threshold: float = Field(default=0.85, description="Pass threshold for fast scoring (0-1)")

    # ─── V3.3 Ranking Engine ────────────────────────────────────
    ranking_learning_rate: float = Field(default=0.01, description="Micro-update learning rate for ranking weights")

    # ─── V3.3 State Summarisation ────────────────────────────────
    state_max_size_kb: int = Field(default=200, description="Max state JSON before triggering pruning")
    state_retention_days: int = Field(default=7, description="Days to keep raw history")

    # ─── V3.3 Circuit Breaker ────────────────────────────────────
    circuit_breaker_error_pct: float = Field(default=10.0, description="Error % threshold for circuit breaker")
    circuit_breaker_sample_size: int = Field(default=20, description="Min requests before evaluation")
    circuit_breaker_cooldown_sec: int = Field(default=120, description="Cooldown before re-testing")

    # ─── Alpha Readiness (Tier 4) ───────────────────────────────
    alpha_rate_limit_rpm: int = Field(default=20, description="Rate limit (starts/min)")
    alpha_sse_history_max: int = Field(default=100, description="Max events stored for SSE replay")
    alpha_sse_history_ttl: int = Field(default=1800, description="TTL for SSE history (30 mins)")


    # ─── V3.3 Cost Table (cents per 1K tokens) ──────────────────
    # Low-cost / Routing (GPT-4o-mini, Gemini Flash, DeepSeek)
    cost_per_1k_input_routing: float = Field(default=0.01, description="Cost/1K input — GPT-4o-mini")
    cost_per_1k_output_routing: float = Field(default=0.03, description="Cost/1K output — GPT-4o-mini")
    
    # Mid-range (Gemini Pro, Claude Sonnet)
    cost_per_1k_input_standard: float = Field(default=0.3, description="Cost/1K input — Claude 3.5 Sonnet / Gemini 1.5 Pro")
    cost_per_1k_output_standard: float = Field(default=1.2, description="Cost/1K output — Claude 3.5 Sonnet / Gemini 1.5 Pro")
    
    # High-end (o1-preview, Deep Reasoning)
    cost_per_1k_input_premium: float = Field(default=1.5, description="Cost/1K input — o1-preview")
    cost_per_1k_output_premium: float = Field(default=6.0, description="Cost/1K output — o1-preview")

    # ─── V3.3 Legacy Compat Cost fields ─────────────────────────
    cost_per_1k_input_flash: float = Field(default=0.01)
    cost_per_1k_output_flash: float = Field(default=0.03)
    cost_per_1k_input_pro: float = Field(default=0.35)
    cost_per_1k_output_pro: float = Field(default=1.05)

    # ─── Production Hardening ──────────────────────────
    env: str = Field(default="dev", description="Application environment (dev/prod)")
    test_mode: bool = Field(default=False, description="Enable deterministic test mode (Mocks + Fixed IDs)", alias="TEST_MODE")
    
    def validate_config(self):
        """Raise error if critical keys are missing or misconfigured in any environment."""
        critical_keys = {
            "GROQ_API_KEY": self.groq_api_key,
            "MONGO_URI": self.mongo_uri,
            "REDIS_URL": self.redis_url,
            "QDRANT_URL": self.qdrant_url,
            "QDRANT_API_KEY": self.qdrant_api_key,
        }
        
        # 1. Missing or Placeholder Check
        missing = [k for k, v in critical_keys.items() if not v or "your_" in str(v).lower()]
        if missing:
            raise ValueError(f"CRITICAL: Missing or placeholder configuration: {', '.join(missing)}")
            
        # 2. Localhost Fallback Prevention
        # In PROD: Strictly NO localhost.
        # In DEV: Warn if localhost is used but not explicitly intended.
        is_prod = self.env.lower() == "prod"
        for key, val in [("MONGO_URI", self.mongo_uri), ("REDIS_URL", self.redis_url), ("QDRANT_URL", self.qdrant_url)]:
            if "localhost" in val or "127.0.0.1" in val:
                if is_prod:
                    raise ValueError(f"CRITICAL: {key} is pointing to LOCALHOST in production environment")
                else:
                    print(f"WARNING: {key} is pointing to LOCALHOST in {self.env} environment. Using local shadow instance.")
        
        # 3. Explicit Cloud Validation (Protocols & Domains)
        # Verify MongoDB is Atlas (if not local)
        if "localhost" not in self.mongo_uri and "mongodb.net" not in self.mongo_uri:
             print(f"WARNING: MONGO_URI does not look like Atlas but is not localhost.")

        # Verify Redis is Upstash (if not local)
        if "localhost" not in self.redis_url and "upstash.io" not in self.redis_url:
             print(f"WARNING: REDIS_URL does not look like Upstash but is not localhost.")

        # Verify Qdrant is Cloud (if not local)
        if "localhost" not in self.qdrant_url and "qdrant.io" not in self.qdrant_url:
             print(f"WARNING: QDRANT_URL does not look like Qdrant Cloud but is not localhost.")
    prioritize_groq: bool = Field(default=True, description="Always try Groq first in dev mode")
    
    # Timeouts (seconds)
    timeout_groq: float = Field(default=5.0, description="Timeout for Groq requests")
    timeout_together: float = Field(default=10.0, description="Timeout for Together AI requests")
    timeout_openai: float = Field(default=15.0, description="Timeout for OpenAI requests")
    timeout_claude: float = Field(default=20.0, description="Timeout for Anthropic requests")
    timeout_default: float = Field(default=30.0, description="Default timeout for other providers")

    # Circuit Breaker Thresholds
    cb_threshold_groq: int = Field(default=3, description="Failure threshold for Groq")
    cb_threshold_premium: int = Field(default=7, description="Failure threshold for premium models")
    cb_threshold_default: int = Field(default=5, description="Default failure threshold")
    cb_cooldown_default: int = Field(default=60, description="Default cooldown period in seconds")

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance with runtime config handshake.
    """
    settings = Settings()
    
    # --- RUNTIME CONFIGURATION HANDSHAKE (PHASE 1) ---
    print(f"\n{'='*50}")
    print(f" CreatorIQ Runtime Infrastructure Handshake")
    print(f"{'='*50}")
    print(f" ENV:        {settings.env.upper()}")
    print(f" MONGO_URI:  {settings.mongo_uri.split('@')[-1].split('?')[0] if '@' in settings.mongo_uri else 'MISSING/LOCAL'}")
    print(f" REDIS_URL:  {settings.redis_url.split('@')[-1] if '@' in settings.redis_url else 'MISSING/LOCAL'}")
    print(f" QDRANT_URL: {settings.qdrant_url if settings.qdrant_url else 'MISSING'}")
    print(f"{'='*50}\n")

    settings.validate_config()
    return settings

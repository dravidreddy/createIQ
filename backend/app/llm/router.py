"""
LLM Router — Task-aware model routing with dynamic loading and scoring.

Selects the optimal provider based on task type, priority, cost-weight, 
and historical performance (latency loop).
"""

import json
import logging
import time
from typing import AsyncGenerator, Dict, Any, List, Optional

from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse, LLMStreamChunk
from app.llm.gemini import GeminiProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.deepseek import DeepSeekProvider
from app.llm.together import TogetherAIProvider
from app.llm.groq_provider import GroqProvider
from app.llm.capability_registry import PROVIDER_CAPABILITIES
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.execution_layer import ExecutionLayer
from app.llm.usage_tracker import usage_tracker
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMRouter:
    """
    Task-aware LLM router with scoring-based selection and dynamic registry.
    """

    _instance: Optional["LLMRouter"] = None

    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Performance loop (EMA latency)
        self._latency_history: Dict[str, float] = {}
        self._alpha = 0.3  # EMA smoothing factor
        
        # Dynamically load model registry
        self._load_registry()
        self._initialize_providers()
        
        # Centralized Execution Layer
        self.exec_layer = ExecutionLayer(self)

    def _load_registry(self) -> None:
        """Load model registry from JSON."""
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        registry_path = os.path.join(base_dir, "llm", "model_registry.json")
        try:
            with open(registry_path, "r") as f:
                self.registry = json.load(f)
            
            # Load feature flags if they exist
            flag_path = os.path.join(os.path.dirname(base_dir), "config", "feature_flags.json")
            try:
                with open(flag_path, "r") as f:
                    self.feature_flags = json.load(f)
            except FileNotFoundError:
                self.feature_flags = {}
                
            logger.info("LLMRouter: successfully loaded model registry and feature flags")
        except Exception as e:
            logger.error(f"LLMRouter: failed to load registry: {e}")
            self.registry = {"models": {}, "routing_defaults": {}, "fallbacks": {}}
            self.feature_flags = {}

    async def warmup(self) -> None:
        """
        Trigger lightweight warmup calls for critical models to reduce cold-start latency.
        """
        logger.info("LLMRouter: starting model warmup...")
        warmup_msg = [LLMMessage(role="user", content="Ping")]
        
        if not self.feature_flags.get("enable_warmup", True):
            return

        tasks = []
        for name, provider in self._providers.items():
            config = self.registry.get("models", {}).get(name, {})
            if config.get("warmup", False):
                logger.debug(f"LLMRouter: warming up {name}")
                tasks.append(provider.generate(warmup_msg, max_tokens=1))
        
        if tasks:
            import asyncio
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("LLMRouter: warmup complete")

    def _initialize_providers(self) -> None:
        """Initialize all providers defined in the registry."""
        model_configs = self.registry.get("models", {})
        
        for name, config in model_configs.items():
            provider_type = config.get("provider")
            model_id = config.get("model_id")
            
            try:
                if provider_type == "openai":
                    self._providers[name] = OpenAIProvider(model=model_id, provider_name="openai")
                elif provider_type == "anthropic":
                    self._providers[name] = AnthropicProvider(model=model_id)
                elif provider_type == "google":
                    self._providers[name] = GeminiProvider(model=model_id)
                elif provider_type == "deepseek":
                    self._providers[name] = DeepSeekProvider(model=model_id)
                elif provider_type == "together":
                    self._providers[name] = TogetherAIProvider(model=model_id)
                elif provider_type == "groq":
                    self._providers[name] = GroqProvider(model=model_id)
                
                if name in self._providers:
                    self._circuit_breakers[name] = CircuitBreaker(provider_name=name, failure_threshold=5)
                    self._latency_history[name] = config.get("latency_tier") == "low" and 100.0 or 1000.0
                    logger.debug(f"LLMRouter: initialized {name} ({provider_type})")
            except Exception as e:
                logger.error(f"LLMRouter: failed to initialize {name}: {e}")

    def get_provider(self, name: str) -> Optional[BaseLLMProvider]:
        """Get a provider instance by name."""
        return self._providers.get(name)

    async def is_circuit_open(self, name: str) -> bool:
        """Check if a provider's circuit is open."""
        cb = self._circuit_breakers.get(name)
        if not cb:
            return True
        return await cb.is_open()

    def get_fallback_chain(self, name: str) -> List[str]:
        """Get the fallback chain for a provider or its type."""
        # Normalize name (dots to dashes)
        norm_name = name.replace(".", "-")
        fallbacks = self.registry.get("fallbacks", {}).get(norm_name, [])
        if not fallbacks:
            config = self.registry.get("models", {}).get(norm_name, {})
            provider_type = config.get("provider")
            fallbacks = self.registry.get("fallbacks", {}).get(provider_type, [])
            
        return fallbacks

    async def record_success(self, name: str, latency: float) -> None:
        """Record success and update latency loop."""
        if name in self._circuit_breakers:
            await self._circuit_breakers[name].record_success()
        
        if latency > 0:
            old_latency = self._latency_history.get(name, latency)
            self._latency_history[name] = (self._alpha * latency) + ((1 - self._alpha) * old_latency)

    async def record_failure(self, name: str) -> None:
        """Record failure in circuit breaker."""
        if name in self._circuit_breakers:
            await self._circuit_breakers[name].record_failure()

    def _score_model(self, model_name: str, task_type: str, priority: str, **kwargs) -> float:
        """
        Score a model based on capability registry, cost, and historical latency.
        """
        config = self.registry.get("models", {}).get(model_name, {})
        if not config: return -999.0
        
        provider_type = config.get("provider")
        caps = PROVIDER_CAPABILITIES.get(provider_type, {})

        # Feature Flag: Disable specific models
        if not self.feature_flags.get(f"enable_model_{model_name}", True):
            return -1000.0

        # 1. Capability Score (using registry)
        capability_score = 0.5
        if task_type.upper() in config.get("capabilities", []):
            capability_score = 1.0
            
        # JSON Reliability boost
        if kwargs.get("json_mode"):
            if caps.get("json_reliability") == "high":
                capability_score += 0.2
            elif caps.get("json_reliability") == "low":
                capability_score -= 0.3

        # 2. Cost Score
        cost = config.get("cost_per_1k_input", 1.0)
        cost_score = max(0.0, 1.0 - (cost / 2.0))
        
        # 3. Latency Score
        latency = self._latency_history.get(model_name, 1000.0)
        latency_score = max(0.0, 1.0 - (latency / 5000.0))
        
        # Weighted Aggregation based on priority
        if priority == "HIGH":
            return (capability_score * 0.4) + (latency_score * 0.4) + (cost_score * 0.2)
        elif priority == "LOW":
            return (capability_score * 0.2) + (cost_score * 0.6) + (latency_score * 0.2)
        else: # MEDIUM
            return (capability_score * 0.4) + (cost_score * 0.3) + (latency_score * 0.3)

    async def _select_optimal_model(self, task_type: str, priority: str, trace_id: str = "unknown", **kwargs) -> str:
        """Select the best healthy model with dev-mode and cost-efficiency logic."""
        
        # 1. Dev Mode Prioritization
        if settings.env == "dev" and settings.prioritize_groq:
            for name, provider in self._providers.items():
                config = self.registry.get("models", {}).get(name, {})
                if config.get("provider") == "groq" and not await self.is_circuit_open(name):
                    usage_tracker.log_event("selection_override", f"Dev mode: forced Groq model '{name}'", trace_id=trace_id)
                    return name

        # 2. System-level global override
        env_model = settings.llm_model
        if env_model and env_model in self._providers and not await self.is_circuit_open(env_model):
            usage_tracker.log_event("selection_override", f"Global override: using '{env_model}'", trace_id=trace_id)
            return env_model

        # 3. Hybrid Mode: Default Stage 1 (IDEAS) to Groq
        if task_type == "IDEAS" or "idea" in task_type.lower():
            for name, provider in self._providers.items():
                config = self.registry.get("models", {}).get(name, {})
                if config.get("provider") == "groq" and not await self.is_circuit_open(name):
                    usage_tracker.log_event("selection", f"Hybrid Stage 1: selected Groq '{name}'", trace_id=trace_id)
                    return name

        # 4. Try default mapping
        default_model = self.registry.get("routing_defaults", {}).get(task_type)
        if default_model and not await self.is_circuit_open(default_model):
            usage_tracker.log_event("selection", f"Routing default: '{default_model}' for {task_type}", trace_id=trace_id)
            return default_model
            
        # 5. Scoring-based selection (Cost-efficient)
        best_score = -1000.0
        best_model = None
        
        for name in list(self._providers.keys()):
            if await self.is_circuit_open(name):
                continue
                
            score = self._score_model(name, task_type, priority, **kwargs)
            if score > best_score:
                best_score = score
                best_model = name
        
        selected = best_model or next(iter(self._providers.keys()))
        usage_tracker.log_event("selection", f"Scored optimal: '{selected}' (Score: {best_score:.2f})", trace_id=trace_id)
        return selected

    async def generate(
        self,
        messages: List[LLMMessage],
        task_type: str = "quality",
        priority: str = "MEDIUM",
        **kwargs,
    ) -> LLMResponse:
        """Route generation request with traceability."""
        trace_id = kwargs.get("trace_id") or f"tr-{time.time_ns()}"
        kwargs["trace_id"] = trace_id
        
        # Avoid passing trace_id twice
        select_kwargs = kwargs.copy()
        select_kwargs.pop("trace_id", None)
        
        model_name = kwargs.get("model_override") or await self._select_optimal_model(task_type, priority, trace_id=trace_id, **select_kwargs)
        
        # ─── Test Control (Phase 1) ──────────────────────────────────
        test_control = kwargs.get("test_control")
        if test_control and (settings.debug or settings.env == "development"):
            if test_control == "fail_llm":
                logger.warning(f"LLMRouter: [TEST_CONTROL] Injecting LLM failure for trace {trace_id}")
                raise Exception("Injected LLM failure for testing")
            if test_control == "slow_response":
                import asyncio
                logger.warning(f"LLMRouter: [TEST_CONTROL] Injecting 5s delay for trace {trace_id}")
                await asyncio.sleep(5)

        return await self.exec_layer.execute(
            provider_name=model_name,
            messages=messages,
            task_type=task_type,
            priority=priority,
            **kwargs
        )

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        task_type: str = "quality",
        priority: str = "MEDIUM",
        **kwargs,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Route streaming request with traceability."""
        trace_id = kwargs.get("trace_id") or f"tr-{time.time_ns()}"
        kwargs["trace_id"] = trace_id
        
        # Avoid passing trace_id twice
        select_kwargs = kwargs.copy()
        select_kwargs.pop("trace_id", None)
        
        model_name = kwargs.get("model_override") or await self._select_optimal_model(task_type, priority, trace_id=trace_id, **select_kwargs)
        
        # ─── Test Control (Phase 1) ──────────────────────────────────
        test_control = kwargs.get("test_control")
        if test_control and (settings.debug or settings.env == "development"):
            if test_control == "fail_llm":
                logger.warning(f"LLMRouter: [TEST_CONTROL] Injecting LLM failure for trace {trace_id}")
                raise Exception("Injected LLM failure for streaming test")
            if test_control == "slow_response":
                import asyncio
                logger.warning(f"LLMRouter: [TEST_CONTROL] Injecting 5s delay for trace {trace_id}")
                await asyncio.sleep(5)

        async for chunk in self.exec_layer.execute_stream(
            provider_name=model_name,
            messages=messages,
            **kwargs
        ):
            yield chunk

    @classmethod
    def get_instance(cls) -> "LLMRouter":
        """Get singleton router instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_llm_router() -> LLMRouter:
    """Convenience function."""
    return LLMRouter.get_instance()

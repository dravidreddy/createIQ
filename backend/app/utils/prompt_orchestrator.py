"""
PromptOrchestrator — NAPOS Core Engine.

Niche-Aware Adaptive Prompt Orchestration System.

Composes final prompts from 5 layers:
  1. System Layer  — Global rules (quality, format, anti-generic)
  2. Niche Layer   — Domain vocabulary, tone, patterns
  3. User Layer    — Learned preferences (tone, style, engagement)
  4. Task Layer    — Agent-specific YAML template (existing prompts)
  5. Memory Layer  — Top-K relevant past outputs (Qdrant vector search)

Each layer degrades gracefully — missing layers produce empty strings.
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional

from app.niche_configs import load_niche_config
from app.models.niche_config import NicheConfigModel
from app.utils.prompt_loader import load_system_prompt

logger = logging.getLogger(__name__)


# ── Layer 1: System Layer (Global Rules) ────────────────────────

_SYSTEM_LAYER = """## GLOBAL CONTENT GENERATION RULES

You are a high-performance content generation AI operating within the NAPOS framework.
Follow these rules at all times:

1. **Structured Output**: Always return well-organized, structured content.
2. **No Generic Filler**: Every sentence must add value. Remove fluff, filler, and generic statements.
3. **Engagement Priority**: Optimize for audience retention and engagement above all else.
4. **Platform Awareness**: Adapt content format, length, and tone to the target platform.
5. **Authenticity**: Write as a knowledgeable human creator, not a corporate bot.
6. **Specificity**: Use concrete examples, numbers, and actionable advice — never vague generalities.
"""


class PromptOrchestrator:
    """
    NAPOS Prompt Orchestration Engine.

    Composes multi-layer prompts by combining global rules, niche context,
    user preferences, task-specific templates, and memory context into a
    single coherent system prompt for LLM calls.
    """

    def __init__(self, memory_service=None):
        """
        Initialize the orchestrator.

        Args:
            memory_service: Optional MemoryService for Phase 4 memory layer.
        """
        self.memory_service = memory_service

    # ── Public API ──────────────────────────────────────────────

    async def build_system_prompt(
        self,
        agent_name: str,
        niche: str,
        user_preferences: Dict[str, Any],
        project_context: Dict[str, Any],
        prompt_version: Optional[str] = None,
        memory_context: str = "",
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> str:
        """Compose the full system prompt with all 5 context layers.

        Args:
            agent_name: Agent identifier (matches YAML filename, e.g. 'script_drafter')
            niche: Niche identifier (e.g. 'fitness', 'tech')
            user_preferences: Learned user preferences dict
            project_context: Project configuration dict
            prompt_version: Optional specific prompt version
            memory_context: Pre-built memory context string (or empty for auto-retrieval)
            user_id: For memory layer retrieval
            thread_id: For memory layer retrieval

        Returns:
            Composed multi-layer system prompt string
        """
        layers_used = []

        # Layer 1: System Layer (always present)
        system_layer = self._get_system_layer()
        layers_used.append("system")

        # Layer 2: Niche Layer (dynamic)
        niche_layer = await self._get_niche_layer(niche, project_context)
        if niche_layer:
            layers_used.append("niche")

        # Layer 3: User Layer (learned preferences)
        user_layer = self._get_user_layer(user_preferences)
        if user_layer:
            layers_used.append("user")

        # Layer 4: Task Layer (existing YAML template — the original prompt)
        task_layer = self._get_task_layer(
            agent_name, project_context, user_preferences, prompt_version
        )
        layers_used.append("task")

        # Layer 5: Memory Layer (top-K retrieval from Qdrant)
        memory_layer = await self._get_memory_layer(
            memory_context, user_id, thread_id,
            project_context.get("topic", "")
        )
        if memory_layer:
            layers_used.append("memory")

        # Compose all layers
        composed = "\n\n".join(filter(None, [
            system_layer,
            niche_layer,
            user_layer,
            task_layer,
            memory_layer,
        ]))

        # Generate hash for A/B tracking
        prompt_hash = hashlib.md5(composed.encode()).hexdigest()[:12]

        logger.info(
            "NAPOS: Composed prompt for %s [niche=%s, layers=%s, hash=%s, len=%d]",
            agent_name, niche, "+".join(layers_used), prompt_hash, len(composed)
        )

        # Store metadata for pipeline state tracking
        self._last_composition = {
            "agent": agent_name,
            "niche": niche,
            "layers_used": layers_used,
            "prompt_hash": prompt_hash,
            "prompt_length": len(composed),
        }

        return composed

    def get_last_composition_meta(self) -> Dict[str, Any]:
        """Return metadata from the last prompt composition. For pipeline state tracking."""
        return getattr(self, "_last_composition", {})

    # ── Layer Builders (Private) ────────────────────────────────

    def _get_system_layer(self) -> str:
        """Layer 1: Global rules that apply to all agents."""
        return _SYSTEM_LAYER

    async def _get_niche_layer(
        self, niche: str, project_context: Dict[str, Any]
    ) -> str:
        """Layer 2: Niche-specific domain knowledge injection.

        Dynamically loads niche config from the hybrid store and formats
        it into a structured prompt section.
        """
        if not niche or niche.lower() in ("general", "other", "_base", ""):
            return ""

        try:
            config: NicheConfigModel = await load_niche_config(niche)
        except Exception as e:
            logger.warning("NAPOS: Failed to load niche config for '%s': %s", niche, e)
            return ""

        # Early exit if it's just the base fallback
        if config.niche == "_base" and niche != "_base":
            return ""

        # Build niche layer
        parts = [f"## NICHE CONTEXT: {config.display_name.upper()}"]

        if config.tone_guidelines:
            parts.append(f"\n### Tone & Voice\n{config.tone_guidelines}")

        if config.vocabulary:
            vocab_str = ", ".join(config.vocabulary[:20])
            parts.append(f"\n### Domain Vocabulary (USE these terms naturally)\n{vocab_str}")

        if config.avoid_vocabulary:
            avoid_str = ", ".join(config.avoid_vocabulary)
            parts.append(f"\n### Avoid These Words/Phrases\n{avoid_str}")

        if config.audience_archetype:
            parts.append(f"\n### Target Audience Archetype\n{config.audience_archetype}")

        if config.content_patterns:
            patterns_str = ", ".join(config.content_patterns)
            parts.append(f"\n### Preferred Content Patterns\n{patterns_str}")

        # Platform-specific hint (if platform is known)
        platform = project_context.get("platform", "").lower()
        if platform and config.platform_hints:
            hint = getattr(config.platform_hints, platform, "")
            if hint:
                parts.append(f"\n### Platform-Specific Guidance ({platform.title()})\n{hint}")

        if config.engagement_rules:
            rules_str = "\n".join(f"- {r}" for r in config.engagement_rules)
            parts.append(f"\n### Engagement Rules\n{rules_str}")

        return "\n".join(parts)

    def _get_user_layer(self, user_preferences: Dict[str, Any]) -> str:
        """Layer 3: Personalization from learned user preferences.

        Formats EMA-learned preferences into a structured prompt section.
        """
        if not user_preferences:
            return ""

        # Filter out empty/default values
        meaningful_prefs = {
            k: v for k, v in user_preferences.items()
            if v and k != "custom_signals"
        }

        if not meaningful_prefs:
            return ""

        parts = ["## USER PERSONALIZATION"]

        pref_map = {
            "writing_style": "Writing Style",
            "tone": "Tone",
            "preferred_length": "Length Preference",
            "vocabulary_level": "Vocabulary Level",
            "engagement_style": "Engagement Style",
        }

        for key, label in pref_map.items():
            value = meaningful_prefs.get(key)
            if value:
                parts.append(f"- **{label}**: {value}")

        # Custom signals (if strong enough)
        custom = user_preferences.get("custom_signals", {})
        if custom:
            strong_signals = {k: v for k, v in custom.items() if abs(v) > 0.3}
            if strong_signals:
                signals_str = ", ".join(f"{k}: {v:+.2f}" for k, v in strong_signals.items())
                parts.append(f"- **Learned Signals**: {signals_str}")

        parts.append("\nAdapt your output to match these preferences while maintaining content quality.")

        return "\n".join(parts)

    def _get_task_layer(
        self,
        agent_name: str,
        project_context: Dict[str, Any],
        user_preferences: Dict[str, Any],
        prompt_version: Optional[str] = None,
    ) -> str:
        """Layer 4: Agent-specific task prompt from YAML templates.

        This wraps the existing prompt_loader to maintain backward compatibility.
        All existing YAML prompts continue to work unchanged.
        """
        try:
            # Sanitize project_context to prevent keyword collisions with
            # load_system_prompt's named parameters (agent_name, version, prompt_key)
            safe_context = {
                k: v for k, v in project_context.items()
                if k not in ("user_preferences", "version", "agent_name", "prompt_key")
            }
            return load_system_prompt(
                agent_name,
                version=prompt_version,
                user_preferences=user_preferences,
                **safe_context,
            )
        except Exception as e:
            logger.error("NAPOS: Failed to load task prompt for '%s': %s", agent_name, e)
            return ""

    async def _get_memory_layer(
        self,
        memory_context: str,
        user_id: Optional[str],
        thread_id: Optional[str],
        topic: str,
    ) -> str:
        """Layer 5: Memory context from Qdrant vector search.

        Retrieves top-K semantically similar past outputs to provide
        continuity and context-awareness across sessions.
        """
        # Use pre-built context if provided
        if memory_context:
            return f"## RELEVANT PAST CONTEXT\n{memory_context}"

        # Auto-retrieve from Qdrant if memory service is available
        if not self.memory_service or not user_id or not topic:
            return ""

        try:
            results = await self.memory_service.search_similar(
                query=topic,
                user_id=user_id,
                thread_id=thread_id or "",
                top_k=3,
            )

            if not results:
                return ""

            memory_parts = ["## RELEVANT PAST CONTEXT"]
            for i, result in enumerate(results[:3], 1):
                content = result.get("content", "")[:500]
                content_type = result.get("content_type", "output")
                similarity = result.get("score", 0)
                memory_parts.append(
                    f"\n### Past {content_type.title()} (relevance: {similarity:.2f})\n{content}"
                )

            return "\n".join(memory_parts)

        except Exception as e:
            logger.warning("NAPOS: Memory layer retrieval failed: %s", e)
            return ""


# ── Module-level singleton ──────────────────────────────────────

_orchestrator: Optional[PromptOrchestrator] = None


def get_prompt_orchestrator(memory_service=None) -> PromptOrchestrator:
    """Get or create the global PromptOrchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PromptOrchestrator(memory_service=memory_service)
    return _orchestrator


def reset_orchestrator() -> None:
    """Reset the singleton (for testing)."""
    global _orchestrator
    _orchestrator = None

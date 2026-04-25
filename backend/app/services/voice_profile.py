"""
Voice Profile Service — Analyze creator scripts to learn their unique voice.

Uses LLM to extract tone, vocabulary, pacing, and signature phrases from
2-3 sample scripts, then stores the profile on UserProfile for injection
into all future pipeline runs.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId

from app.llm.router import get_llm_router
from app.llm.base import LLMMessage
from app.models.profile import UserProfile
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

VOICE_ANALYSIS_PROMPT = """You are an expert writing style analyst. Analyze the following scripts written by a content creator and extract their unique voice profile.

Return a JSON object with EXACTLY these fields:
{
  "tone": "one of: casual_energetic, professional_authoritative, friendly_conversational, dramatic_storytelling, educational_calm, humorous_irreverent",
  "avg_sentence_length": <number of words per sentence on average>,
  "hook_style": "one of: question_based, bold_statement, story_opening, statistic_shock, direct_address, curiosity_gap",
  "vocabulary_level": "one of: simple, moderate, advanced",
  "signature_phrases": ["list of 3-5 recurring phrases or speech patterns the creator uses"],
  "pacing": "one of: fast_throughout, slow_deliberate, fast_start_slow_middle, building_crescendo, varied_dynamic",
  "formality": "one of: very_informal, informal, balanced, formal, very_formal",
  "engagement_style": "one of: question_heavy, story_driven, data_driven, opinion_forward, tutorial_step_by_step",
  "emotional_range": "one of: high_energy, measured, deadpan, passionate, calm_confident"
}

Analyze the scripts carefully. Look for:
- Recurring words and phrases
- Sentence structure patterns
- How they open and close sections
- Their relationship with the audience (do they say "you", "we", "I"?)
- Punctuation and emphasis patterns

Return ONLY valid JSON, no markdown or explanation."""


class VoiceProfileService:
    """Analyze and manage creator voice profiles."""

    def __init__(self):
        self.router = get_llm_router()

    async def analyze_and_save(
        self, user_id: str, scripts: List[str]
    ) -> Dict[str, Any]:
        """Analyze sample scripts and save the extracted voice profile.

        Args:
            user_id: The creator's user ID (MongoDB ObjectId string)
            scripts: List of 2-3 sample scripts to analyze

        Returns:
            The extracted voice profile dict
        """
        if not scripts or len(scripts) < 1:
            raise ValueError("At least 1 script is required for voice analysis")

        # Truncate to prevent token overflow (keep ~2000 words per script)
        truncated = []
        for i, script in enumerate(scripts[:5]):  # Max 5 scripts
            words = script.split()[:2000]
            truncated.append(f"--- SCRIPT {i + 1} ---\n{' '.join(words)}")

        combined = "\n\n".join(truncated)

        messages = [
            LLMMessage(role="system", content=VOICE_ANALYSIS_PROMPT),
            LLMMessage(role="user", content=combined),
        ]

        response = await self.router.generate(
            messages=messages,
            task_type="scoring",
            priority="MEDIUM",
            json_mode=True,
        )

        # Parse the LLM response
        try:
            profile_data = json.loads(response.content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown fences
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            profile_data = json.loads(content.strip())

        profile_data["analyzed_at"] = utc_now().isoformat()
        profile_data["sample_count"] = len(scripts)

        # Save to UserProfile
        user_profile = await UserProfile.find_one(
            UserProfile.user_id == PydanticObjectId(user_id)
        )

        if not user_profile:
            logger.warning("voice_profile: no UserProfile found for %s", user_id)
            raise ValueError("User profile not found. Complete profile setup first.")

        user_profile.voice_profile = profile_data
        user_profile.voice_sample_count = len(scripts)
        user_profile.updated_at = utc_now()
        await user_profile.save()

        logger.info(
            "voice_profile: saved for user %s (tone=%s, %d scripts analyzed)",
            user_id, profile_data.get("tone"), len(scripts),
        )

        return profile_data

    async def get_voice_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the current voice profile for a user."""
        user_profile = await UserProfile.find_one(
            UserProfile.user_id == PydanticObjectId(user_id)
        )
        if not user_profile:
            return None
        return user_profile.voice_profile

    async def reset_voice_profile(self, user_id: str) -> bool:
        """Reset the voice profile for a user."""
        user_profile = await UserProfile.find_one(
            UserProfile.user_id == PydanticObjectId(user_id)
        )
        if not user_profile:
            return False

        user_profile.voice_profile = None
        user_profile.voice_sample_count = 0
        user_profile.updated_at = utc_now()
        await user_profile.save()

        logger.info("voice_profile: reset for user %s", user_id)
        return True

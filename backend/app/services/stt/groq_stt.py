"""
Groq STT Provider — Whisper-large-v3 implementation.
"""

import logging
from typing import BinaryIO, Optional
from groq import AsyncGroq

from app.services.stt.base import BaseSTTProvider
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class GroqSTTProvider(BaseSTTProvider):
    """
    Groq Whisper STT implementation.
    """

    def __init__(self, api_key: str = None):
        self._api_key = api_key or settings.groq_api_key
        self.client = AsyncGroq(api_key=self._api_key)
        self._default_model = "whisper-large-v3"
        self._name = "groq"

    @property
    def provider_name(self) -> str:
        return self._name

    async def transcribe(
        self, 
        audio_file: BinaryIO, 
        model: Optional[str] = None,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> str:
        """Transcribe audio using Groq Whisper."""
        try:
            transcription = await self.client.audio.transcriptions.create(
                file=audio_file,
                model=model or self._default_model,
                language=language,
                prompt=prompt,
                response_format="json"
            )
            return transcription.text
        except Exception as e:
            logger.error(f"Groq STT error: {e}")
            raise Exception(f"Failed to transcribe with Groq: {str(e)}")

"""
STT Router — Dynamic selecting and dispatching Speech-to-Text requests.
"""

import logging
from typing import BinaryIO, Optional, Dict
from app.services.stt.base import BaseSTTProvider
from app.services.stt.groq_stt import GroqSTTProvider
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class STTRouter:
    """
    Router for selecting and using STT providers.
    """

    _instance: Optional["STTRouter"] = None

    def __init__(self):
        self._providers: Dict[str, BaseSTTProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Load and initialize STT providers based on config."""
        try:
            # Groq is default/primary
            self._providers["groq"] = GroqSTTProvider()
            logger.info("STTRouter: initialized Groq STT Provider")
            
            # Future providers (OpenAI, Local) can be added here
        except Exception as e:
            logger.error(f"STTRouter: failed to initialize providers: {e}")

    def _validate_audio(self, audio_file: BinaryIO) -> None:
        """Lightweight validation for production safety."""
        # 1. Size Check (25MB limit as per Groq Whisper constraints)
        MAX_SIZE = 25 * 1024 * 1024
        audio_file.seek(0, 2)
        size = audio_file.tell()
        audio_file.seek(0)
        
        if size > MAX_SIZE:
            logger.error(f"STTRouter: File too large ({size / (1024*1024):.2f}MB)")
            raise ValueError(f"Audio file exceeds 25MB limit. Provided: {size / (1024*1024):.2f}MB")
            
        if size < 100: # Arbitrary small floor for "empty" or invalid headers
            logger.warning("STTRouter: File is too small to be valid audio")
            raise ValueError("Audio file is empty or invalid.")

    async def transcribe(
        self, 
        audio_file: BinaryIO, 
        provider_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """Routes transcription request with strict validation."""
        # 1. Immediate validation
        self._validate_audio(audio_file)
        
        # 2. Selection logic
        target = provider_name or settings.stt_provider
        
        provider = self._providers.get(target)
        if not provider:
            if not self._providers:
                raise Exception("No STT providers initialized.")
            provider = next(iter(self._providers.values()))
            logger.warning(f"STTRouter: Request '{target}' not found. Falling back to '{provider.provider_name}'")
            
        return await provider.transcribe(audio_file, **kwargs)

    @classmethod
    def get_instance(cls) -> "STTRouter":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

def get_stt_router() -> STTRouter:
    """Convenience function."""
    return STTRouter.get_instance()

"""
Base STT Provider — Abstract interface for Speech-to-Text services.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional

class BaseSTTProvider(ABC):
    """
    Abstract base class for STT providers (Groq-Whisper, OpenAI-Whisper, etc.)
    """

    @abstractmethod
    async def transcribe(
        self, 
        audio_file: BinaryIO, 
        model: Optional[str] = None,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> str:
        """
        Transcribe audio file to text.
        
        Args:
            audio_file: File-like object containing audio data (wav, mp3, m4a, etc.)
            model: Model override
            language: ISO-639-1 language code
            prompt: Contextual prompt to guide transcription
            
        Returns:
            Transcribed text
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass

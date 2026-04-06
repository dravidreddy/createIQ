"""
Together AI LLM Provider — OpenAI-compatible.
"""

from app.llm.openai_provider import OpenAIProvider
from app.config import get_settings

settings = get_settings()


class TogetherAIProvider(OpenAIProvider):
    """
    Together AI LLM provider using OpenAI-compatible API.
    """

    def __init__(self, api_key: str = None, model: str = None):
        super().__init__(
            api_key=api_key or settings.together_api_key,
            base_url="https://api.together.xyz/v1",
            model=model or "togethercontainer/qwen2.5-7b-instruct",
            provider_name="together"
        )

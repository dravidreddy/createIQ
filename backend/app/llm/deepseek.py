"""
DeepSeek LLM Provider — OpenAI-compatible.
"""

from app.llm.openai_provider import OpenAIProvider
from app.config import get_settings

settings = get_settings()


class DeepSeekProvider(OpenAIProvider):
    """
    DeepSeek LLM provider using OpenAI-compatible API.
    """

    def __init__(self, api_key: str = None, model: str = None):
        super().__init__(
            api_key=api_key or settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
            model=model or settings.deepseek_model,
            provider_name="deepseek"
        )

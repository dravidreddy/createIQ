"""
Abstract LLM Provider

Base class for vendor-agnostic LLM integration.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, List, Optional
from pydantic import BaseModel


class LLMMessage(BaseModel):
    """Schema for LLM messages."""
    role: str  # system, user, assistant, tool
    content: str
    metadata: Dict[str, Any] = {}


class LLMResponse(BaseModel):
    """Schema for normalized LLM response."""
    content: str
    input_tokens: int
    output_tokens: int
    cost_cents: float = 0.0
    latency_ms: float = 0.0
    model: str
    model_path: str = ""  # Actual model used (e.g. gpt-4o-mini)
    finish_reason: str = "stop"
    provider_metadata: Dict[str, Any] = {}
    tool_calls: Optional[List[Dict[str, Any]]] = None


class LLMStreamChunk(BaseModel):
    """Schema for normalized streaming response chunk."""
    content: str
    is_complete: bool = False
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_cents: Optional[float] = None
    model: Optional[str] = None
    tool_call_chunks: Optional[List[Dict[str, Any]]] = None


class LLMError(Exception):
    """Base exception for all LLM-related errors."""
    def __init__(self, message: str, provider: str = "unknown", retryable: bool = True):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class LLMTimeoutError(LLMError):
    """Raised when an LLM request times out."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when an LLM provider returns a rate limit error."""
    pass


class LLMNotExecutedError(LLMError):
    """Raised when an LLM call returns empty content."""
    pass


class TokenUsageMissingError(LLMError):
    """Raised when an LLM call returns zero tokens."""
    pass


class LLMProviderDownError(LLMError):
    """Raised when an LLM provider is completely unreachable or returning 5xx."""
    pass


class LLMInvalidRequestError(LLMError):
    """Raised when the request is malformed or violates provider policy."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, provider=provider, retryable=False)


class LLMBudgetExceededError(LLMError):
    """Raised when a request would exceed the project or user budget."""
    def __init__(self, message: str):
        super().__init__(message, retryable=False)


# Standardized Error Codes for V4 Production Hardening
class ErrorCode:
    LLM_NOT_EXECUTED = "LLM_NOT_EXECUTED"
    CRITICAL_NODE_FAILURE = "CRITICAL_NODE_FAILURE"
    TIMEOUT = "TIMEOUT"
    NO_MODEL_SELECTED = "NO_MODEL_SELECTED"
    TOKEN_USAGE_MISSING = "TOKEN_USAGE_MISSING"
    GRAPH_EXECUTION_FAILED = "GRAPH_EXECUTION_FAILED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    Implement this class to add support for new LLM providers
    (OpenAI, Anthropic, etc.) without changing agent code.
    """
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name."""
        pass

    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether the model/provider supports native tool calling."""
        pass

    @abstractmethod
    def supports_json(self) -> bool:
        """Whether the model/provider supports JSON mode/structured output."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM.
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Generate a streaming response from the LLM.
        """
        pass
    
    async def generate_with_tools(
        self,
        messages: List[LLMMessage],
        tools: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response with tool/function calling.
        Default implementation calls generate with tools in kwargs.
        """
        return await self.generate(messages, tools=tools, temperature=temperature, max_tokens=max_tokens, **kwargs)
    
    def format_system_prompt(self, base_prompt: str, user_context: Dict[str, Any]) -> str:
        """
        Format system prompt with user context.
        """
        return base_prompt.format(**user_context)

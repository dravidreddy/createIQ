"""
Provider Capability Registry — Metadata for intelligent routing.
"""

PROVIDER_CAPABILITIES = {
    "groq": {
        "json_reliability": "low",
        "tool_calling": "partial",
        "streaming": True,
        "latency": "ultra_fast",
        "context_limit": 32768,
    },
    "openai": {
        "json_reliability": "high",
        "tool_calling": "native",
        "streaming": True,
        "latency": "medium",
        "context_limit": 128000,
    },
    "anthropic": {
        "json_reliability": "high",
        "tool_calling": "strong",
        "streaming": True,
        "latency": "medium",
        "context_limit": 200000,
    },
    "google": {
        "json_reliability": "medium",
        "tool_calling": "native",
        "streaming": True,
        "latency": "medium",
        "context_limit": 1000000,
    },
    "deepseek": {
        "json_reliability": "medium",
        "tool_calling": "native",
        "streaming": True,
        "latency": "medium",
        "context_limit": 64000,
    },
    "together": {
        "json_reliability": "medium",
        "tool_calling": "partial",
        "streaming": True,
        "latency": "fast",
        "context_limit": 32768,
    }
}

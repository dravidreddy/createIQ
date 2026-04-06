from typing import Any, Generic, Optional, TypeVar, Dict
from pydantic import BaseModel, Field

T = TypeVar("T")

class ResponseMetadata(BaseModel):
    trace_id: str
    latency_ms: Optional[float] = None

class CreatorResponse(BaseModel, Generic[T]):
    """Standardized API response envelope for CreatorIQ V4."""
    status: str = "success"
    data: Optional[T] = None
    error: Optional[dict[str, Any]] = None
    metadata: ResponseMetadata

def wrap_response(
    data: Optional[T] = None, 
    error: Optional[dict[str, Any]] = None,
    trace_id: str = "",
    status: str = "success"
) -> CreatorResponse[T]:
    """Helper to wrap any data or error in the standardized CreatorResponse envelope."""
    from app.utils.logging import trace_var
    return CreatorResponse(
        status=status,
        data=data,
        error=error,
        metadata=ResponseMetadata(
            trace_id=trace_id or trace_var.get(),
            latency_ms=0.0
        )
    )

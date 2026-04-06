"""
Production-Ready Chat Endpoint for CreatorIQ

This endpoint serves as a unified interface for testing and interacting with the 
LangGraph-orchestrated AI pipeline. It supports both JSON (blocking) and SSE (streaming)
responses and handles test control headers for resilience validation.
"""

import asyncio
import logging
import uuid
import json
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from fastapi.responses import StreamingResponse, JSONResponse

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.pipeline import PipelineStartRequest, PipelineEvent
from app.pipeline.graph import get_graph
from app.worker import run_pipeline_task
from app.config import get_settings
from app.llm.base import ErrorCode
from app.utils.determinism import get_uuid
from app.schemas.base import wrap_response
import redis.asyncio as redis

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()

class ChatRequest(PipelineStartRequest):
    blocking: bool = False
    test_control: Optional[str] = None

@router.post("/")
async def chat_interaction(
    body: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    x_test_control: Optional[str] = Header(None)
):
    """
    Unified chat endpoint. 
    If body.blocking is True, it waits for the full pipeline execution (not recommended for long runs).
    If body.blocking is False (default), it returns an SSE stream.
    """
    request_id = request.headers.get("X-Request-ID", get_uuid())
    thread_id = f"chat:{body.project_id}:{get_uuid()}"
    test_control = body.test_control or x_test_control

    # 3. Validate project existence
    from app.models.project import Project
    from beanie import PydanticObjectId
    
    try:
        logger.info(f"Chat: Validating project_id={body.project_id}")
        project = await Project.get(PydanticObjectId(body.project_id))
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {body.project_id} not found"
            )
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid project_id format: {body.project_id}"
        )

    # 4. Initialize State & Trace
    from app.pipeline.routes import _build_initial_state
    initial_state = _build_initial_state(body, current_user, request_id, thread_id)
    
    # Inject test control into state so nodes can pick it up
    if test_control:
        initial_state["test_control"] = test_control
        logger.info(f"Chat: [TEST_CONTROL] {test_control} active for thread {thread_id}")

    if body.blocking:
        # For blocking mode, we run the graph directly in this request
        # WARNING: This might timeout for a full 6-stage pipeline
        # but is useful for small-talk or fast-path testing.
        try:
            graph = get_graph()
            config = {"configurable": {"thread_id": thread_id}}
            final_state = await graph.ainvoke(initial_state, config)
            
            if final_state.get("status") == "failed":
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content=wrap_response(
                        status="error",
                        error={
                            "code": final_state.get("error_code", ErrorCode.INTERNAL_ERROR),
                            "message": "Pipeline execution failed",
                            "execution_trace": final_state.get("execution_trace", [])
                        },
                        data={
                            "thread_id": thread_id,
                            "request_id": request_id,
                            "metadata": {
                                "total_cost_cents": final_state.get("total_cost_cents", 0),
                                "total_tokens": final_state.get("total_tokens", {"input": 0, "output": 0}),
                                "trace_id": request_id,
                                "model": final_state.get("last_model_used") or "unknown",
                            }
                        }
                    ).model_dump()
                )

            return JSONResponse(
                wrap_response(
                    status="success",
                    data={
                        "thread_id": thread_id,
                        "request_id": request_id,
                        "output": {
                            "idea": final_state.get("selected_idea"),
                            "hook": final_state.get("selected_hook"),
                            "script": final_state.get("edited_script") or final_state.get("script"),
                        },
                        "metadata": {
                            "total_cost_cents": final_state.get("total_cost_cents", 0),
                            "total_tokens": final_state.get("total_tokens", {"input": 0, "output": 0}),
                            "trace_id": request_id,
                            "model": final_state.get("last_model_used") or "unknown", 
                        },
                        "execution_trace": final_state.get("execution_trace", [])
                    }
                ).model_dump()
            )
        except Exception as e:
            logger.exception("Chat: blocking execution failed")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=wrap_response(
                    status="error",
                    error={
                        "code": ErrorCode.INTERNAL_ERROR,
                        "message": str(e),
                        "execution_trace": ["exception_raised:root_handler"]
                    },
                    data={
                        "thread_id": thread_id,
                        "request_id": request_id
                    }
                ).model_dump()
            )

    # Default: SSE Streaming
    # 1. Enqueue the task
    await run_pipeline_task.kiq(thread_id=thread_id, initial_state=initial_state)

    # 2. Return the stream generator (reusing logic from pipeline/start)
    from app.pipeline.streaming import stream_start_event, format_sse

    async def event_generator():
        r = redis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        channel = f"pipeline_stream:{thread_id}:{request_id}"
        await pubsub.subscribe(channel)

        local_seq = 0
        try:
            yield stream_start_event(thread_id, request_id, local_seq)
            local_seq += 1
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"].decode("utf-8")
                    yield data
                    if '"type": "stream_end"' in data:
                        break
        except asyncio.CancelledError:
            logger.info("Chat: Stream cancelled for thread %s", thread_id)
        finally:
            await pubsub.unsubscribe(channel)
            await r.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Thread-Id": thread_id,
            "X-Request-ID": request_id,
        }
    )

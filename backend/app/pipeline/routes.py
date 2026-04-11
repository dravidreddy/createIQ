import logging
import uuid
import json
import asyncio
from typing import Dict, Any, Optional
from uuid import uuid4
import redis.asyncio as redis
from app.models.infrastructure import get_redis

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.pipeline import (
    PipelineStartRequest,
    PipelineResumeRequest,
    PipelineStatusResponse,
)
from app.pipeline.graph import get_graph
from app.pipeline.streaming import (
    format_sse,
    group_start_event,
    get_interrupt_data,
    error_event,
    stream_start_event,
)
from app.config import get_settings
from app.worker import run_pipeline_async
from app.schemas.base import CreatorResponse, wrap_response

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


async def verify_alpha_rate_limit(user: User = Depends(get_current_user)):
    """
    Redis-based rate limiter for Alpha users.
    Limits pipeline starts to alpha_rate_limit_rpm (default 5/min).
    """
    import time
    r = redis.from_url(settings.redis_url, decode_responses=True)
    minute_key = f"rate_limit:{user.id}:{time.strftime('%Y%m%d%H%M')}"
    
    try:
        count = await r.incr(minute_key)
        if count == 1:
            await r.expire(minute_key, 60)
            
        if count > settings.alpha_rate_limit_rpm:
            logger.warning(f"Rate limit exceeded for user {user.id}")
            raise HTTPException(
                status_code=429, 
                detail=f"Rate limit exceeded. Max {settings.alpha_rate_limit_rpm} pipeline starts per minute."
            )
    finally:
        await r.close()


def _build_initial_state(body: PipelineStartRequest, user: User, request_id: str, thread_id: str) -> Dict[str, Any]:
    """Build the initial PipelineState from a start request."""
    return {
        "user_id": str(user.id),
        "project_id": body.project_id,
        "thread_id": thread_id,
        "job_id": str(uuid4()),
        "user_preferences": None,
        "project_context": {
            "topic": body.topic,
            "niche": body.niche,
            "platforms": body.platforms,
            "platform": body.platform or (body.platforms[0] if body.platforms else "YouTube"),
            "video_length": body.video_length,
            "target_audience": body.target_audience,
            "language": body.language,
            "style_overrides": body.style_overrides,
        },
        "ideas": None,
        "selected_idea": None,
        "hooks": None,
        "selected_hook": None,
        "script": None,
        "structure_guidance": None,
        "edited_script": None,
        "strategy_plan": None,
        "edit_history": [],
        "current_stage": "",
        "completed_stages": [],
        "errors": [],
        "total_cost_cents": 0.0,
        "total_tokens": {"input": 0, "output": 0},
        "execution_mode": body.execution_mode or "auto",
        "node_confidence": {},
        "user_action": None,
        "user_edited_content": None,
        "_last_action": None,
        "should_terminate": False,
        "stream_events": [],
        "status": "initialized",
        "error_code": None,
        "execution_trace": ["START: request received"],
        "last_model_used": None,
        "fallback_triggered": False,
    }


@router.get("/config", response_model=CreatorResponse[dict])
async def get_pipeline_config():
    """Exposes global feature flags and versioning for frontend synchronization."""
    return wrap_response({
        "config_version": 1,
        "v3_3_enabled": getattr(settings, "V3_3_ENABLED", False),
        "streaming_batch_threshold": 5,
        "heartbeat_interval_ms": 5000,
        "interrupt_version": 1
    })


@router.post("/start", dependencies=[Depends(verify_alpha_rate_limit)])
async def start_pipeline(
    body: PipelineStartRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
):
    """Start a new pipeline execution with isolated streaming channels."""
    request_id = http_request.headers.get("X-Request-ID", str(uuid4()))
    thread_id = f"{body.project_id}:{uuid4()}"
    initial_state = _build_initial_state(body, current_user, request_id, thread_id)

    asyncio.create_task(run_pipeline_async(thread_id=thread_id, initial_state=initial_state))
    logger.info(f"Launched pipeline background task for thread {thread_id} [Req: {request_id}]")

    async def event_generator():
        if not settings.redis_url:
            raise ValueError("REDIS_URL must be configured for pipeline streaming")
        
        r = get_redis()
        pubsub = r.pubsub()
        channel = f"pipeline_stream:{thread_id}:{request_id}"
        await pubsub.subscribe(channel)

        local_seq = 0
        heartbeat_task = None

        async def heartbeat():
            nonlocal local_seq
            while True:
                await asyncio.sleep(5)
                yield heartbeat_event(thread_id, request_id, local_seq)
                local_seq += 1

        try:
            logger.info("Stream opened", extra={"thread_id": thread_id, "request_id": request_id})
            
            # 1. Start Event
            yield stream_start_event(thread_id, request_id, local_seq)
            local_seq += 1
            
            # 2. Legacy Thread Created Event
            from app.schemas.pipeline import PipelineEvent
            yield format_sse(PipelineEvent(
                type="thread_created", 
                seq=local_seq, 
                thread_id=thread_id, 
                request_id=request_id, 
                content={"thread_id": thread_id}
            ))
            local_seq += 1

            # 3. Listen for Redis events with heartbeat interleaved
            # Note: We use a loop that checks both the pubsub and a timer
            while True:
                # Check for message with 5s timeout to trigger heartbeat
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
                
                if message:
                    if message["type"] == "message":
                        data = message["data"].decode("utf-8")
                        yield data
                        if '"type": "stream_end"' in data:
                            logger.info("Stream finished normally", extra={"thread_id": thread_id})
                            break
                else:
                    # Timeout reached -> emit heartbeat
                    yield heartbeat_event(thread_id, request_id, local_seq)
                    local_seq += 1
                    
        except asyncio.CancelledError:
            logger.info("Stream client disconnected (Cancelled)", extra={"thread_id": thread_id})
        except Exception as e:
            logger.error("Stream error", extra={"error": str(e), "thread_id": thread_id})
            yield error_event(thread_id, request_id, local_seq, message=str(e), error_type="STREAM_ERROR")
        finally:
            await pubsub.unsubscribe(channel)
            logger.info("Stream closed", extra={"thread_id": thread_id})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Thread-Id": thread_id,
            "X-Request-ID": request_id,
        },
    )


@router.post("/{thread_id}/resume")
async def resume_pipeline(
    thread_id: str,
    body: PipelineResumeRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
):
    """Resume pipeline with isolated streaming channels."""
    request_id = http_request.headers.get("X-Request-ID", str(uuid4()))
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Pipeline thread not found")

    update = {
        "user_action": body.action,
        "user_edited_content": body.edited_content,
        "request_id": request_id,
    }

    if body.selected_content:
        if body.stage in ("idea_selection",):
            update["selected_idea"] = body.selected_content
        elif body.stage in ("hook_selection",):
            update["selected_hook"] = body.selected_content

    await graph.aupdate_state(config, update)
    asyncio.create_task(run_pipeline_async(thread_id=thread_id, initial_state={"request_id": request_id}))

    async def event_generator():
        if not settings.redis_url:
            raise ValueError("REDIS_URL must be configured for pipeline resume streaming")
        r = get_redis()
        pubsub = r.pubsub()
        channel = f"pipeline_stream:{thread_id}:{request_id}"
        await pubsub.subscribe(channel)

        local_seq = 0
        try:
            logger.info("Resume stream opened", extra={"thread_id": thread_id, "request_id": request_id})
            
            yield stream_start_event(thread_id, request_id, local_seq)
            local_seq += 1
            
            yield group_start_event(thread_id, request_id, local_seq, body.stage, f"Resuming pipeline from {body.stage}...")
            local_seq += 1

            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
                if message:
                    if message["type"] == "message":
                        data = message["data"].decode("utf-8")
                        yield data
                        if '"type": "stream_end"' in data:
                            logger.info("Resume stream finished normally", extra={"thread_id": thread_id})
                            break
                else:
                    yield heartbeat_event(thread_id, request_id, local_seq)
                    local_seq += 1

        except asyncio.CancelledError:
            logger.info("Resume stream client disconnected", extra={"thread_id": thread_id})
        except Exception as e:
            logger.error("Resume stream error", extra={"error": str(e), "thread_id": thread_id})
            yield error_event(thread_id, request_id, local_seq, message=str(e), error_type="RESUME_STREAM_ERROR")
        finally:
            await pubsub.unsubscribe(channel)
            logger.info("Resume stream closed", extra={"thread_id": thread_id})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id,
        },
    )


@router.get("/{thread_id}/status", response_model=CreatorResponse[PipelineStatusResponse])
async def get_pipeline_status(
    thread_id: str,
    last_seq: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    """Get current pipeline state with full HITL recovery data."""
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Pipeline thread not found")

    values = state.values
    
    # Calculate recovery data if waiting for user input
    interrupt_data = None
    if state.next and any(n.startswith("process_") for n in state.next):
        from app.pipeline.streaming import get_interrupt_data as build_interrupt
        interrupt_data = build_interrupt(values)

    return wrap_response(PipelineStatusResponse(
        thread_id=thread_id,
        current_stage=values.get("current_stage"),
        completed_stages=values.get("completed_stages", []),
        next_nodes=list(state.next) if state.next else [],
        total_cost_cents=values.get("total_cost_cents", 0),
        total_tokens=values.get("total_tokens", {"input": 0, "output": 0}),
        errors=values.get("errors", []),
        interrupt_data=interrupt_data
    ))


@router.get("/schema", response_model=CreatorResponse[dict])
async def get_pipeline_schema(current_user: User = Depends(get_current_user)):
    """Return the static pipeline stages mapping for the UI."""
    return wrap_response({
        "stages": [
            {"id": "idea_discovery", "name": "Idea Discovery", "interrupt_node": "process_idea_selection"},
            {"id": "hook_generation", "name": "Hook Generation", "interrupt_node": "process_hook_selection"},
            {"id": "script_writing", "name": "Script Writing", "interrupt_node": "process_script_edit"},
            {"id": "structure", "name": "Screenplay Structure", "interrupt_node": "process_structure_edit"},
            {"id": "editing", "name": "Script Editing", "interrupt_node": "process_final_review"},
            {"id": "strategy", "name": "Strategy & SEO", "interrupt_node": "process_strategy_approval"},
        ]
    })

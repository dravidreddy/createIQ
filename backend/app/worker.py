import asyncio
import logging
import json
import signal
import time
import redis.asyncio as redis
from typing import Any, Dict, Optional, List
from taskiq import TaskiqScheduler
from taskiq_redis import ListQueueBroker
from langchain_core.messages import AIMessageChunk

from app.config import get_settings
from app.models.database import init_db, close_db
from app.models.infrastructure import get_redis, init_infrastructure, close_infrastructure
from app.pipeline.graph import get_graph
from app.pipeline.streaming import (
    format_state_update_as_sse,
    interrupt_event,
    get_interrupt_data,
    stream_start_event,
    stream_end_event,
    error_event,
    token_event,
    heartbeat_event,
    agent_complete_event,
    node_complete_event,
    metrics_event,
)

settings = get_settings()
logger = logging.getLogger(__name__)

# Initialize TaskIQ Redis Broker
broker = ListQueueBroker(settings.redis_url)

# Generic Redis client (Upstash) — initialized lazily
def get_worker_redis():
    return get_redis()

redis_client = None # Will be retrieved inside tasks

@broker.task(task_name="run_pipeline")
async def run_pipeline_task(
    thread_id: str,
    initial_state: Optional[Dict[str, Any]] = None,
    checkpoint_id: Optional[str] = None
) -> None:
    """
    Executes the LangGraph pipeline in a worker process with production-hardened streaming.
    Uses Redis-based atomic sequencing, token batching, and heartbeats.
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    if checkpoint_id:
        config["configurable"]["checkpoint_id"] = checkpoint_id

    # Traceability
    request_id = (initial_state or {}).get("request_id", "worker-task")
    # Isolated Channel: thread + request
    channel = f"pipeline_stream:{thread_id}:{request_id}"
    seq_key = f"seq:{thread_id}"
    
    # Ensure sequence starts fresh for new runs, or continues for resumes
    r = get_worker_redis()
    try:
        if initial_state is not None:
            await r.delete(seq_key)
    except Exception as e:
        logger.warning(f"Worker: Redis delete seq failed: {e}")

    local_seq = 0
    async def get_next_seq() -> int:
        nonlocal local_seq
        try:
            return await r.incr(seq_key)
        except Exception as e:
            logger.warning(f"Worker: Redis incr seq failed (using local fallback): {e}")
            local_seq += 1
            return local_seq

    # Metrics & Timing State
    start_time = time.time()
    first_token_time: Optional[float] = None
    total_tokens_emitted = 0

    # Token Batching State (Adaptive with Hard Limits)
    token_buffer: List[str] = []
    last_flush_time = time.time()
    current_node = "startup"

    redis_degraded_notified = False
    async def emit_event(event_str: str):
        """Publish event and store in Redis history for Alpha replay with Fail-Open."""
        nonlocal redis_degraded_notified
        try:
            r = get_worker_redis()
            await r.publish(channel, event_str)
            history_key = f"history:{thread_id}"
            await r.rpush(history_key, event_str)
            await r.ltrim(history_key, -settings.alpha_sse_history_max, -1)
            await r.expire(history_key, settings.alpha_sse_history_ttl)
        except Exception as e:
            if not redis_degraded_notified:
                logger.error(f"Worker: REDIS CONNECTION LOST (Degraded Mode Active): {e}")
                redis_degraded_notified = True
                # We can't publish the warning if Redis is down, but we log it for audit.

    async def flush_tokens(node: str = None):
        if not token_buffer:
            return
        
        nonlocal first_token_time, total_tokens_emitted
        if first_token_time is None:
            first_token_time = time.time()

        content = "".join(token_buffer)
        total_tokens_emitted += len(token_buffer)
        token_buffer.clear()
        
        seq = await get_next_seq()
        event = token_event(thread_id, request_id, seq, content, node or current_node)
        await emit_event(event)
        nonlocal last_flush_time
        last_flush_time = time.time()

    # Heartbeat task to keep connection alive with full metadata
    async def heartbeat_loop():
        try:
            while True:
                await asyncio.sleep(5)
                seq = await get_next_seq()
                await emit_event(heartbeat_event(thread_id, request_id, seq))
        except asyncio.CancelledError:
            pass

    heartbeat_task = asyncio.create_task(heartbeat_loop())

    logger.info(f"Worker: Starting pipeline for thread {thread_id} [Req: {request_id}]")

    try:
        inputs = initial_state if initial_state is not None else {}
        # Inject budget parameters for ExecutionLayer fallback
        inputs["current_job_id"] = thread_id # Using thread_id as job_id
        inputs["current_state_cost"] = inputs.get("total_cost_cents", 0.0)
        
        # 1. Hybrid Streaming (5-minute guard)
        async with asyncio.timeout(300): # 5-minute safety limit
            stream = graph.astream(inputs, config, stream_mode=["messages", "updates"])
            
            async for mode, payload in stream:
                # Handle Tokens (Real-time feedback)
                if mode == "messages":
                    message_chunk, metadata = payload
                    if isinstance(message_chunk, AIMessageChunk):
                        current_node = metadata.get("langgraph_node", current_node)
                        token_buffer.append(message_chunk.content)
                        
                        # Adaptive Batching: max 20 tokens OR 200ms delay
                        time_since_flush = time.time() - last_flush_time
                        if len(token_buffer) >= 20 or time_since_flush >= 0.2:
                            await flush_tokens(current_node)

                # Handle Node Completion
                elif mode == "updates":
                    await flush_tokens()
                    
                    for node_name, state_update in payload.items():
                        # Emit explicit node completion
                        seq = await get_next_seq()
                        await emit_event(node_complete_event(thread_id, request_id, seq, node_name))
                        
                        # Use legacy formatter for backward compat state updates (cost/stages)
                        seq = await get_next_seq()
                        for sse_line in format_state_update_as_sse({node_name: state_update}, thread_id, request_id, seq):
                            if sse_line.strip():
                                await emit_event(sse_line)
                                seq = await get_next_seq()

                        # Progress visibility: predict next node or emit generic progress
                        # In LangGraph, we can't easily see the *next* node before it starts in astream()
                        # so we emit progress when the *current* node finishes based on common flow.
                        progress_map = {
                            "trend_research": "Analyzing trends...",
                            "idea_generation": "Brainstorming ideas...",
                            "hook_creation": "Crafting hooks...",
                            "deep_research": "Deep diving into data...",
                            "script_drafting": "Writing script...",
                        }
                        if node_name in progress_map:
                            seq = await get_next_seq()
                            await emit_event(json.dumps({
                                "thread_id": thread_id,
                                "request_id": request_id,
                                "seq": seq,
                                "type": "progress",
                                "message": progress_map[node_name]
                            }))

        # 2. Final Flush & Metrics
        await flush_tokens()
        heartbeat_task.cancel()
        
        # Calculate final metrics
        end_time = time.time()
        ttft = (first_token_time - start_time) * 1000 if first_token_time else 0
        total_latency = (end_time - start_time) * 1000
        tps = total_tokens_emitted / (end_time - first_token_time) if first_token_time and end_time > first_token_time else 0
        
        # Emit final metrics event
        state = await graph.aget_state(config)
        final_cost = (state.values or {}).get("total_cost_cents", 0.0) if state else 0.0
        
        seq = await get_next_seq()
        seq = await get_next_seq()
        await emit_event(metrics_event(thread_id, request_id, seq, ttft, total_latency, tps, final_cost))

        # 3. Standardized Termination
        status = "success"
        if state and state.values:
            if not state.values.get("should_terminate"):
                status = "interrupted"
                # Emit interrupt event as before
                interrupt_data = get_interrupt_data(state.values)
                seq = await get_next_seq()
                event = interrupt_event(
                    thread_id=thread_id,
                    request_id=request_id,
                    seq=seq,
                    stage=state.values.get("current_stage", "unknown"),
                    message=interrupt_data.get("message", ""),
                    data=interrupt_data.get("current_output"),
                )
                await emit_event(event)

        seq = await get_next_seq()
        await emit_event(stream_end_event(thread_id, request_id, seq, status))

    except asyncio.TimeoutError:
        logger.error(f"Worker: Execution Timeout for thread {thread_id}")
        seq = await get_next_seq()
        await emit_event(error_event(thread_id, request_id, seq, "Execution timed out", error_type="TIMEOUT", recoverable=False))
    except Exception as e:
        logger.exception(f"Worker error in thread {thread_id}: {e}")
        seq = await get_next_seq()
        await emit_event(error_event(thread_id, request_id, seq, str(e), recoverable=False))
    finally:
        await flush_tokens()
        if not heartbeat_task.done():
            heartbeat_task.cancel()
            
        logger.info(f"Worker: Finished pipeline for thread {thread_id}")

@broker.task(task_name="run_shadow_generation")
async def run_shadow_generation_task(
    state_values: Dict[str, Any],
    config: Dict[str, Any]
) -> None:
    try:
        from app.pipeline.shadow import trigger_shadow_script_generation
        await trigger_shadow_script_generation(state_values, config)
    except Exception as e:
        logger.error(f"Worker: Shadow generation failed: {e}")

@broker.on_event("startup")
async def startup():
    from app.models.database import init_db
    await init_db()
    await init_infrastructure()
    
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda: logger.warning(f"Worker: Received signal {sig.name}. Shutting down..."))
        except NotImplementedError:
            pass
            
    logger.info("Worker: Database initialized and signal handlers registered.")


@broker.on_event("shutdown")
async def shutdown():
    from app.models.database import close_db
    await close_db()
    await close_infrastructure()
    logger.info("Worker: Database connection closed and shutdown complete.")

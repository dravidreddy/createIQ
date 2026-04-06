from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
import json
import redis.asyncio as redis

from app.api.deps import get_current_user
from app.models.user import User
from app.config import get_settings

router = APIRouter()
settings = get_settings()

@router.get("/{thread_id}/history")
async def get_pipeline_history(
    thread_id: str,
    last_seq: int = -1,
    current_user: User = Depends(get_current_user)
):
    """
    Returns events from Redis sliding-window history where seq > last_seq.
    Used for Alpha Readiness SSE recovery.
    """
    r = redis.from_url(settings.redis_url, decode_responses=True)
    history_key = f"history:{thread_id}"
    
    try:
        # 1. Fetch all events
        events_raw = await r.lrange(history_key, 0, -1)
        if not events_raw:
            return {"thread_id": thread_id, "events": [], "count": 0, "status": "empty"}
            
        events = []
        oldest_seq = float('inf')
        for e in events_raw:
            try:
                evt = json.loads(e)
                seq = evt.get("seq", -1)
                if seq < oldest_seq: oldest_seq = seq
                if seq > last_seq:
                    events.append(evt)
            except (json.JSONDecodeError, TypeError):
                continue
                
        # 2. Out-of-Sync Detection
        # If client's last_seq is NOT -1 AND it's older than our oldest visible event, 
        # it means they missed a gap of events we no longer have in our sliding window.
        status = "ok"
        if last_seq != -1 and oldest_seq != float('inf') and last_seq < oldest_seq - 1:
            status = "out_of_sync"
            
        # 3. Sort and Return
        events.sort(key=lambda x: x.get("seq", 0))
        
        return {
            "thread_id": thread_id,
            "events": events,
            "count": len(events),
            "status": status,
            "oldest_seq_available": oldest_seq if oldest_seq != float('inf') else None,
            "last_seq_returned": events[-1].get("seq") if events else last_seq
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History recovery failed: {str(e)}")
    finally:
        await r.close()

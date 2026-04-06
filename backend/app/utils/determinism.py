"""
Determinism Utility — Intercepts non-deterministic functions in TEST_MODE.
"""

import uuid
import time
from datetime import datetime, timezone
from app.config import get_settings

settings = get_settings()

FIXED_TIME = 1712316403.0  # 2026-04-05T11:26:43Z
FIXED_UUID = "00000000-0000-4000-a000-000000000000"

def get_now() -> datetime:
    if settings.test_mode:
        return datetime.fromtimestamp(FIXED_TIME, tz=timezone.utc)
    return datetime.now(timezone.utc)

def get_uuid() -> str:
    if settings.test_mode:
        return FIXED_UUID
    return str(uuid.uuid4())

def get_time() -> float:
    if settings.test_mode:
        return FIXED_TIME
    return time.time()

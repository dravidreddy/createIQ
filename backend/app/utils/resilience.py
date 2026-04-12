import asyncio
import random
import time
import functools
from typing import Callable, Any, Optional
from fastapi import Request
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging
from app.utils.logging import logger

def retry_with_backoff(
    max_attempts: int = 2,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retry_on: tuple = (Exception,)
):
    """
    Standardized retry decorator with exponential backoff.
    Default: 2 attempts (1 retry).
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=base_delay, max=max_delay),
        retry=retry_if_exception_type(retry_on),
        before_sleep=before_sleep_log(logger, logging.INFO),
        reraise=True
    )

class FailureSimulator:
    """
    Utility to simulate production failures based on request headers.
    Used for resilience testing (Phase 8.2).
    """
    
    @staticmethod
    async def simulate_from_request(request: Request):
        from app.config import get_settings
        settings = get_settings()
        if not settings.debug and settings.env != "development":
            return
            
        # 1. Latency Simulation
        delay_ms = request.headers.get("X-Simulate-Delay")
        if delay_ms:
            delay_sec = int(delay_ms) / 1000.0
            logger.warning(f"SIMULATION: Injecting latency of {delay_ms}ms")
            await asyncio.sleep(delay_sec)
            
        # 2. Error Simulation
        error_code = request.headers.get("X-Simulate-Error")
        if error_code:
            logger.warning(f"SIMULATION: Injecting error {error_code}")
            if error_code == "500":
                raise Exception("SIMULATED_INTERNAL_ERROR")
            if error_code == "timeout":
                await asyncio.sleep(60) # Force gateway timeout
                
        # 3. Flaky Connection Simulation
        flakiness = request.headers.get("X-Simulate-Flaky")
        if flakiness and random.random() < float(flakiness):
            logger.warning("SIMULATION: Injecting flaky failure")
            raise ConnectionError("SIMULATED_CONNECTION_FLAKY")

def resilience_gate(func: Callable):
    """
    Wrapper to apply failure simulation to any async route handler.
    Expects 'request' as one of the arguments.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        if request:
            await FailureSimulator.simulate_from_request(request)
        return await func(*args, **kwargs)
    return wrapper

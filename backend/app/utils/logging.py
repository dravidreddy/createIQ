import logging
import sys
import time
from typing import Dict, Any
from contextvars import ContextVar
from pythonjsonlogger import json as jsonlogger

# Centralized Trace ID for observability and response wrapping
trace_var: ContextVar[str] = ContextVar("trace_id", default="system")

class TracingFilter(logging.Filter):
    """Filter that injects trace_id from ContextVar into all log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_var.get()
        return True

def setup_logging():
    """Centralized structured JSON logging configuration."""
    logger = logging.getLogger("CreatorIQ")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        # Structured JSON Format
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(trace_id)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ"
        )
        
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.addFilter(TracingFilter())
        
    # Silence third-party noise
    logging.getLogger("uvicorn.access").propagate = False
    
    return logger

# Initialize and export project-wide logger
logger = setup_logging()

class RateLimitedLogger:
    """Utility to prevent log flooding by suppressing repeated messages."""
    def __init__(self, name: str, interval: float = 60.0):
        self.logger = logging.getLogger(name)
        self.interval = interval
        self.last_logged: Dict[str, float] = {}

    def log(self, level: int, msg: str, key: str = None):
        """Log a message only if it hasn't been logged within the interval."""
        cache_key = key or msg
        now = time.time()
        
        if cache_key not in self.last_logged or (now - self.last_logged[cache_key]) > self.interval:
            self.logger.log(level, msg)
            self.last_logged[cache_key] = now

    def error(self, msg: str, key: str = None):
        self.log(logging.ERROR, msg, key)

    def warning(self, msg: str, key: str = None):
        self.log(logging.WARNING, msg, key)

    def info(self, msg: str, key: str = None):
        self.log(logging.INFO, msg, key)

    def critical(self, msg: str, key: str = None):
        self.log(logging.CRITICAL, msg, key)

# Export a default rate-limited logger for infra
infra_logger = RateLimitedLogger("CreatorIQ.Infra", interval=60.0)

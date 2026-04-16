from datetime import datetime, UTC

def utc_now() -> datetime:
    """Returns a timezone-aware datetime object for the current UTC time."""
    return datetime.now(UTC)

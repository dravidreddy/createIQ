#!/bin/bash

# Force unbuffered output so logs appear immediately in cloud console
export PYTHONUNBUFFERED=1

# Single-process deployment: pipeline runs as asyncio background tasks inside uvicorn.
# TaskIQ worker is NOT needed — run_pipeline_async() is called via asyncio.create_task().
echo "Starting CreatorIQ Backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

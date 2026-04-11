#!/bin/bash

# Force python to not buffer stdout/stderr so logs appear instantly
export PYTHONUNBUFFERED=1

# Start the TaskIQ background worker (Limit to 1 process to avoid Docker OOM kill)
echo "Starting TaskIQ Background Worker..."
taskiq worker app.worker:broker -w 1 --max-async-tasks 20 &

# Start the Uvicorn FastAPI web server in the FOREGROUND
echo "Starting FastAPI Web Server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

#!/bin/bash

# Start the TaskIQ background worker (Limit to 1 process to avoid Docker OOM kill)
echo "Starting TaskIQ Background Worker..."
taskiq worker app.worker:broker -w 1 --max-async-tasks 20 &
WORKER_PID=$!

# Start the Uvicorn FastAPI web server
echo "Starting FastAPI Web Server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
WEB_PID=$!

# Wait for any process to exit (if either fails, the container accurately crashes for cloud restart)
wait -n

# Exit with the status of the process that exited first
exit $?

#!/bin/bash
set -e

# Start FastAPI backend on port 8000
cd /app/backend
uvicorn main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Start Next.js on the main port (8080 for Cloud Run)
cd /app/frontend-standalone
export PORT=8080
export HOSTNAME=0.0.0.0
export API_URL=http://localhost:8000
node server.js &
NEXTJS_PID=$!

# Wait for either to exit
wait $FASTAPI_PID $NEXTJS_PID

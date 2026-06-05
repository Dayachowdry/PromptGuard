# PromptGuard Demo — Multi-stage Dockerfile
# Stage 1: Build Next.js frontend
# Stage 2: Python FastAPI serving both API + frontend

# ── Stage 1: Build frontend ──────────────────────────────────────────
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --production=false
COPY frontend/ .
RUN npm run build

# ── Stage 2: Python API + static frontend ─────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install Python deps
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy built frontend (standalone Next.js)
COPY --from=frontend-builder /app/frontend/.next/standalone ./frontend-standalone/
COPY --from=frontend-builder /app/frontend/.next/static ./frontend-standalone/.next/static/
COPY --from=frontend-builder /app/frontend/public ./frontend-standalone/public/

# Install Node.js for Next.js standalone server
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Startup script: run both FastAPI + Next.js
COPY <<'EOF' /app/start.sh
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
EOF

RUN chmod +x /app/start.sh

EXPOSE 8080

CMD ["/app/start.sh"]

# PromptGuard Demo — Single-stage Dockerfile
# Frontend is pre-built locally; this image just serves API + frontend

FROM python:3.12-slim

WORKDIR /app

# Install Node.js 22 for Next.js standalone server
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy pre-built frontend (standalone Next.js output)
COPY frontend/.next/standalone ./frontend-standalone/
COPY frontend/.next/static ./frontend-standalone/.next/static/
COPY frontend/public ./frontend-standalone/public/

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8080

CMD ["/app/start.sh"]

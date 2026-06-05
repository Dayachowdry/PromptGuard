# PromptGuard Demo — Python-only Dockerfile
# Frontend is a pre-built Next.js static export served by FastAPI

FROM python:3.12-slim

WORKDIR /app

# Install Python deps
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy pre-built frontend static export
COPY frontend/out/ ./frontend-static/

EXPOSE 8080

WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

"""PromptGuard API — Identity-First Zero Trust Access Control for LLMs.

FastAPI backend that demonstrates the PromptGuard architecture:
- Persona-based trust levels (5 tiers)
- Dynamic system prompt injection
- Multi-model support (Claude, GPT, Gemini)
- Compare mode (same query across all trust levels)
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from models import (
    QueryRequest,
    CompareRequest,
    QueryResponse,
    CompareResponse,
    Persona,
    ExampleQuery,
)
from trust import get_persona, get_all_personas, get_all_examples, PERSONAS
from gateway import process_query, process_compare, MODELS


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    print("PromptGuard API starting...")
    print(f"  Models: {', '.join(f'{k} ({v['name']})' for k, v in MODELS.items())}")
    print(f"  Personas: {', '.join(PERSONAS.keys())}")

    # Check for API keys
    for key_name in ["ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
        if os.environ.get(key_name):
            print(f"  {key_name}: configured")
        else:
            print(f"  {key_name}: NOT SET — {key_name.split('_')[0].lower()} calls will fail")

    yield
    print("PromptGuard API shutting down.")


app = FastAPI(
    title="PromptGuard",
    description="Identity-First Zero Trust Access Control for LLMs",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API Routes ────────────────────────────────────────────────────────


@app.get("/api/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "promptguard"}


@app.get("/api/personas", response_model=list[Persona])
async def list_personas():
    """List all available personas with trust info."""
    return [Persona(**p) for p in get_all_personas()]


@app.get("/api/examples", response_model=list[ExampleQuery])
async def list_examples():
    """List pre-loaded example queries."""
    return [ExampleQuery(**e) for e in get_all_examples()]


@app.get("/api/models")
async def list_models():
    """List available LLM backends."""
    return {
        k: {"name": v["name"], "model_id": v["model_id"]}
        for k, v in MODELS.items()
    }


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Process a single query through PromptGuard.

    Takes a persona + query + model, enriches the prompt with
    identity-driven access controls, and returns the LLM response.
    """
    try:
        result = await process_query(
            persona_id=request.persona,
            query=request.query,
            model_key=request.model,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {str(e)}")


@app.post("/api/compare", response_model=CompareResponse)
async def compare(request: CompareRequest):
    """Compare mode — process the same query across all 5 trust levels.

    Fires all 5 LLM calls in parallel and returns results for each persona.
    """
    try:
        results = await process_compare(
            query=request.query,
            model_key=request.model,
        )
        return CompareResponse(
            query=request.query,
            model_used=MODELS.get(request.model, {}).get("name", "Unknown"),
            results=results,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compare failed: {str(e)}")


# ── Static file serving (frontend) ───────────────────────────────────

# In Docker, frontend/out is copied to /app/frontend-static
# Locally, it's at ../frontend/out relative to this file
FRONTEND_DIR = Path("/app/frontend-static")
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "out"

if FRONTEND_DIR.exists():
    # Mount _next directory for JS/CSS assets
    next_dir = FRONTEND_DIR / "_next"
    if next_dir.exists():
        app.mount("/_next", StaticFiles(directory=next_dir), name="nextjs-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the Next.js static export."""
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # SPA fallback
        index = FRONTEND_DIR / "index.html"
        if index.exists():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

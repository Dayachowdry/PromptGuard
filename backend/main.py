"""PromptGuard API — Identity-First Zero Trust Access Control for LLMs.

FastAPI backend that demonstrates the PromptGuard architecture:
- Persona-based trust levels (5 tiers)
- Dynamic system prompt injection
- Multi-model support (Claude, GPT, Gemini)
- Compare mode (same query across all trust levels)
"""

import os
import logging
import secrets
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from models import (
    QueryRequest,
    CompareRequest,
    QueryResponse,
    CompareResponse,
    Persona,
    ExampleQuery,
    LoginRequest,
)
from trust import get_all_personas, get_all_examples, PERSONAS
from gateway import process_query, process_compare, MODELS, get_public_models


logger = logging.getLogger(__name__)
SESSION_COOKIE_NAME = "promptguard_access"


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


def _get_allowed_origins() -> list[str]:
    configured = os.environ.get("ALLOWED_ORIGINS", "")
    if configured.strip():
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return []


def _is_auth_enabled() -> bool:
    return bool(os.environ.get("PROMPTGUARD_ACCESS_CODE"))


def _is_authenticated(request: Request) -> bool:
    if not _is_auth_enabled():
        return True
    cookie_value = request.cookies.get(SESSION_COOKIE_NAME, "")
    access_code = os.environ.get("PROMPTGUARD_ACCESS_CODE", "")
    return bool(cookie_value) and secrets.compare_digest(cookie_value, access_code)


def _apply_security_headers(response, path: str):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store" if path.startswith("/api/") else "public, max-age=300"
    return response


allowed_origins = _get_allowed_origins()
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.url.path not in {
        "/api/health",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/session",
    }:
        if not _is_authenticated(request):
            return _apply_security_headers(
                JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required."},
                ),
                request.url.path,
            )

    response = await call_next(request)
    return _apply_security_headers(response, request.url.path)


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
    return get_public_models()


@app.get("/api/auth/session")
async def auth_session(request: Request):
    """Report whether the current browser session is authenticated."""
    return {"authenticated": _is_authenticated(request)}


@app.post("/api/auth/login")
async def auth_login(request: Request, payload: LoginRequest):
    """Exchange a static access code for an authenticated browser session."""
    if not _is_auth_enabled():
        return {"authenticated": True}

    access_code = os.environ.get("PROMPTGUARD_ACCESS_CODE", "")
    if not secrets.compare_digest(payload.code, access_code):
        raise HTTPException(status_code=401, detail="Invalid access code.")

    response = JSONResponse({"authenticated": True})
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=access_code,
        httponly=True,
        samesite="lax",
        secure=bool(os.environ.get("K_SERVICE")) or request.url.scheme == "https",
        max_age=60 * 60 * 24 * 7,
    )
    return response


@app.post("/api/auth/logout")
async def auth_logout():
    """Clear the authenticated browser session."""
    response = JSONResponse({"authenticated": False})
    response.delete_cookie(SESSION_COOKIE_NAME, httponly=True, samesite="lax")
    return response


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
    except Exception:
        logger.exception("Unhandled error during single-query request")
        raise HTTPException(status_code=500, detail="The model request failed.")


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
    except Exception:
        logger.exception("Unhandled error during compare request")
        raise HTTPException(status_code=500, detail="The compare request failed.")


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

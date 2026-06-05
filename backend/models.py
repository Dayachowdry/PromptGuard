"""Pydantic models for PromptGuard API."""

from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    """Single query request."""
    persona: str = Field(..., description="Persona ID: intern, sales, developer, director, pentester")
    query: str = Field(..., description="User query to send to the LLM")
    model: str = Field(default="claude", description="LLM backend: claude, gpt, gemini")


class CompareRequest(BaseModel):
    """Compare mode request — same query across all trust levels."""
    query: str = Field(..., description="User query to compare across all personas")
    model: str = Field(default="claude", description="LLM backend: claude, gpt, gemini")


class TrustInfo(BaseModel):
    """Trust level metadata returned with responses."""
    persona_id: str
    persona_title: str
    level: int
    score: int
    query_limit: int
    allowed: list[str]
    blocked: list[str]
    directive: str


class QueryResponse(BaseModel):
    """Response from a single query."""
    response: str
    trust_info: TrustInfo
    system_prompt: str
    model_used: str
    query_truncated: bool = False


class CompareResponse(BaseModel):
    """Response from compare mode — all 5 trust levels."""
    query: str
    model_used: str
    results: list[QueryResponse]


class Persona(BaseModel):
    """Persona definition for the UI."""
    id: str
    title: str
    description: str
    level: int
    score: int
    color: str
    icon: str
    allowed: list[str]
    blocked: list[str]


class ExampleQuery(BaseModel):
    """Pre-loaded example query."""
    id: int
    text: str
    category: str

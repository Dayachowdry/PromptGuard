"""PromptGuard Gateway — core proxy logic.

Enriches user queries with identity-driven system prompts and routes
to the selected LLM backend. Supports Claude, GPT, and Gemini.
"""

import os
import json
import asyncio

import anthropic
from google import genai
from openai import AsyncOpenAI

from trust import get_persona
from templates import build_system_prompt
from models import QueryResponse, TrustInfo


# ── Model configuration ──────────────────────────────────────────────

MODELS = {
    "claude": {
        "name": "Claude Haiku",
        "model_id": "claude-haiku-4-5-20251001",
        "provider": "anthropic",
    },
    "gpt": {
        "name": "GPT-4o Mini",
        "model_id": "gpt-4o-mini",
        "provider": "openai",
    },
    "gemini": {
        "name": "Gemini 3.5 Flash",
        "model_id": "gemini-3.5-flash",
        "provider": "google",
    },
}


# ── LLM Clients (lazy-initialized) ───────────────────────────────────

_anthropic_client = None
_openai_client = None
_gemini_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
    return _anthropic_client


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY")
        )
    return _openai_client


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(
            api_key=os.environ.get("GOOGLE_API_KEY")
        )
    return _gemini_client


# ── Core Gateway Logic ────────────────────────────────────────────────

async def process_query(
    persona_id: str,
    query: str,
    model_key: str = "claude",
) -> QueryResponse:
    """Process a single query through the PromptGuard pipeline.

    1. Look up persona → trust level
    2. Build enriched system prompt
    3. Enforce query length limit
    4. Call LLM with enriched context
    5. Return response + metadata
    """
    persona = get_persona(persona_id)
    if not persona:
        raise ValueError(f"Unknown persona: {persona_id}")

    model_config = MODELS.get(model_key)
    if not model_config:
        raise ValueError(f"Unknown model: {model_key}. Options: claude, gpt, gemini")

    # Build the enriched system prompt (the core of PromptGuard)
    system_prompt = build_system_prompt(persona)

    # Enforce query length limit (0 = unlimited)
    query_truncated = False
    if persona["query_limit"] > 0 and len(query) > persona["query_limit"]:
        query = query[: persona["query_limit"]]
        query_truncated = True

    # Route to the appropriate LLM backend
    response_text = await _call_llm(
        model_key=model_key,
        model_config=model_config,
        system_prompt=system_prompt,
        user_query=query,
    )

    # Build trust info for the response
    trust_info = TrustInfo(
        persona_id=persona["id"],
        persona_title=persona["title"],
        level=persona["level"],
        score=persona["score"],
        query_limit=persona["query_limit"],
        allowed=persona["allowed"],
        blocked=persona["blocked"],
        directive=persona["directive"],
    )

    return QueryResponse(
        response=response_text,
        trust_info=trust_info,
        system_prompt=system_prompt,
        model_used=model_config["name"],
        query_truncated=query_truncated,
    )


async def process_compare(
    query: str,
    model_key: str = "claude",
) -> list[QueryResponse]:
    """Process a query across all 5 trust levels simultaneously.

    Fires all 5 LLM calls in parallel for speed.
    """
    persona_ids = ["intern", "sales", "developer", "director", "pentester"]

    tasks = [
        process_query(persona_id=pid, query=query, model_key=model_key)
        for pid in persona_ids
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert exceptions to error responses
    responses = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            persona = get_persona(persona_ids[i])
            responses.append(
                QueryResponse(
                    response=f"Error: {str(result)}",
                    trust_info=TrustInfo(
                        persona_id=persona_ids[i],
                        persona_title=persona["title"] if persona else "Unknown",
                        level=persona["level"] if persona else 0,
                        score=persona["score"] if persona else 0,
                        query_limit=persona["query_limit"] if persona else 0,
                        allowed=persona["allowed"] if persona else [],
                        blocked=persona["blocked"] if persona else [],
                        directive=persona["directive"] if persona else "",
                    ),
                    system_prompt="",
                    model_used=MODELS.get(model_key, {}).get("name", "Unknown"),
                )
            )
        else:
            responses.append(result)

    return responses


# ── LLM Backend Calls ─────────────────────────────────────────────────

async def _call_llm(
    model_key: str,
    model_config: dict,
    system_prompt: str,
    user_query: str,
) -> str:
    """Route to the appropriate LLM backend."""
    provider = model_config["provider"]

    if provider == "anthropic":
        return await _call_claude(model_config["model_id"], system_prompt, user_query)
    elif provider == "openai":
        return await _call_gpt(model_config["model_id"], system_prompt, user_query)
    elif provider == "google":
        return await _call_gemini(model_config["model_id"], system_prompt, user_query)
    else:
        raise ValueError(f"Unknown provider: {provider}")


async def _call_claude(model_id: str, system_prompt: str, user_query: str) -> str:
    """Call Claude via Anthropic SDK."""
    client = _get_anthropic_client()
    response = await client.messages.create(
        model=model_id,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_query}],
    )
    return response.content[0].text


async def _call_gpt(model_id: str, system_prompt: str, user_query: str) -> str:
    """Call GPT via OpenAI SDK."""
    client = _get_openai_client()
    response = await client.chat.completions.create(
        model=model_id,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
    )
    return response.choices[0].message.content


async def _call_gemini(model_id: str, system_prompt: str, user_query: str) -> str:
    """Call Gemini via Google GenAI SDK."""
    client = _get_gemini_client()

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model_id,
        contents=user_query,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=1024,
        ),
    )
    return response.text

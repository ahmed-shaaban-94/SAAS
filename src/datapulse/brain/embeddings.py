"""OpenRouter embedding client for Brain semantic search.

Lightweight and standalone — reads env vars directly, no Settings dependency.
Returns None on any failure so callers can fall back to FTS.
"""

from __future__ import annotations

import os

import httpx

OPENROUTER_EMBED_URL = "https://openrouter.ai/api/v1/embeddings"
DEFAULT_EMBED_MODEL = "openai/text-embedding-3-small"  # $0.02/1M tokens
EMBED_TIMEOUT = 10  # seconds


def get_embedding(text: str) -> list[float] | None:
    """Generate a 1536-dim embedding via OpenRouter.

    Returns None if:
    - OPENROUTER_API_KEY is not set
    - The API call fails for any reason
    - The response is malformed
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return None

    model = os.environ.get("BRAIN_EMBED_MODEL", DEFAULT_EMBED_MODEL)

    # Truncate very long texts to ~8000 tokens (~32000 chars) to stay within
    # model limits and keep costs low.
    max_chars = 32_000
    if len(text) > max_chars:
        text = text[:max_chars]

    try:
        resp = httpx.post(
            OPENROUTER_EMBED_URL,
            json={"model": model, "input": text},
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://datapulse.dev",
                "X-Title": "DataPulse Brain",
            },
            timeout=EMBED_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]
    except Exception:
        # Non-critical — FTS still works without embeddings.
        return None

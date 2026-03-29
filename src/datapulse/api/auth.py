"""Authentication and authorization dependencies for the FastAPI API.

Provides lightweight API-key and webhook-token guards.
When the corresponding config value is empty, the guard is skipped (dev mode).
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from datapulse.config import Settings, get_settings

# Header schemes (auto_error=False so we control the error message)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_pipeline_token_header = APIKeyHeader(name="X-Pipeline-Token", auto_error=False)


def require_api_key(
    api_key: str | None = Security(_api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    """Verify the X-API-Key header matches the configured api_key.

    Skips validation when ``settings.api_key`` is empty (dev / local mode).
    """
    if not settings.api_key:
        return  # dev mode — no auth required
    if not api_key or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def require_pipeline_token(
    token: str | None = Security(_pipeline_token_header),
    settings: Settings = Depends(get_settings),
) -> None:
    """Verify the X-Pipeline-Token header for pipeline execution endpoints.

    Skips validation when ``settings.pipeline_webhook_secret`` is empty.
    """
    if not settings.pipeline_webhook_secret:
        return  # dev mode — no token required
    if not token or token != settings.pipeline_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid or missing pipeline token")

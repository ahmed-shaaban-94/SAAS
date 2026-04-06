"""Embed API endpoints — token generation and embedded data access.

Provides endpoints for:
- Generating scoped embed tokens (authenticated users)
- Accessing data via embed tokens (no session required, for iframes)
"""

from __future__ import annotations

from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.limiter import limiter
from datapulse.core.db import get_session_factory
from datapulse.embed.token import create_embed_token, validate_embed_token
from datapulse.explore.manifest_parser import build_catalog
from datapulse.explore.models import ExploreQuery, ExploreResult
from datapulse.explore.sql_builder import build_sql
from datapulse.logging import get_logger

log = get_logger(__name__)


# ------------------------------------------------------------------
# Authenticated endpoints (token generation)
# ------------------------------------------------------------------

auth_router = APIRouter(
    prefix="/embed",
    tags=["embed"],
    dependencies=[Depends(get_current_user)],
)


class EmbedTokenRequest(BaseModel):
    """Request body for generating an embed token."""

    resource_type: str = Field("explore", description="Type of resource to embed")
    resource_id: str = Field("", description="Specific resource ID (optional)")
    expires_hours: int = Field(8, ge=1, le=72, description="Token lifetime in hours")


class EmbedTokenResponse(BaseModel):
    """Response with the generated embed token."""

    token: str
    expires_hours: int


@auth_router.post("/token", response_model=EmbedTokenResponse)
@limiter.limit("30/minute")
def generate_embed_token(
    request: Request,
    body: EmbedTokenRequest,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> EmbedTokenResponse:
    """Generate a scoped embed token for iframe embedding."""
    tenant_id = user.get("tenant_id", "1")
    token = create_embed_token(
        tenant_id=tenant_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        expires_hours=body.expires_hours,
    )
    return EmbedTokenResponse(token=token, expires_hours=body.expires_hours)


# ------------------------------------------------------------------
# Public endpoints (token-authenticated, no session needed)
# ------------------------------------------------------------------

public_router = APIRouter(
    prefix="/embed",
    tags=["embed-public"],
)


def _get_embed_session(token_payload: dict) -> Session:
    """Create a DB session scoped to the embed token's tenant."""
    tenant_id = token_payload.get("tenant_id", "1")
    session = get_session_factory()()
    session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
    session.execute(text("SET LOCAL statement_timeout = '30s'"))
    return session


@public_router.post("/{token}/query", response_model=ExploreResult)
@limiter.limit("60/minute")
def embed_query(
    request: Request,
    token: str,
    body: ExploreQuery,
) -> ExploreResult:
    """Execute an explore query via embed token (no session auth needed).

    Validates the embed token, then runs the query with tenant-scoped RLS.
    """
    import time

    from datapulse.config import get_settings

    try:
        payload = validate_embed_token(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired embed token") from exc

    session = _get_embed_session(payload)
    try:
        settings = get_settings()
        catalog = build_catalog(f"{settings.dbt_project_dir}/models")

        sql, params = build_sql(body, catalog)

        start = time.perf_counter()
        result = session.execute(text(sql), params)
        columns = list(result.keys())
        rows: list[list] = []
        truncated = False

        for i, row in enumerate(result):
            if i >= body.limit:
                truncated = True
                break
            rows.append([_serialise(v) for v in row])

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        log.info("embed_query_executed", row_count=len(rows), duration_ms=duration_ms)

        # Never expose SQL in embed responses — these are public-facing
        return ExploreResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            sql="",
            truncated=truncated,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        session.rollback()
        log.error("embed_query_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Query execution failed") from exc
    finally:
        session.close()


from datapulse.core.serializers import serialise_value as _serialise  # shared utility

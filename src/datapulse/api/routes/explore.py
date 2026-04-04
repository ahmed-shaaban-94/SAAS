"""Explore API endpoints — dbt-powered self-serve analytics.

Provides endpoints for:
- Listing available models with their dimensions/metrics
- Executing explore queries (dimensions + metrics + filters -> SQL -> results)
"""

from __future__ import annotations

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.config import get_settings
from datapulse.explore.manifest_parser import get_catalog as _get_cached_catalog
from datapulse.explore.manifest_parser import invalidate_catalog
from datapulse.explore.models import (
    ExploreCatalog,
    ExploreModel,
    ExploreQuery,
    ExploreResult,
)
from datapulse.explore.sql_builder import build_sql
from datapulse.logging import get_logger

log = get_logger(__name__)

router = APIRouter(
    prefix="/explore",
    tags=["explore"],
    dependencies=[Depends(get_current_user)],
)


def _get_catalog() -> ExploreCatalog:
    """Return the thread-safe cached explore catalog."""
    settings = get_settings()
    return _get_cached_catalog(f"{settings.dbt_project_dir}/models")


def refresh_catalog() -> ExploreCatalog:
    """Force a catalog rebuild (called after pipeline completion)."""
    invalidate_catalog()
    return _get_catalog()


@router.get("/models", response_model=ExploreCatalog)
@limiter.limit("60/minute")
def list_models(request: Request) -> ExploreCatalog:
    """List all available explore models with their dimensions and metrics."""
    return _get_catalog()


@router.get("/models/{model_name}", response_model=ExploreModel)
@limiter.limit("60/minute")
def get_model(request: Request, model_name: str) -> ExploreModel:
    """Get the full schema for a single explore model."""
    catalog = _get_catalog()
    for m in catalog.models:
        if m.name == model_name:
            return m
    raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")


@router.post("/query", response_model=ExploreResult)
@limiter.limit("30/minute")
def execute_explore_query(
    request: Request,
    body: ExploreQuery,
    session: Annotated[Session, Depends(get_tenant_session)],
) -> ExploreResult:
    """Execute an explore query and return results.

    Validates all requested fields against the dbt catalog (whitelist),
    generates parameterised SQL, and executes it against the database.
    Returns both the data and the generated SQL for transparency.
    """
    catalog = _get_catalog()

    # Build SQL from the explore query
    try:
        sql, params = build_sql(body, catalog)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Execute the query
    start = time.perf_counter()
    try:
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

        log.info(
            "explore_query_executed",
            model=body.model,
            row_count=len(rows),
            duration_ms=duration_ms,
        )

        return ExploreResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            sql=sql,
            truncated=truncated,
        )
    except Exception as exc:
        log.error("explore_query_failed", error=str(exc), model=body.model)
        raise HTTPException(
            status_code=500,
            detail="Query execution failed. Check the server logs for details.",
        ) from exc


@router.post("/refresh-catalog", response_model=ExploreCatalog)
@limiter.limit("5/minute")
def refresh_catalog_endpoint(request: Request) -> ExploreCatalog:
    """Force a catalog rebuild from dbt YAML files.

    Called after pipeline completion to pick up new/changed models.
    """
    return refresh_catalog()


def _serialise(value: Any) -> str | int | float | bool | None:
    """Convert a DB value to a JSON-safe primitive."""
    if value is None:
        return None
    from datetime import date, datetime
    from decimal import Decimal

    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float, bool, str)):
        return value
    return str(value)

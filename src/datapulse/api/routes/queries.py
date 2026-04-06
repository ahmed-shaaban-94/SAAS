"""Async query execution API endpoints.

Provides a submit-then-poll pattern for long-running SQL queries:
- ``POST /api/v1/queries`` — submit a query, get back a query_id
- ``GET  /api/v1/queries/{query_id}`` — poll for results

Uses a lightweight asyncio-based executor with Redis job state
instead of Celery, reducing infrastructure complexity.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from datapulse.api.auth import get_current_user
from datapulse.logging import get_logger
from datapulse.tasks.async_executor import get_job_result, submit_query
from datapulse.tasks.models import QueryResponse, QueryResult, QueryStatus, QuerySubmit

log = get_logger(__name__)

router = APIRouter(
    prefix="/queries",
    tags=["queries"],
    dependencies=[Depends(get_current_user)],
)

# Allowlist: only SELECT and WITH (CTE) statements
_ALLOWED_PATTERN = re.compile(
    r"^\s*(SELECT|WITH|EXPLAIN\s+(ANALYZE\s+)?SELECT)\b",
    re.IGNORECASE | re.DOTALL,
)

# Blocklist: dangerous SQL keywords and statements
_BLOCKED_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|EXECUTE|"
    r"DO|CALL|SET(?!\s+LOCAL\s+app\.)|VACUUM|ANALYZE|LOCK|COMMENT|LISTEN|NOTIFY|"
    r"PREPARE|DEALLOCATE)\b",
    re.IGNORECASE,
)


def _validate_sql(sql: str) -> None:
    """Validate that the SQL is a read-only SELECT statement."""
    if not _ALLOWED_PATTERN.match(sql):
        raise HTTPException(
            status_code=422,
            detail="Only SELECT and WITH (CTE) statements are allowed.",
        )
    # Reject statement stacking (semicolon-separated statements)
    if ";" in sql.rstrip().rstrip(";"):
        raise HTTPException(
            status_code=422,
            detail="Multiple SQL statements are not allowed.",
        )
    # Reject SQL comments (potential keyword hiding)
    if "--" in sql or "/*" in sql:
        raise HTTPException(
            status_code=422,
            detail="SQL comments are not allowed in queries.",
        )
    if _BLOCKED_KEYWORDS.search(sql):
        raise HTTPException(
            status_code=422,
            detail="SQL contains disallowed keywords (INSERT, UPDATE, DELETE, DROP, etc.).",
        )


@router.post("", response_model=QueryResponse, status_code=202)
async def submit_query_endpoint(
    body: QuerySubmit,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> QueryResponse:
    """Submit an async SQL query for execution.

    The query is validated for safety (read-only) and dispatched to a
    background thread. Returns a query_id for polling.
    """
    _validate_sql(body.sql)

    tenant_id = user.get("tenant_id", "1")

    job_id = await submit_query(
        sql=body.sql,
        tenant_id=tenant_id,
        row_limit=body.row_limit,
    )

    if job_id is None:
        raise HTTPException(
            status_code=503,
            detail="Query service unavailable (Redis not connected)",
        )

    log.info("query_submitted", query_id=job_id, tenant_id=tenant_id)

    return QueryResponse(
        query_id=job_id,
        status=QueryStatus.pending,
        submitted_at=datetime.now(UTC),
    )


@router.get("/{query_id}", response_model=QueryResult)
def get_query_result_endpoint(query_id: str) -> QueryResult:
    """Poll for async query results.

    Returns the current status and, if complete, the result data.
    """
    data = get_job_result(query_id)
    now = datetime.now(UTC)

    if data is None:
        raise HTTPException(status_code=404, detail="Query not found or expired")

    status = data.get("status", "pending")

    if status == "complete":
        return QueryResult(
            query_id=query_id,
            status=QueryStatus.complete,
            submitted_at=now,
            completed_at=now,
            columns=data.get("columns", []),
            rows=data.get("rows", []),
            row_count=data.get("row_count", 0),
            truncated=data.get("truncated", False),
            duration_ms=data.get("duration_ms"),
        )

    if status == "failed":
        return QueryResult(
            query_id=query_id,
            status=QueryStatus.failed,
            submitted_at=now,
            error=data.get("error", "Query execution failed"),
        )

    # pending or running
    mapped = QueryStatus.running if status == "running" else QueryStatus.pending
    return QueryResult(
        query_id=query_id,
        status=mapped,
        submitted_at=now,
    )

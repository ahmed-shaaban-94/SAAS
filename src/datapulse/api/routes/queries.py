"""Async query execution API endpoints.

Provides a submit-then-poll pattern for long-running SQL queries:
- ``POST /api/v1/queries`` — submit a query, get back a query_id
- ``GET  /api/v1/queries/{query_id}`` — poll for results
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from datapulse.api.auth import get_current_user
from datapulse.logging import get_logger
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

# Blocklist: dangerous SQL keywords
_BLOCKED_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|EXECUTE|"
    r"DO|CALL|SET(?!\s+LOCAL\s+app\.))\b",
    re.IGNORECASE,
)


def _validate_sql(sql: str) -> None:
    """Validate that the SQL is a read-only SELECT statement."""
    if not _ALLOWED_PATTERN.match(sql):
        raise HTTPException(
            status_code=422,
            detail="Only SELECT and WITH (CTE) statements are allowed.",
        )
    if _BLOCKED_KEYWORDS.search(sql):
        raise HTTPException(
            status_code=422,
            detail="SQL contains disallowed keywords (INSERT, UPDATE, DELETE, DROP, etc.).",
        )


@router.post("", response_model=QueryResponse, status_code=202)
def submit_query(
    body: QuerySubmit,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> QueryResponse:
    """Submit an async SQL query for execution.

    The query is validated for safety (read-only) and dispatched to a
    Celery worker.  Returns a query_id for polling.
    """
    _validate_sql(body.sql)

    tenant_id = user.get("tenant_id", "1")

    from datapulse.tasks.query_tasks import execute_query

    task = execute_query.apply_async(
        kwargs={
            "sql": body.sql,
            "tenant_id": tenant_id,
            "row_limit": body.row_limit,
        },
    )

    log.info("query_submitted", query_id=task.id, tenant_id=tenant_id)

    return QueryResponse(
        query_id=task.id,
        status=QueryStatus.pending,
        submitted_at=datetime.now(UTC),
    )


@router.get("/{query_id}", response_model=QueryResult)
def get_query_result(query_id: str) -> QueryResult:
    """Poll for async query results.

    Returns the current status and, if complete, the result data.
    """
    from datapulse.tasks.celery_app import celery_app

    result = celery_app.AsyncResult(query_id)

    # Map Celery states to our QueryStatus
    status_map = {
        "PENDING": QueryStatus.pending,
        "STARTED": QueryStatus.running,
        "SUCCESS": QueryStatus.complete,
        "FAILURE": QueryStatus.failed,
        "RETRY": QueryStatus.running,
        "REVOKED": QueryStatus.failed,
    }

    status = status_map.get(result.state, QueryStatus.pending)
    now = datetime.now(UTC)

    if status == QueryStatus.complete and result.successful():
        data = result.result
        return QueryResult(
            query_id=query_id,
            status=QueryStatus.complete,
            submitted_at=now,  # Celery doesn't track submission time natively
            completed_at=now,
            columns=data.get("columns", []),
            rows=data.get("rows", []),
            row_count=data.get("row_count", 0),
            truncated=data.get("truncated", False),
            duration_ms=data.get("duration_ms"),
        )

    if status == QueryStatus.failed:
        error_msg = str(result.result) if result.result else "Query execution failed"
        return QueryResult(
            query_id=query_id,
            status=QueryStatus.failed,
            submitted_at=now,
            error=error_msg,
        )

    return QueryResult(
        query_id=query_id,
        status=status,
        submitted_at=now,
    )

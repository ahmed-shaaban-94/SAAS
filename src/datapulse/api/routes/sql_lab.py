"""SQL Lab API endpoints.

Provides a SQL editor experience with:
- Schema browser (table/column metadata)
- SQL execution with validation (read-only)
- Async execution via Celery for large queries
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.logging import get_logger
from datapulse.sql_lab.validator import SQLValidationError, get_schema_tables, validate_sql

log = get_logger(__name__)

router = APIRouter(
    prefix="/sql-lab",
    tags=["sql-lab"],
    dependencies=[Depends(get_current_user)],
)


class SQLExecuteRequest(BaseModel):
    """Request body for SQL execution."""

    sql: str = Field(..., min_length=1, max_length=50_000, description="SQL query")
    row_limit: int = Field(1000, ge=1, le=10_000, description="Max rows")


class SQLExecuteResult(BaseModel):
    """SQL execution result."""

    columns: list[str] = Field(default_factory=list)
    rows: list[list] = Field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    duration_ms: float = 0
    sql: str = ""


class SchemaTable(BaseModel):
    """Table metadata for schema browser."""

    table_name: str
    columns: list[dict]


@router.get("/schemas", response_model=list[SchemaTable])
@limiter.limit("30/minute")
def get_schemas(
    request: Request,
    session: Annotated[Session, Depends(get_tenant_session)],
) -> list[SchemaTable]:
    """Return table/column metadata for the schema browser."""
    tables = get_schema_tables(session)
    return [SchemaTable(**t) for t in tables]


@router.post("/execute", response_model=SQLExecuteResult)
@limiter.limit("20/minute")
def execute_sql(
    request: Request,
    body: SQLExecuteRequest,
    session: Annotated[Session, Depends(get_tenant_session)],
) -> SQLExecuteResult:
    """Execute a read-only SQL query.

    Validates the SQL for safety (no DDL/DML), prepends the search_path
    to public_marts, and executes with the tenant's RLS scope.
    """
    try:
        validated_sql = validate_sql(body.sql)
    except SQLValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Set search path to marts schema
    session.execute(text("SET LOCAL search_path TO public_marts, public"))

    start = time.perf_counter()
    try:
        result = session.execute(text(validated_sql))
        columns = list(result.keys())
        rows: list[list] = []
        truncated = False

        for i, row in enumerate(result):
            if i >= body.row_limit:
                truncated = True
                break
            rows.append([_serialise(v) for v in row])

        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        log.info(
            "sql_lab_executed",
            row_count=len(rows),
            truncated=truncated,
            duration_ms=duration_ms,
        )

        return SQLExecuteResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            duration_ms=duration_ms,
            sql=validated_sql,
        )
    except Exception as exc:
        log.error("sql_lab_failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Query execution failed: {exc}",
        ) from exc


def _serialise(value) -> str | int | float | bool | None:
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

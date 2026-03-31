"""Celery tasks for async query execution.

Provides a generic ``execute_query`` task that runs a SQL query via
SQLAlchemy and stores the results in the Celery result backend (Redis).
"""

from __future__ import annotations

import time

from sqlalchemy import text

from datapulse.core.db import get_session_factory
from datapulse.logging import get_logger
from datapulse.tasks.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(bind=True, name="datapulse.execute_query", max_retries=1)
def execute_query(
    self,
    sql: str,
    params: dict | None = None,
    tenant_id: str = "1",
    row_limit: int = 10_000,
) -> dict:
    """Execute a read-only SQL query and return results as a dict.

    Parameters
    ----------
    sql:
        The SQL SELECT statement to execute.
    params:
        Bind parameters for the query.
    tenant_id:
        Tenant ID for RLS scoping.
    row_limit:
        Maximum number of rows to return.

    Returns
    -------
    dict with keys:
        - columns: list[str]
        - rows: list[list]
        - row_count: int
        - truncated: bool
        - duration_ms: float
    """
    start = time.perf_counter()
    session = get_session_factory()()
    try:
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})

        result = session.execute(text(sql), params or {})
        columns = list(result.keys())
        rows = []
        truncated = False

        for i, row in enumerate(result):
            if i >= row_limit:
                truncated = True
                break
            rows.append([_serialise(v) for v in row])

        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        log.info(
            "query_executed",
            row_count=len(rows),
            truncated=truncated,
            duration_ms=duration_ms,
        )

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
            "duration_ms": duration_ms,
        }
    except Exception as exc:
        session.rollback()
        log.error("query_failed", error=str(exc))
        raise
    finally:
        session.close()


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

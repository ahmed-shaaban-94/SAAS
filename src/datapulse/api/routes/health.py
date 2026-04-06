"""Health check endpoints.

- ``/health``       — full component check (DB + Redis)
- ``/health/live``  — liveness probe (app is running)
- ``/health/ready`` — readiness probe (DB is reachable)
"""

import time

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from datapulse.api.deps import get_engine

router = APIRouter(tags=["health"])
logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Component checks
# ---------------------------------------------------------------------------


def _check_db() -> dict:
    """Ping PostgreSQL and return status + latency."""
    try:
        t0 = time.monotonic()
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = round((time.monotonic() - t0) * 1000)
        return {"status": "ok", "latency_ms": latency}
    except Exception as exc:
        logger.error("health_db_error", error=str(exc))
        return {"status": "error", "error": str(exc)[:100]}


def _check_redis() -> dict:
    """Ping Redis and return status + latency."""
    try:
        from datapulse.cache import get_redis_client

        client = get_redis_client()
        if client is None:
            return {"status": "disabled"}
        t0 = time.monotonic()
        client.ping()
        latency = round((time.monotonic() - t0) * 1000)
        return {"status": "ok", "latency_ms": latency}
    except Exception as exc:
        logger.error("health_redis_error", error=str(exc))
        return {"status": "error", "error": str(exc)[:100]}


def _check_query_executor() -> dict:
    """Check whether the async query executor (Redis db 2) is reachable."""
    try:
        from datapulse.tasks.async_executor import _get_job_client

        client = _get_job_client()
        if client is None:
            return {"status": "disabled"}
        t0 = time.monotonic()
        client.ping()
        latency = round((time.monotonic() - t0) * 1000)
        return {"status": "ok", "latency_ms": latency}
    except Exception as exc:
        logger.error("health_query_executor_error", error=str(exc))
        return {"status": "error", "error": str(exc)[:100]}


def _check_pool() -> dict:
    """Check database connection pool saturation."""
    try:
        engine = get_engine()
        pool = engine.pool
        size = pool.size()
        checked_out = pool.checkedout()
        overflow = pool.overflow()
        max_total = size + pool._max_overflow
        saturation = checked_out / max(max_total, 1)
        status = "ok"
        if saturation > 0.95:
            status = "critical"
        elif saturation > 0.8:
            status = "warning"
        return {
            "status": status,
            "size": size,
            "checked_out": checked_out,
            "overflow": overflow,
            "saturation_pct": round(saturation * 100, 1),
        }
    except Exception as exc:
        logger.error("health_pool_error", error=str(exc))
        return {"status": "error", "error": str(exc)[:100]}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
def health_check(request: Request) -> JSONResponse:
    """Full health check — database, Redis, query executor, connection pool.

    Returns detailed component status for authenticated callers (API key or JWT).
    Unauthenticated callers get only the overall status (no infrastructure details).
    """
    checks = {
        "database": _check_db(),
        "redis": _check_redis(),
        "query_executor": _check_query_executor(),
        "connection_pool": _check_pool(),
    }

    # Determine overall status
    db_ok = checks["database"]["status"] == "ok"
    all_ok = all(c["status"] in ("ok", "disabled") for c in checks.values())

    if not db_ok:
        overall = "unhealthy"
    elif not all_ok:
        overall = "degraded"
    else:
        overall = "healthy"

    status_code = 200 if overall == "healthy" else 503

    # Only expose component details to callers with a valid auth header
    has_auth = bool(
        request.headers.get("authorization")
        or request.headers.get("x-api-key")
    )
    content: dict = {"status": overall}
    if has_auth:
        content["checks"] = checks

    return JSONResponse(status_code=status_code, content=content)


@router.get("/health/live")
def liveness() -> dict:
    """Liveness probe — app process is running."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness() -> JSONResponse:
    """Readiness probe — database is reachable."""
    db = _check_db()
    ready = db["status"] == "ok"
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"ready": ready, "database": db},
    )

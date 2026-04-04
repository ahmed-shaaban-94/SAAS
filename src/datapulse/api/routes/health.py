"""Health check endpoints.

- ``/health``       — full component check (DB + Redis + Celery)
- ``/health/live``  — liveness probe (app is running)
- ``/health/ready`` — readiness probe (DB is reachable)
"""

import time

import structlog
from fastapi import APIRouter
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
        return {"status": "error", "error": str(exc)[:100]}


def _check_celery() -> dict:
    """Check whether at least one Celery worker is available."""
    try:
        from datapulse.tasks.celery_app import celery_app

        inspector = celery_app.control.inspect(timeout=2)
        active = inspector.active()
        if active is None:
            return {"status": "no-workers"}
        return {"status": "ok", "workers": len(active)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:100]}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
def health_check() -> JSONResponse:
    """Full health check — database, Redis, Celery.

    Returns detailed component status for internal/authenticated callers.
    Unauthenticated callers get only the overall status (no infra details).
    """
    checks = {
        "database": _check_db(),
        "redis": _check_redis(),
        "celery": _check_celery(),
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
    # Only expose component details to internal callers; public gets status only
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks},
    )


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

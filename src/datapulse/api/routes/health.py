"""Health check endpoints.

- ``/health``       — full component check (DB + Redis)
- ``/health/live``  — liveness probe (app is running)
- ``/health/ready`` — readiness probe (DB is reachable)
"""

import time
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from datapulse.api.auth import get_optional_user_for_health
from datapulse.api.deps import get_engine
from datapulse.api.limiter import limiter
from datapulse.checks import check_db, check_redis
from datapulse.core.db import apply_session_locals

router = APIRouter(tags=["health"])
logger = structlog.get_logger()

# Backward-compat aliases — remove once no other module uses the underscore names.
_check_db = check_db
_check_redis = check_redis


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
    except Exception:
        logger.exception("Query executor health check failed")
        return {"status": "error", "error": "internal_error"}


def _check_pool() -> dict:
    """Check database connection pool saturation."""
    try:
        engine = get_engine()
        pool = engine.pool
        size = pool.size()  # type: ignore[attr-defined]
        checked_out = pool.checkedout()  # type: ignore[attr-defined]
        overflow = pool.overflow()  # type: ignore[attr-defined]
        max_total = size + pool._max_overflow  # type: ignore[attr-defined]
        saturation = checked_out / max(max_total, 1)
        status = "ok"
        if saturation > 0.95:
            status = "critical"
        elif saturation > 0.8:
            status = "warning"
        if saturation > 0.95:
            logger.error(
                "pool_saturation_critical",
                checked_out=checked_out,
                max_total=max_total,
                saturation_pct=round(saturation * 100, 1),
            )
        elif saturation > 0.8:
            logger.warning(
                "pool_saturation_warning",
                checked_out=checked_out,
                max_total=max_total,
                saturation_pct=round(saturation * 100, 1),
            )
        return {
            "status": status,
            "size": size,
            "checked_out": checked_out,
            "overflow": overflow,
            "saturation_pct": round(saturation * 100, 1),
        }
    except Exception:
        logger.exception("Connection pool health check failed")
        return {"status": "error", "error": "internal_error"}


def _check_dbt_freshness() -> dict:
    """Check when dbt models were last refreshed."""
    try:
        with get_engine().connect() as conn:
            sql = "SELECT MAX(updated_at) FROM public_marts.metrics_summary"
            row = conn.execute(text(sql)).fetchone()
        last_updated = row[0] if row and row[0] else None
        if last_updated is None:
            return {"status": "unknown", "last_updated_at": None}
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=UTC)
        age_hours = (datetime.now(UTC) - last_updated).total_seconds() / 3600
        status = "stale" if age_hours > 24 else "ok"
        if status == "stale":
            logger.warning(
                "dbt_freshness_stale",
                last_updated_at=last_updated.isoformat(),
                age_hours=round(age_hours, 1),
            )
        return {
            "status": status,
            "last_updated_at": last_updated.isoformat(),
            "age_hours": round(age_hours, 1),
        }
    except Exception:
        logger.exception("dbt freshness health check failed")
        return {"status": "error", "error": "internal_error"}


def _check_data_freshness() -> dict:
    """Check last successful data load into bronze layer."""
    try:
        with get_engine().connect() as conn:
            row = conn.execute(text("SELECT MAX(loaded_at) FROM bronze.sales")).fetchone()
        last_loaded = row[0] if row and row[0] else None
        if last_loaded is None:
            return {"status": "unknown", "last_loaded_at": None}
        if last_loaded.tzinfo is None:
            last_loaded = last_loaded.replace(tzinfo=UTC)
        age_hours = (datetime.now(UTC) - last_loaded).total_seconds() / 3600
        status = "stale" if age_hours > 24 else "ok"
        if status == "stale":
            logger.warning(
                "data_freshness_stale",
                last_loaded_at=last_loaded.isoformat(),
                age_hours=round(age_hours, 1),
            )
        return {
            "status": status,
            "last_loaded_at": last_loaded.isoformat(),
            "age_hours": round(age_hours, 1),
        }
    except Exception:
        logger.exception("Data freshness health check failed")
        return {"status": "error", "error": "internal_error"}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
@limiter.limit("10/minute")
def health_check(
    request: Request,
    user: dict[str, Any] | None = Depends(get_optional_user_for_health),  # noqa: B008
) -> JSONResponse:
    """Full health check — database, Redis, query executor, connection pool.

    Returns detailed component status for authenticated callers (API key or JWT).
    Unauthenticated callers get only the overall status (no infrastructure details).

    Rate-limited to 10/minute per remote address because each call fires ~6
    database queries; leaving it uncapped is a trivial DoS vector. The
    lightweight ``/health/live`` and ``/health/ready`` stay rate-free so
    kubelet probes can still run at their normal cadence.
    """
    checks = {
        "database": _check_db(),
        "redis": _check_redis(),
        "query_executor": _check_query_executor(),
        "connection_pool": _check_pool(),
        "dbt_freshness": _check_dbt_freshness(),
        "data_freshness": _check_data_freshness(),
    }

    # Determine overall status
    # Core checks: database must be up. Redis/pool/executor degrade gracefully.
    # Informational checks (dbt_freshness, data_freshness) are
    # non-critical — missing tables on fresh deploy shouldn't block health.
    db_ok = checks["database"]["status"] == "ok"
    critical_keys = ("database", "redis", "query_executor", "connection_pool")
    critical_ok = all(
        checks[k]["status"] in ("ok", "disabled", "stale", "unknown")
        for k in critical_keys
        if k in checks
    )

    if not db_ok:
        overall = "unhealthy"
    elif not critical_ok:
        overall = "degraded"
    else:
        overall = "healthy"

    status_code = 200 if overall in ("healthy", "degraded") else 503

    # Only expose component details to callers with a verified identity
    content: dict = {"status": overall}
    if user is not None:
        from datapulse.scheduler import get_scheduler_status

        checks["scheduler"] = get_scheduler_status()
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


@router.get("/health/auth-check")
def auth_check() -> JSONResponse:
    """Auth pipeline probe — validates that tenant context can be established.

    Checks that ``default_tenant_id`` is configured and that the DB accepts
    ``SET LOCAL app.tenant_id``.  If this fails, all JWT-authenticated requests
    will be rejected with 401 even though the API container looks healthy.
    """
    from datapulse.config import get_settings

    settings = get_settings()
    if not settings.default_tenant_id:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "error": "no_default_tenant_id"},
        )
    try:
        with get_engine().connect() as conn:
            apply_session_locals(conn, tenant_id=settings.default_tenant_id)
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "default_tenant_id": str(settings.default_tenant_id),
            },
        )
    except Exception:
        logger.exception("Auth pipeline health check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "error": "tenant_session_failed"},
        )

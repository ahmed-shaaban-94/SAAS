"""Health check endpoint."""

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from datapulse.api.deps import _get_engine
from datapulse.api.limiter import limiter

router = APIRouter(tags=["health"])
logger = structlog.get_logger()


@router.get("/health")
@limiter.limit("200/minute")
def health_check(request: Request) -> JSONResponse:
    checks: dict[str, str] = {}
    overall = "ok"

    # Database check
    try:
        with _get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["db"] = "connected"
    except Exception as exc:
        logger.warning("health_check_db_failed", error=str(exc))
        checks["db"] = "disconnected"
        overall = "degraded"

    # Filesystem check (data directory writable)
    try:
        from datapulse.config import get_settings
        from pathlib import Path
        data_dir = Path(get_settings().raw_sales_path)
        checks["filesystem"] = "ok" if data_dir.exists() else "missing"
    except Exception:
        checks["filesystem"] = "error"

    status_code = 200 if overall == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, **checks},
    )

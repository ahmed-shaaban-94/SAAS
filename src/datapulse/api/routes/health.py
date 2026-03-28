"""Health check endpoint."""

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from datapulse.api.limiter import limiter
from datapulse.api.deps import _get_engine

router = APIRouter(tags=["health"])
logger = structlog.get_logger()


@router.get("/health")
@limiter.limit("200/minute")
def health_check(request: Request) -> JSONResponse:
    try:
        with _get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return JSONResponse(content={"status": "ok", "db": "connected"})
    except Exception as exc:
        logger.warning("health_check_degraded", error=str(exc))
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "disconnected"},
        )

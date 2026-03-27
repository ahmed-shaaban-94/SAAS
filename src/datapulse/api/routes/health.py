"""Health check endpoint."""

from fastapi import APIRouter
from sqlalchemy import text

from datapulse.api.deps import _get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    try:
        with _get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        return {"status": "degraded", "db": "disconnected"}

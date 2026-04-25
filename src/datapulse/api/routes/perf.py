"""POST /api/v1/perf/vitals — receive web-vitals beacons (#734)."""

from __future__ import annotations

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["observability"])

logger = structlog.get_logger()


class VitalPayload(BaseModel):
    metric: str = Field(..., description="Web vital name, e.g. FCP, LCP, CLS, INP")
    value: float = Field(..., description="Metric value in ms (or unitless for CLS)")
    route: str = Field(..., description="Next.js pathname where the vital was measured")
    ts: int = Field(..., description="Unix timestamp in milliseconds")


@router.post(
    "/perf/vitals",
    status_code=204,
    summary="Receive web-vitals beacon",
    description="Accept a single web-vital measurement from the client. No auth required.",
)
def receive_vital(payload: VitalPayload) -> None:
    """Accept a web-vitals beacon. No auth required (client-side telemetry)."""
    logger.info("web_vital", **payload.model_dump())

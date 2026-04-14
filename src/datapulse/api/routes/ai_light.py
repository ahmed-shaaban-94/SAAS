"""AI-Light API endpoints — Phase D: HITL approval + SSE streaming.

Endpoints:
  GET  /ai-light/status                    — availability check
  GET  /ai-light/summary                   — executive narrative (sync | stream)
  GET  /ai-light/anomalies                 — anomaly report (sync | stream)
  GET  /ai-light/changes                   — change narrative (sync | stream)
  POST /ai-light/deep-dive                 — composite deep-dive (sync | require_review | stream)
  GET  /ai-light/review/{run_id}           — pending HITL draft
  POST /ai-light/review/{run_id}/approve   — resume graph with optional edits

All endpoints require insights:view.
The approve endpoint additionally requires insights:approve.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from datapulse.ai_light.models import (
    AISummary,
    AnomalyReport,
    ApproveRequest,
    ChangeNarrative,
    DeepDiveDraft,
    DeepDiveRequest,
    DeepDiveResponse,
)
from datapulse.ai_light.service import AILightService
from datapulse.api.deps import get_ai_light_service
from datapulse.api.limiter import limiter
from datapulse.logging import get_logger
from datapulse.rbac.dependencies import require_permission

router = APIRouter(
    prefix="/ai-light",
    tags=["ai-light"],
    dependencies=[Depends(require_permission("insights:view"))],
)
log = get_logger(__name__)

# Type alias — works for both AILightService and AILightGraphService
ServiceDep = Annotated[AILightService, Depends(get_ai_light_service)]


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


def _sse_event(node: str, status: str, data: dict | None = None) -> str:
    """Format a single Server-Sent Event."""
    payload: dict[str, Any] = {"node": node, "status": status}
    if data:
        payload["partial_state"] = data
    return f"data: {json.dumps(payload)}\n\n"


async def _stream_insight(service, insight_type: str, **params) -> AsyncIterator[str]:
    """Yield SSE events for each node transition during graph execution."""
    if not hasattr(service, "stream_run"):
        # Fallback: non-graph service — yield a single done event
        yield _sse_event("start", "running")
        await asyncio.sleep(0)  # allow event loop tick
        yield _sse_event("done", "complete")
        return

    yield _sse_event("start", "running", {"insight_type": insight_type})
    async for node_name, chunk in service.stream_run(insight_type, **params):
        yield _sse_event(node_name, "done", chunk)
    yield _sse_event("end", "complete")


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


@router.get("/status")
@limiter.limit("20/minute")
async def get_status(request: Request, service: ServiceDep) -> dict:
    """Check if AI-Light is available (OpenRouter configured)."""
    return {"available": service.is_available}


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=AISummary)
@limiter.limit("20/minute")
async def get_summary(
    request: Request,
    service: ServiceDep,
    target_date: Annotated[date | None, Query()] = None,
    stream: Annotated[bool, Query()] = False,
):
    """Generate an AI-powered executive summary.

    Pass stream=true for an SSE stream of node-level events.
    """
    if not service.is_available:
        raise HTTPException(status_code=503, detail="OpenRouter API key not configured")

    if stream:
        return StreamingResponse(
            _stream_insight(service, "summary", target_date=str(target_date or date.today())),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        return service.generate_summary(target_date)
    except Exception as exc:
        log.error("ai_summary_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable") from exc


# ---------------------------------------------------------------------------
# Anomalies
# ---------------------------------------------------------------------------


@router.get("/anomalies", response_model=AnomalyReport)
@limiter.limit("20/minute")
async def get_anomalies(
    request: Request,
    service: ServiceDep,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    stream: Annotated[bool, Query()] = False,
):
    """Detect anomalies in daily sales data.

    Pass stream=true for an SSE stream of node-level events.
    """
    if stream:
        return StreamingResponse(
            _stream_insight(
                service,
                "anomalies",
                start_date=str(start_date or ""),
                end_date=str(end_date or ""),
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        return service.detect_anomalies(start_date, end_date)
    except Exception as exc:
        log.error("ai_anomalies_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable") from exc


# ---------------------------------------------------------------------------
# Changes
# ---------------------------------------------------------------------------


@router.get("/changes", response_model=ChangeNarrative)
@limiter.limit("20/minute")
async def get_changes(
    request: Request,
    service: ServiceDep,
    current_date: Annotated[date | None, Query()] = None,
    previous_date: Annotated[date | None, Query()] = None,
    stream: Annotated[bool, Query()] = False,
):
    """Compare two dates and explain the key changes.

    Pass stream=true for an SSE stream of node-level events.
    """
    if stream:
        return StreamingResponse(
            _stream_insight(
                service,
                "changes",
                end_date=str(current_date or ""),
                start_date=str(previous_date or ""),
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        return service.explain_changes(current_date, previous_date)
    except Exception as exc:
        log.error("ai_changes_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable") from exc


# ---------------------------------------------------------------------------
# Deep-dive (Phase C/D)
# ---------------------------------------------------------------------------


@router.post("/deep-dive", status_code=200)
@limiter.limit("10/minute")
async def post_deep_dive(
    request: Request,
    body: DeepDiveRequest,
    service: ServiceDep,
):
    """Run a composite deep-dive across KPIs, anomalies, forecast, and targets.

    - Default: synchronous JSON response (DeepDiveResponse).
    - stream=true: SSE stream of node-level events (text/event-stream).
    - require_review=true: pauses before synthesize; returns 202 + DeepDiveDraft.
      Call GET /review/{run_id} to inspect, POST /review/{run_id}/approve to resume.
    """
    if not service.is_available:
        raise HTTPException(status_code=503, detail="OpenRouter API key not configured")

    if body.stream:
        return StreamingResponse(
            _stream_insight(
                service,
                "deep_dive",
                start_date=str(body.start_date or ""),
                end_date=str(body.end_date or ""),
                require_review=body.require_review,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    if not hasattr(service, "start_deep_dive"):
        raise HTTPException(
            status_code=501,
            detail="Deep-dive requires ai_light_use_langgraph=true",
        )

    try:
        result = service.start_deep_dive(body)
        if isinstance(result, DeepDiveDraft):
            # HITL: paused before synthesize
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=202, content=result.model_dump(mode="json"))
        return result
    except Exception as exc:
        log.error("ai_deep_dive_failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable") from exc


# ---------------------------------------------------------------------------
# HITL review endpoints (Phase D)
# ---------------------------------------------------------------------------


@router.get(
    "/review/{run_id}",
    response_model=DeepDiveDraft,
    dependencies=[Depends(require_permission("insights:view"))],
)
@limiter.limit("30/minute")
async def get_review(
    request: Request,
    run_id: str,
    service: ServiceDep,
) -> DeepDiveDraft:
    """Return the pending draft state for a paused HITL deep-dive run.

    Returns 404 if the run_id is not found or is already completed.
    """
    if not hasattr(service, "get_review_state"):
        raise HTTPException(
            status_code=501,
            detail="HITL review requires ai_light_use_langgraph=true",
        )

    draft = service.get_review_state(run_id)
    if draft is None:
        raise HTTPException(
            status_code=404,
            detail=f"No pending review found for run_id={run_id!r}. "
            "The run may have already completed or expired.",
        )
    return draft


@router.post(
    "/review/{run_id}/approve",
    response_model=DeepDiveResponse,
    dependencies=[Depends(require_permission("insights:approve"))],
)
@limiter.limit("10/minute")
async def approve_review(
    request: Request,
    run_id: str,
    body: ApproveRequest,
    service: ServiceDep,
) -> DeepDiveResponse:
    """Resume a paused HITL run, optionally incorporating analyst edits.

    Requires the insights:approve permission (admin/owner only by default).

    The body may contain:
    - narrative: override the draft narrative
    - highlights: override the draft highlights

    Returns the final DeepDiveResponse after graph completion.
    """
    if not hasattr(service, "approve_run"):
        raise HTTPException(
            status_code=501,
            detail="HITL approval requires ai_light_use_langgraph=true",
        )

    # Build edits dict from non-None fields only
    edits: dict = {}
    if body.narrative is not None:
        edits["narrative"] = body.narrative
    if body.highlights is not None:
        edits["highlights"] = body.highlights

    try:
        return service.approve_run(run_id, edits or None)
    except Exception as exc:
        log.error("ai_approve_failed", run_id=run_id, error=str(exc), exc_info=True)
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable") from exc

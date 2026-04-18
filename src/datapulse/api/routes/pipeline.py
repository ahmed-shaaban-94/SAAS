"""Pipeline status tracking API endpoints.

Provides CRUD endpoints for pipeline run monitoring and control,
used by n8n webhooks and the frontend dashboard.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from functools import partial
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from datapulse.api.auth import get_current_user, require_pipeline_token
from datapulse.api.deps import (
    get_billing_service,
    get_pipeline_executor,
    get_pipeline_service,
    get_quality_service,
)
from datapulse.billing.service import BillingService, PlanLimitExceededError
from datapulse.cache import cache_invalidate_pattern
from datapulse.logging import get_logger
from datapulse.pipeline.checkpoint import get_completed_stages, get_last_successful_stage
from datapulse.pipeline.executor import PipelineExecutor
from datapulse.pipeline.models import (
    VALID_STATUSES,
    ExecuteRequest,
    ExecutionResult,
    PipelineRunCreate,
    PipelineRunList,
    PipelineRunResponse,
    PipelineRunUpdate,
    QualityScorecard,
    TriggerRequest,
    TriggerResponse,
)
from datapulse.pipeline.quality import (
    VALID_STAGES,
    QualityCheckRequest,
    QualityReport,
    QualityRunDetail,
)
from datapulse.pipeline.quality_service import QualityService
from datapulse.pipeline.service import PipelineService
from datapulse.pipeline.state_machine import get_resume_stage

log = get_logger(__name__)

router = APIRouter(
    prefix="/pipeline",
    tags=["pipeline"],
    dependencies=[Depends(get_current_user)],
)

ServiceDep = Annotated[PipelineService, Depends(get_pipeline_service)]
ExecutorDep = Annotated[PipelineExecutor, Depends(get_pipeline_executor)]
QualityServiceDep = Annotated[QualityService, Depends(get_quality_service)]


@router.get("/runs", response_model=PipelineRunList)
def list_runs(
    service: ServiceDep,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    started_after: Annotated[
        datetime | None, Query(description="Filter runs started after this time")
    ] = None,
    started_before: Annotated[
        datetime | None, Query(description="Filter runs started before this time")
    ] = None,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
) -> PipelineRunList:
    """List pipeline runs with optional filters and pagination."""
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}"
            ),
        )
    return service.list_runs(
        status=status,
        started_after=started_after,
        started_before=started_before,
        offset=offset,
        limit=limit,
    )


@router.get("/runs/latest", response_model=PipelineRunResponse)
def get_latest_run(
    service: ServiceDep,
    run_type: Annotated[str | None, Query(description="Filter by run type")] = None,
) -> PipelineRunResponse:
    """Return the most recent pipeline run."""
    result = service.get_latest_run(run_type)
    if result is None:
        raise HTTPException(status_code=404, detail="No pipeline runs found")
    return result


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
def get_run(service: ServiceDep, run_id: UUID) -> PipelineRunResponse:
    """Return a single pipeline run by ID."""
    result = service.get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return result


@router.get("/runs/{run_id}/stream")
async def stream_run_progress(
    service: ServiceDep,
    run_id: UUID,
    request: Request,
) -> StreamingResponse:
    """SSE stream for real-time pipeline run progress.

    Emits events:
    - ``status_change``: when status differs from the previous poll
    - ``complete``: when the run reaches a terminal state (success/failed/cancelled)

    Polls every 2 seconds. Closes automatically on terminal state, client
    disconnect, or after 10 minutes.
    """
    terminal = {"success", "failed", "cancelled"}
    poll_interval = 2  # seconds
    max_duration = 600  # 10 minutes

    # Verify run exists before starting stream
    loop = asyncio.get_event_loop()
    run = await loop.run_in_executor(None, service.get_run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    async def event_generator():
        last_status = None
        elapsed = 0

        try:
            while elapsed < max_duration:
                # Detect client disconnect
                if await request.is_disconnected():
                    log.info("sse_client_disconnected", run_id=str(run_id))
                    return

                try:
                    current = await loop.run_in_executor(None, service.get_run, run_id)
                except Exception as exc:
                    log.error("sse_poll_error", run_id=str(run_id), error=str(exc))
                    yield _sse_event("error", {"message": "Internal error polling run status"})
                    return

                if current is None:
                    yield _sse_event("error", {"message": "Run not found"})
                    return

                data = {
                    "run_id": str(current.id),
                    "status": current.status,
                    "started_at": str(current.started_at),
                    "finished_at": (str(current.finished_at) if current.finished_at else None),
                    "duration_seconds": (
                        float(current.duration_seconds) if current.duration_seconds else None
                    ),
                    "rows_loaded": current.rows_loaded,
                    "error_message": current.error_message,
                }

                if current.status != last_status:
                    yield _sse_event("status_change", data)
                    last_status = current.status

                if current.status in terminal:
                    yield _sse_event("complete", data)
                    return

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            yield _sse_event("timeout", {"message": "Stream timeout after 10 minutes"})
        except asyncio.CancelledError:
            log.info("sse_stream_cancelled", run_id=str(run_id))
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event message."""
    return f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post(
    "/runs",
    response_model=PipelineRunResponse,
    status_code=201,
)
def create_run(
    service: ServiceDep,
    body: PipelineRunCreate,
) -> PipelineRunResponse:
    """Create a new pipeline run record."""
    return service.start_run(body)


@router.patch(
    "/runs/{run_id}",
    response_model=PipelineRunResponse,
)
def update_run(
    service: ServiceDep,
    run_id: UUID,
    body: PipelineRunUpdate,
) -> PipelineRunResponse:
    """Update an existing pipeline run (status, metrics, error).

    Status validation is handled by PipelineRunUpdate's Pydantic field_validator;
    invalid values are rejected with 422 before this handler runs.

    When a run transitions to 'success', all analytics caches are invalidated
    so that dashboards reflect the freshly loaded data.
    """
    result = service.update_status(run_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    # Invalidate analytics cache on successful pipeline completion
    if body.status == "success":
        deleted = cache_invalidate_pattern("datapulse:analytics:*")
        log.info(
            "cache_invalidated_on_pipeline_success",
            run_id=str(run_id),
            keys_deleted=deleted,
        )

    return result


@router.post(
    "/trigger",
    response_model=TriggerResponse,
    status_code=202,
    dependencies=[Depends(require_pipeline_token)],
)
async def trigger_pipeline(
    service: ServiceDep,
    billing: Annotated[BillingService, Depends(get_billing_service)],
    user: Annotated[dict, Depends(get_current_user)],
    body: TriggerRequest | None = None,
) -> TriggerResponse:
    """Trigger a full pipeline run.

    Checks plan limits before starting. Creates a pipeline_run record (pending),
    then starts the pipeline orchestrator in the background. Returns immediately.
    Uses JWT-derived tenant_id for all authorization — never the request body.
    """
    req = body or TriggerRequest()
    # Tenant ID from JWT claims — never trust the request body for authorization
    tenant_id = int(user.get("tenant_id", "1"))

    # 0. Enforce plan limits — reject if tenant would exceed row/source caps
    try:
        billing.check_plan_limits(tenant_id)
    except PlanLimitExceededError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "plan_limit_exceeded",
                "limit_type": e.limit_type,
                "message": f"Your {e.limit_type} limit has been reached. "
                "Upgrade your plan to continue.",
            },
        ) from e

    # Check pipeline_automation feature access
    if not billing.check_feature_access(tenant_id, "pipeline_automation"):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "feature_not_available",
                "feature": "pipeline_automation",
                "message": "Pipeline automation is not available on your current plan. "
                "Upgrade to Pro or Enterprise to enable automated pipelines.",
            },
        )

    # 1. Create the run record
    run = service.start_run(
        PipelineRunCreate(
            run_type="full",
            trigger_source="api",
            metadata={"source_dir": req.source_dir},
        ),
        tenant_id=tenant_id,
    )

    # 2. Run pipeline in background (replaces n8n webhook)
    from datapulse.scheduler import run_pipeline

    asyncio.create_task(
        run_pipeline(
            run_id=run.id,
            source_dir=req.source_dir,
            tenant_id=tenant_id,
        )
    )

    return TriggerResponse(run_id=run.id, status=run.status)


@router.post(
    "/runs/{run_id}/resume",
    response_model=PipelineRunResponse,
    dependencies=[Depends(require_pipeline_token)],
)
def resume_run(
    service: ServiceDep,
    run_id: UUID,
) -> PipelineRunResponse:
    """Resume a failed pipeline run from the last successful checkpoint.

    Reads the checkpoint from metadata, determines the next stage,
    and resets the run to 'running' status so n8n can pick it up.
    """
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    if run.status != "failed":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot resume run with status '{run.status}'."
            " Only 'failed' runs can be resumed.",
        )

    last_stage = get_last_successful_stage(run.metadata)
    if last_stage is None:
        raise HTTPException(
            status_code=409,
            detail="No checkpoint found. Cannot resume — trigger a new run instead.",
        )

    resume_from = get_resume_stage(last_stage)
    if resume_from is None:
        raise HTTPException(
            status_code=409,
            detail=f"Run already completed stage '{last_stage}'. Nothing to resume.",
        )

    completed = get_completed_stages(run.metadata)

    update = PipelineRunUpdate(
        status="running",
        error_message=None,
        metadata={
            **run.metadata,
            "resumed_from": resume_from.value,
            "skipped_stages": completed,
        },
    )
    result = service.update_status(run_id, update)
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    log.info(
        "pipeline_resumed",
        run_id=str(run_id),
        resumed_from=resume_from.value,
        skipped=completed,
    )
    return result


@router.post(
    "/execute/bronze",
    response_model=ExecutionResult,
    dependencies=[Depends(require_pipeline_token)],
)
async def execute_bronze(
    executor: ExecutorDep,
    body: ExecuteRequest,
) -> ExecutionResult:
    """Run the bronze loader stage for a pipeline run.

    Runs in a background thread to avoid blocking the API threadpool.
    """
    return await asyncio.to_thread(
        partial(executor.run_bronze, run_id=body.run_id, source_dir=body.source_dir),
    )


@router.post(
    "/execute/dbt-staging",
    response_model=ExecutionResult,
    dependencies=[Depends(require_pipeline_token)],
)
async def execute_dbt_staging(
    executor: ExecutorDep,
    body: ExecuteRequest,
) -> ExecutionResult:
    """Run dbt staging models in a background thread."""
    return await asyncio.to_thread(
        partial(executor.run_dbt, run_id=body.run_id, selector="staging"),
    )


@router.post(
    "/execute/dbt-marts",
    response_model=ExecutionResult,
    dependencies=[Depends(require_pipeline_token)],
)
async def execute_dbt_marts(
    executor: ExecutorDep,
    body: ExecuteRequest,
) -> ExecutionResult:
    """Run dbt marts models in a background thread."""
    return await asyncio.to_thread(
        partial(executor.run_dbt, run_id=body.run_id, selector="marts"),
    )


@router.post(
    "/execute/forecasting",
    response_model=ExecutionResult,
    dependencies=[Depends(require_pipeline_token)],
)
async def execute_forecasting(
    executor: ExecutorDep,
    body: ExecuteRequest,
    user: Annotated[dict, Depends(get_current_user)],
) -> ExecutionResult:
    """Run the forecasting stage in a background thread."""
    tenant_id = str(user.get("tenant_id", "1"))
    return await asyncio.to_thread(
        partial(executor.run_forecasting, run_id=body.run_id, tenant_id=tenant_id),
    )


@router.get("/runs/{run_id}/quality", response_model=QualityRunDetail)
def get_quality_checks(
    service: ServiceDep,
    quality_service: QualityServiceDep,
    run_id: UUID,
    stage: Annotated[str | None, Query(description="Filter by stage")] = None,
) -> QualityRunDetail:
    """Return quality check results for a pipeline run with aggregate counts.

    Response shape is aligned with the web frontend's `useQualityRunDetail`
    hook contract: carries `run_id`, `checks`, `total_checks`, and
    `passed`/`failed`/`warned` counters so the UI does not have to
    re-derive them.
    """
    if service.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    if stage is not None and stage not in VALID_STAGES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid stage '{stage}'. Must be one of: {', '.join(sorted(VALID_STAGES))}",
        )
    return quality_service.get_run_detail(run_id, stage)


@router.post(
    "/execute/quality-check",
    response_model=QualityReport,
    dependencies=[Depends(require_pipeline_token)],
)
def execute_quality_check(
    quality_service: QualityServiceDep,
    body: QualityCheckRequest,
    user: Annotated[dict, Depends(get_current_user)],
) -> QualityReport:
    """Run quality checks for a specific pipeline stage.

    Returns a QualityReport with gate_passed indicating whether
    the pipeline should continue (True) or halt (False).

    Stage validation is handled by QualityCheckRequest's Pydantic field_validator;
    invalid values are rejected with 422 before this handler runs.
    """
    tenant_id = int(user.get("tenant_id", "1"))
    return quality_service.run_checks_for_stage(
        run_id=body.run_id,
        stage=body.stage,
        tenant_id=tenant_id,
    )


@router.get("/quality/scorecard", response_model=QualityScorecard)
def get_quality_scorecard(
    request: Request,
    quality_service: QualityServiceDep,
    limit: int = Query(20, ge=1, le=100),
) -> QualityScorecard:
    """Return aggregated quality scores across recent pipeline runs."""
    return quality_service.get_scorecard(limit=limit)

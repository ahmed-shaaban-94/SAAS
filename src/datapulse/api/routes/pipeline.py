"""Pipeline status tracking API endpoints.

Provides CRUD endpoints for pipeline run monitoring and control,
used by n8n webhooks and the frontend dashboard.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from datapulse.api.auth import get_current_user, require_pipeline_token
from datapulse.api.deps import get_pipeline_executor, get_pipeline_service, get_quality_service
from datapulse.config import get_settings
from datapulse.logging import get_logger
from datapulse.pipeline.executor import PipelineExecutor
from datapulse.pipeline.models import (
    VALID_STATUSES,
    ExecuteRequest,
    ExecutionResult,
    PipelineRunCreate,
    PipelineRunList,
    PipelineRunResponse,
    PipelineRunUpdate,
    TriggerRequest,
    TriggerResponse,
)
from datapulse.pipeline.quality import (
    VALID_STAGES,
    QualityCheckList,
    QualityCheckRequest,
    QualityReport,
)
from datapulse.pipeline.quality_service import QualityService
from datapulse.pipeline.service import PipelineService

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
            detail=f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
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


@router.post(
    "/runs", response_model=PipelineRunResponse, status_code=201,
)
def create_run(
    service: ServiceDep, body: PipelineRunCreate,
) -> PipelineRunResponse:
    """Create a new pipeline run record."""
    return service.start_run(body)


@router.patch(
    "/runs/{run_id}", response_model=PipelineRunResponse,
)
def update_run(
    service: ServiceDep, run_id: UUID, body: PipelineRunUpdate,
) -> PipelineRunResponse:
    """Update an existing pipeline run (status, metrics, error).

    Status validation is handled by PipelineRunUpdate's Pydantic field_validator;
    invalid values are rejected with 422 before this handler runs.
    """
    result = service.update_status(run_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return result


@router.post(
    "/trigger", response_model=TriggerResponse, status_code=202,
    dependencies=[Depends(require_pipeline_token)],
)
def trigger_pipeline(
    service: ServiceDep,
    body: TriggerRequest | None = None,
) -> TriggerResponse:
    """Trigger a full pipeline run.

    Creates a pipeline_run record (pending), then notifies n8n
    via webhook to begin orchestration. Returns immediately.
    """
    req = body or TriggerRequest()
    settings = get_settings()

    # 1. Create the run record
    run = service.start_run(
        PipelineRunCreate(
            run_type="full",
            trigger_source="api",
            metadata={"source_dir": req.source_dir},
        ),
        tenant_id=req.tenant_id,
    )

    # 2. Notify n8n (best-effort — run exists even if n8n is down)
    webhook_url = f"{settings.n8n_webhook_url}pipeline-trigger"
    headers: dict[str, str] = {}
    if settings.pipeline_webhook_secret:
        headers["X-Pipeline-Token"] = settings.pipeline_webhook_secret
    try:
        httpx.post(
            webhook_url,
            json={
                "run_id": str(run.id),
                "source_dir": req.source_dir,
                "tenant_id": req.tenant_id,
            },
            headers=headers,
            timeout=10.0,
            follow_redirects=True,
        )
    except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
        log.warning(
            "n8n_webhook_failed",
            webhook_url=webhook_url,
            error=str(exc),
        )

    return TriggerResponse(run_id=run.id, status=run.status)


@router.post(
    "/execute/bronze", response_model=ExecutionResult,
    dependencies=[Depends(require_pipeline_token)],
)
def execute_bronze(
    executor: ExecutorDep,
    body: ExecuteRequest,
) -> ExecutionResult:
    """Run the bronze loader stage for a pipeline run."""
    return executor.run_bronze(
        run_id=body.run_id,
        source_dir=body.source_dir,
    )


@router.post(
    "/execute/dbt-staging", response_model=ExecutionResult,
    dependencies=[Depends(require_pipeline_token)],
)
def execute_dbt_staging(
    executor: ExecutorDep,
    body: ExecuteRequest,
) -> ExecutionResult:
    """Run dbt staging models."""
    return executor.run_dbt(run_id=body.run_id, selector="staging")


@router.post(
    "/execute/dbt-marts", response_model=ExecutionResult,
    dependencies=[Depends(require_pipeline_token)],
)
def execute_dbt_marts(
    executor: ExecutorDep,
    body: ExecuteRequest,
) -> ExecutionResult:
    """Run dbt marts models."""
    return executor.run_dbt(run_id=body.run_id, selector="marts")


@router.get("/runs/{run_id}/quality", response_model=QualityCheckList)
def get_quality_checks(
    service: ServiceDep,
    quality_service: QualityServiceDep,
    run_id: UUID,
    stage: Annotated[str | None, Query(description="Filter by stage")] = None,
) -> QualityCheckList:
    """Return quality check results for a pipeline run."""
    if service.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    if stage is not None and stage not in VALID_STAGES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid stage '{stage}'. Must be one of: {', '.join(sorted(VALID_STAGES))}",
        )
    return quality_service.get_checks(run_id, stage)


@router.post(
    "/execute/quality-check", response_model=QualityReport,
    dependencies=[Depends(require_pipeline_token)],
)
def execute_quality_check(
    quality_service: QualityServiceDep,
    body: QualityCheckRequest,
) -> QualityReport:
    """Run quality checks for a specific pipeline stage.

    Returns a QualityReport with gate_passed indicating whether
    the pipeline should continue (True) or halt (False).

    Stage validation is handled by QualityCheckRequest's Pydantic field_validator;
    invalid values are rejected with 422 before this handler runs.
    """
    return quality_service.run_checks_for_stage(
        run_id=body.run_id, stage=body.stage, tenant_id=body.tenant_id,
    )

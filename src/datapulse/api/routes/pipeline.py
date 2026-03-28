"""Pipeline status tracking API endpoints.

Provides CRUD endpoints for pipeline run monitoring and control,
used by n8n webhooks and the frontend dashboard.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from datapulse.api.deps import get_pipeline_service
from datapulse.pipeline.models import (
    VALID_STATUSES,
    PipelineRunCreate,
    PipelineRunList,
    PipelineRunResponse,
    PipelineRunUpdate,
)
from datapulse.pipeline.service import PipelineService

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

ServiceDep = Annotated[PipelineService, Depends(get_pipeline_service)]


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


@router.post("/runs", response_model=PipelineRunResponse, status_code=201)
def create_run(
    service: ServiceDep, body: PipelineRunCreate,
) -> PipelineRunResponse:
    """Create a new pipeline run record."""
    return service.start_run(body)


@router.patch("/runs/{run_id}", response_model=PipelineRunResponse)
def update_run(
    service: ServiceDep, run_id: UUID, body: PipelineRunUpdate,
) -> PipelineRunResponse:
    """Update an existing pipeline run (status, metrics, error)."""
    try:
        result = service.update_status(run_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return result

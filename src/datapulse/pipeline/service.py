"""Pipeline business-logic layer.

Thin wrapper around PipelineRepository that adds validation
and convenience methods for common status transitions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from datapulse.logging import get_logger
from datapulse.pipeline.models import (
    PipelineRunCreate,
    PipelineRunList,
    PipelineRunResponse,
    PipelineRunUpdate,
    VALID_STATUSES,
)
from datapulse.pipeline.repository import PipelineRepository

log = get_logger(__name__)


class PipelineService:
    """Orchestrates pipeline run operations with business rules."""

    def __init__(self, repo: PipelineRepository) -> None:
        self._repo = repo

    def start_run(
        self, data: PipelineRunCreate, tenant_id: int = 1,
    ) -> PipelineRunResponse:
        log.info("pipeline_start_run", run_type=data.run_type)
        return self._repo.create_run(data, tenant_id)

    def update_status(
        self, run_id: UUID, data: PipelineRunUpdate,
    ) -> PipelineRunResponse | None:
        if data.status is not None and data.status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{data.status}'. "
                f"Must be one of: {', '.join(sorted(VALID_STATUSES))}"
            )
        return self._repo.update_run(run_id, data)

    def complete_run(
        self,
        run_id: UUID,
        rows_loaded: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PipelineRunResponse | None:
        existing = self._repo.get_run(run_id)
        if existing is None:
            return None

        now = datetime.now(timezone.utc)
        started = existing.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        duration = Decimal(str((now - started).total_seconds())).quantize(
            Decimal("0.01")
        )

        update = PipelineRunUpdate(
            status="success",
            finished_at=now,
            duration_seconds=duration,
            rows_loaded=rows_loaded,
            metadata=metadata,
        )
        log.info("pipeline_complete_run", run_id=str(run_id), duration=float(duration))
        return self._repo.update_run(run_id, update)

    def fail_run(
        self, run_id: UUID, error_message: str,
    ) -> PipelineRunResponse | None:
        existing = self._repo.get_run(run_id)
        if existing is None:
            return None

        now = datetime.now(timezone.utc)
        started = existing.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        duration = Decimal(str((now - started).total_seconds())).quantize(
            Decimal("0.01")
        )

        update = PipelineRunUpdate(
            status="failed",
            finished_at=now,
            duration_seconds=duration,
            error_message=error_message,
        )
        log.error("pipeline_fail_run", run_id=str(run_id), error=error_message)
        return self._repo.update_run(run_id, update)

    def get_run(self, run_id: UUID) -> PipelineRunResponse | None:
        return self._repo.get_run(run_id)

    def list_runs(
        self,
        *,
        status: str | None = None,
        started_after: datetime | None = None,
        started_before: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> PipelineRunList:
        if status is not None and status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. "
                f"Must be one of: {', '.join(sorted(VALID_STATUSES))}"
            )
        return self._repo.list_runs(
            status=status,
            started_after=started_after,
            started_before=started_before,
            offset=offset,
            limit=limit,
        )

    def get_latest_run(
        self, run_type: str | None = None,
    ) -> PipelineRunResponse | None:
        return self._repo.get_latest_run(run_type)

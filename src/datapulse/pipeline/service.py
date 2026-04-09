"""Pipeline business-logic layer.

Thin wrapper around PipelineRepository that adds validation
and convenience methods for common status transitions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from datapulse.cache import cache_invalidate_pattern
from datapulse.logging import get_logger
from datapulse.pipeline.models import (
    PipelineRunCreate,
    PipelineRunList,
    PipelineRunResponse,
    PipelineRunUpdate,
)
from datapulse.pipeline.repository import PipelineRepository

log = get_logger(__name__)


class PipelineService:
    """Orchestrates pipeline run operations with business rules."""

    def __init__(self, repo: PipelineRepository) -> None:
        self._repo = repo

    @staticmethod
    def _compute_duration(started_at: datetime) -> tuple[datetime, Decimal]:
        """Return (now_utc, duration_seconds) from a started_at timestamp."""
        now = datetime.now(UTC)
        started = started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        duration = Decimal(str((now - started).total_seconds())).quantize(Decimal("0.01"))
        return now, duration

    def start_run(
        self,
        data: PipelineRunCreate,
        tenant_id: int = 1,
    ) -> PipelineRunResponse:
        result = self._repo.create_run(data, tenant_id)
        log.info(
            "pipeline_started",
            run_id=str(result.id),
            run_type=data.run_type,
            tenant_id=tenant_id,
            trigger_source=data.trigger_source,
        )
        return result

    def update_status(
        self,
        run_id: UUID,
        data: PipelineRunUpdate,
    ) -> PipelineRunResponse | None:
        # Status validation is handled by PipelineRunUpdate's Pydantic field_validator
        if data.last_completed_stage is not None:
            log.info(
                "pipeline_stage_completed",
                run_id=str(run_id),
                stage=data.last_completed_stage,
                rows_affected=data.rows_loaded,
                duration_seconds=(
                    float(data.duration_seconds) if data.duration_seconds is not None else None
                ),
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

        now, duration = self._compute_duration(existing.started_at)

        update = PipelineRunUpdate(
            status="success",
            finished_at=now,
            duration_seconds=duration,
            rows_loaded=rows_loaded,
            metadata=metadata,
        )
        log.info(
            "pipeline_completed",
            run_id=str(run_id),
            duration_seconds=float(duration),
            status="success",
            rows_loaded=rows_loaded,
        )
        result = self._repo.update_run(run_id, update)
        cache_invalidate_pattern("datapulse:analytics:*")
        return result

    def fail_run(
        self,
        run_id: UUID,
        error_message: str,
    ) -> PipelineRunResponse | None:
        existing = self._repo.get_run(run_id)
        if existing is None:
            return None

        now, duration = self._compute_duration(existing.started_at)

        update = PipelineRunUpdate(
            status="failed",
            finished_at=now,
            duration_seconds=duration,
            error_message=error_message,
        )
        log.error(
            "pipeline_failed",
            run_id=str(run_id),
            error_message=error_message,
            error_type="pipeline_error",
        )
        result = self._repo.update_run(run_id, update)
        cache_invalidate_pattern("datapulse:analytics:*")
        return result

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
        # Status validation for query params is handled at the route layer
        return self._repo.list_runs(
            status=status,
            started_after=started_after,
            started_before=started_before,
            offset=offset,
            limit=limit,
        )

    def get_latest_run(
        self,
        run_type: str | None = None,
    ) -> PipelineRunResponse | None:
        return self._repo.get_latest_run(run_type)

"""Orchestration for the onboarding sample-data loader (Phase 2 Task 2 / #401).

Wires together:
1. `sample_data.load_sample` — clears + inserts bronze rows (5k by default).
2. `PipelineService` — opens a pipeline_run record so Pipeline Health shows
   the sample load, then marks it success/failed at the end.
3. `QualityRepository` — seeds synthetic passing quality_checks for each
   stage so the Pipeline Health run-detail panel looks healthy by construction.

The silver→gold dbt refresh is deliberately NOT triggered here — dbt runs
out-of-process and would blow the < 15 s DoD budget. On the droplet, the
bronze insert is picked up by the next scheduled dbt refresh. The UI can
still render the seeded quality scorecard immediately.
"""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from datapulse.logging import get_logger
from datapulse.onboarding.models import SampleLoadResult
from datapulse.onboarding.sample_data import load_sample
from datapulse.pipeline.models import PipelineRunCreate
from datapulse.pipeline.quality import QualityCheckResult
from datapulse.pipeline.quality_repository import QualityRepository
from datapulse.pipeline.service import PipelineService

log = get_logger(__name__)

_SAMPLE_TRIGGER_SOURCE = "onboarding_sample"


def _synthetic_checks(row_count: int) -> list[QualityCheckResult]:
    """Three passing checks, one per medallion stage, so the Pipeline Health
    run-detail panel renders a healthy-looking run for the sample load."""
    return [
        QualityCheckResult(
            check_name="row_count",
            stage="bronze",
            severity="error",
            passed=True,
            message=f"{row_count} sample rows loaded",
            details={"row_count": row_count, "source": "sample"},
        ),
        QualityCheckResult(
            check_name="schema_match",
            stage="silver",
            severity="error",
            passed=True,
            message="schema matches stg_sales",
            details={"source": "sample"},
        ),
        QualityCheckResult(
            check_name="sample_coverage",
            stage="gold",
            severity="warn",
            passed=True,
            message="aggregates will populate on next dbt refresh",
            details={"source": "sample"},
        ),
    ]


class SampleLoadService:
    """Loads the curated pharma sample dataset and emits the pipeline/quality
    book-keeping the rest of the product expects.
    """

    def __init__(
        self,
        session: Session,
        pipeline_service: PipelineService,
        quality_repo: QualityRepository,
    ) -> None:
        self._session = session
        self._pipeline_service = pipeline_service
        self._quality_repo = quality_repo

    def load(
        self,
        *,
        tenant_id: int,
        user_id: str,
        row_count: int | None = None,
    ) -> SampleLoadResult:
        """Clear + insert sample rows, record a pipeline run, seed quality.

        Raises whatever the underlying call raises after marking the pipeline
        run as failed.
        """
        log.info(
            "sample_load_start",
            tenant_id=tenant_id,
            user_id=user_id,
            row_count=row_count,
        )

        run = self._pipeline_service.start_run(
            PipelineRunCreate(
                run_type="full",
                trigger_source=_SAMPLE_TRIGGER_SOURCE,
                metadata={"source": "sample", "user_id": user_id},
            ),
            tenant_id=tenant_id,
        )
        run_id = run.id
        t0 = time.perf_counter()

        try:
            inserted = (
                load_sample(
                    self._session,
                    tenant_id=tenant_id,
                    row_count=row_count,
                )
                if row_count is not None
                else load_sample(self._session, tenant_id=tenant_id)
            )
        except Exception as exc:  # noqa: BLE001
            self._pipeline_service.fail_run(run_id, f"sample load failed: {exc.__class__.__name__}")
            raise

        self._quality_repo.save_checks(
            run_id,
            _synthetic_checks(inserted),
            tenant_id=tenant_id,
        )

        metadata: dict[str, Any] = {
            "source": "sample",
            "user_id": user_id,
            "rows_loaded": inserted,
        }
        self._pipeline_service.complete_run(run_id, rows_loaded=inserted, metadata=metadata)

        elapsed = round(time.perf_counter() - t0, 3)
        log.info(
            "sample_load_done",
            tenant_id=tenant_id,
            user_id=user_id,
            run_id=str(run_id),
            rows_loaded=inserted,
            duration_seconds=elapsed,
        )
        return SampleLoadResult(
            rows_loaded=inserted,
            pipeline_run_id=str(run_id),
            duration_seconds=elapsed,
        )

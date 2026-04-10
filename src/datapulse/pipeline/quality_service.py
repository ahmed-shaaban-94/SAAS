"""Quality gate business logic layer.

Orchestrates check-function dispatch for each pipeline stage, handles
special-case parameter injection (stage, selector, settings), persists
results, and returns a QualityReport.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy.exc
from sqlalchemy.orm import Session

from datapulse.config import Settings
from datapulse.logging import get_logger
from datapulse.pipeline.models import QualityScorecard, RunScore
from datapulse.pipeline.quality import (
    STAGE_CHECKS,
    VALID_STAGES,
    QualityCheckList,
    QualityCheckResult,
    QualityReport,
    check_null_rate,
    run_dbt_tests,
)
from datapulse.pipeline.quality_repository import QualityRepository

log = get_logger(__name__)

# dbt selector used when running quality tests for the gold stage
_GOLD_DBT_SELECTOR = "marts"


class QualityService:
    """Runs quality checks for a pipeline stage and persists the results."""

    def __init__(
        self,
        repo: QualityRepository,
        session: Session,
        settings: Settings,
    ) -> None:
        self._repo = repo
        self._session = session
        self._settings = settings

    def run_checks_for_stage(
        self,
        run_id: UUID,
        stage: str,
        tenant_id: int = 1,
    ) -> QualityReport:
        """Execute all checks registered for *stage* and persist results.

        Special-case dispatch rules:
        - ``check_null_rate``  receives an extra ``stage`` keyword argument.
        - ``run_dbt_tests``    receives ``selector`` and ``settings`` positional
                               arguments instead of a session.
        - All other checks     receive ``(session, run_id)``.

        Returns a :class:`QualityReport`.  ``gate_passed`` is ``True`` when
        every ``severity='error'`` check passes; blocking the caller from
        advancing the pipeline when ``False``.
        """
        if stage not in VALID_STAGES:
            raise ValueError(
                f"Invalid stage '{stage}'. Must be one of: {', '.join(sorted(VALID_STAGES))}"
            )

        log.info("quality_run_checks_start", run_id=str(run_id), stage=stage)

        check_fns = STAGE_CHECKS.get(stage, [])
        results: list[QualityCheckResult] = []

        for fn in check_fns:
            try:
                if fn is run_dbt_tests:
                    result = fn(run_id, _GOLD_DBT_SELECTOR, self._settings)
                elif fn is check_null_rate:
                    result = fn(self._session, run_id, stage=stage)
                else:
                    result = fn(self._session, run_id)
            except (sqlalchemy.exc.SQLAlchemyError, OSError) as exc:
                log.error(
                    "quality_check_exception",
                    run_id=str(run_id),
                    check=fn.__name__,
                    error=str(exc),
                )
                result = QualityCheckResult(
                    check_name=fn.__name__,
                    stage=stage,
                    severity="error",
                    passed=False,
                    message="Check raised an unexpected exception",
                    details={},
                )

            log.info(
                "quality_check_result",
                run_id=str(run_id),
                check=result.check_name,
                passed=result.passed,
                severity=result.severity,
            )
            results.append(result)

        # Persist before building the report so checked_at timestamps are DB-generated
        self._repo.save_checks(run_id, results, tenant_id=tenant_id)

        all_passed = all(c.passed for c in results)
        gate_passed = all(c.passed for c in results if c.severity == "error")

        log.info(
            "quality_run_checks_done",
            run_id=str(run_id),
            stage=stage,
            all_passed=all_passed,
            gate_passed=gate_passed,
            checks_run=len(results),
        )

        return QualityReport(
            pipeline_run_id=run_id,
            stage=stage,
            checks=results,
            all_passed=all_passed,
            gate_passed=gate_passed,
            checked_at=datetime.now(UTC),
        )

    def get_checks(
        self,
        run_id: UUID,
        stage: str | None = None,
    ) -> QualityCheckList:
        """Return persisted quality checks for a run, optionally filtered by stage."""
        return self._repo.get_checks_for_run(run_id, stage=stage)

    def get_scorecard(self, limit: int = 20) -> QualityScorecard:
        """Build a quality scorecard from recent pipeline runs."""

        rows = self._repo.get_scorecard(limit=limit)
        runs = []
        total_passed = 0
        total_checks = 0
        for r in rows:
            tc = r["total_checks"]
            p = r["passed"]
            total_passed += p
            total_checks += tc
            runs.append(
                RunScore(
                    run_id=r["run_id"],
                    run_type=r["run_type"],
                    status=r["status"],
                    started_at=r["started_at"],
                    total_checks=tc,
                    passed=p,
                    failed=r["failed"],
                    warned=r["warned"],
                    pass_rate=round(p / tc * 100, 1) if tc > 0 else 0.0,
                )
            )
        overall = round(total_passed / total_checks * 100, 1) if total_checks > 0 else 0.0
        return QualityScorecard(
            runs=runs,
            overall_pass_rate=overall,
            total_runs=len(runs),
        )

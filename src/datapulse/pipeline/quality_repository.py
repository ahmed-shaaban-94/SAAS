"""Data-access layer for the quality_checks table.

All SQL uses parameterized queries via SQLAlchemy text() — no f-string
interpolation of user-supplied values.
"""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger
from datapulse.pipeline.quality import (
    QualityCheckList,
    QualityCheckResponse,
    QualityCheckResult,
)

log = get_logger(__name__)

_COLUMNS = (
    "id, tenant_id, pipeline_run_id, check_name, stage, "
    "severity, passed, message, details, checked_at"
)


class QualityRepository:
    """Thin data-access layer for quality check persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _row_to_response(row) -> QualityCheckResponse:
        details = row._mapping["details"]
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except json.JSONDecodeError:
                details = {}
        return QualityCheckResponse(
            id=row._mapping["id"],
            tenant_id=row._mapping["tenant_id"],
            pipeline_run_id=row._mapping["pipeline_run_id"],
            check_name=row._mapping["check_name"],
            stage=row._mapping["stage"],
            severity=row._mapping["severity"],
            passed=row._mapping["passed"],
            message=row._mapping["message"],
            details=details if details is not None else {},
            checked_at=row._mapping["checked_at"],
        )

    def save_checks(
        self,
        run_id: UUID,
        checks: list[QualityCheckResult],
        tenant_id: int = 1,
    ) -> list[QualityCheckResponse]:
        """Batch-INSERT all check results and return the persisted rows.

        Builds all parameters upfront, then executes individual inserts
        within a single transaction (commit at end). This is more efficient
        than committing per-row, while still using RETURNING for each insert.
        """
        log.info(
            "quality_save_checks",
            run_id=str(run_id),
            count=len(checks),
            tenant_id=tenant_id,
        )
        stmt = text("""
            INSERT INTO public.quality_checks
                (tenant_id, pipeline_run_id, check_name, stage,
                 severity, passed, message, details)
            VALUES
                (:tenant_id, :pipeline_run_id, :check_name, :stage,
                 :severity, :passed, :message, :details::jsonb)
            RETURNING id, tenant_id, pipeline_run_id, check_name, stage,
                      severity, passed, message, details, checked_at
        """)

        # Build all param dicts upfront
        all_params = [
            {
                "tenant_id": tenant_id,
                "pipeline_run_id": str(run_id),
                "check_name": check.check_name,
                "stage": check.stage,
                "severity": check.severity,
                "passed": check.passed,
                "message": check.message,
                "details": json.dumps(check.details),
            }
            for check in checks
        ]

        responses: list[QualityCheckResponse] = []
        try:
            for params in all_params:
                row = self._session.execute(stmt, params).fetchone()
                responses.append(self._row_to_response(row))
            self._session.commit()
        except Exception as exc:
            log.error("quality_checks_save_failed", error=str(exc))
            self._session.rollback()
            raise
        return responses

    def get_scorecard(self, limit: int = 20) -> list[dict]:
        """Aggregate quality check stats per pipeline run."""
        stmt = text("""
            SELECT
                qc.pipeline_run_id AS run_id,
                pr.run_type,
                pr.status,
                pr.started_at,
                COUNT(*) AS total_checks,
                COUNT(*) FILTER (WHERE qc.passed) AS passed,
                COUNT(*) FILTER (WHERE NOT qc.passed AND qc.severity = 'error') AS failed,
                COUNT(*) FILTER (WHERE NOT qc.passed AND qc.severity = 'warn') AS warned
            FROM public.quality_checks qc
            JOIN public.pipeline_runs pr ON pr.id = qc.pipeline_run_id
            GROUP BY qc.pipeline_run_id, pr.run_type, pr.status, pr.started_at
            ORDER BY pr.started_at DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, {"limit": limit}).mappings().all()
        return [dict(r) for r in rows]

    def get_checks_for_run(
        self,
        run_id: UUID,
        stage: str | None = None,
    ) -> QualityCheckList:
        """Return all quality checks for a given pipeline run, optionally filtered by stage."""
        params: dict = {"run_id": str(run_id), "stage": stage}

        count_stmt = text("""
            SELECT COUNT(*)
            FROM public.quality_checks
            WHERE pipeline_run_id = :run_id
              AND (:stage IS NULL OR stage = :stage)
        """)
        total: int = self._session.execute(count_stmt, params).scalar_one()

        select_stmt = text("""
            SELECT id, tenant_id, pipeline_run_id, check_name, stage,
                   severity, passed, message, details, checked_at
            FROM public.quality_checks
            WHERE pipeline_run_id = :run_id
              AND (:stage IS NULL OR stage = :stage)
            ORDER BY checked_at ASC
        """)
        rows = self._session.execute(select_stmt, params).fetchall()

        return QualityCheckList(
            items=[self._row_to_response(r) for r in rows],
            total=total,
        )

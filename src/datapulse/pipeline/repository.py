"""Data-access layer for the pipeline_runs table.

All SQL uses parameterized queries via SQLAlchemy text() — no f-string
interpolation of user-supplied values.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger
from datapulse.pipeline.models import (
    PipelineRunCreate,
    PipelineRunList,
    PipelineRunResponse,
    PipelineRunUpdate,
)

log = get_logger(__name__)

_COLUMNS = (
    "id, tenant_id, run_type, status, trigger_source, "
    "started_at, finished_at, duration_seconds, rows_loaded, "
    "error_message, metadata"
)

_UPDATABLE_COLUMNS = frozenset(
    {
        "status",
        "finished_at",
        "duration_seconds",
        "rows_loaded",
        "error_message",
        "metadata",
        "last_completed_stage",
    }
)

_SAFE_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


class PipelineRepository:
    """Thin data-access layer for pipeline run tracking."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _row_to_response(row) -> PipelineRunResponse:
        meta = row._mapping.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = {}
        return PipelineRunResponse(
            id=row._mapping["id"],
            tenant_id=row._mapping["tenant_id"],
            run_type=row._mapping["run_type"],
            status=row._mapping["status"],
            trigger_source=row._mapping["trigger_source"],
            started_at=row._mapping["started_at"],
            finished_at=row._mapping["finished_at"],
            duration_seconds=(
                Decimal(str(row._mapping["duration_seconds"]))
                if row._mapping["duration_seconds"] is not None
                else None
            ),
            rows_loaded=row._mapping["rows_loaded"],
            error_message=row._mapping["error_message"],
            metadata=meta,
        )

    def create_run(
        self,
        data: PipelineRunCreate,
        tenant_id: int = 1,
    ) -> PipelineRunResponse:
        log.info("create_pipeline_run", run_type=data.run_type, trigger=data.trigger_source)
        stmt = text(f"""
            INSERT INTO public.pipeline_runs
                (run_type, trigger_source, metadata, tenant_id)
            VALUES
                (:run_type, :trigger_source, CAST(:metadata AS jsonb), :tenant_id)
            RETURNING {_COLUMNS}
        """)
        row = self._session.execute(
            stmt,
            {
                "run_type": data.run_type,
                "trigger_source": data.trigger_source,
                "metadata": json.dumps(data.metadata),
                "tenant_id": tenant_id,
            },
        ).fetchone()
        self._session.commit()
        return self._row_to_response(row)

    def update_run(
        self,
        run_id: UUID,
        data: PipelineRunUpdate,
    ) -> PipelineRunResponse | None:
        fields = data.model_dump(exclude_none=True)
        if not fields:
            return self.get_run(run_id)

        set_parts: list[str] = []
        params: dict = {"run_id": str(run_id)}

        for key, value in fields.items():
            if key not in _UPDATABLE_COLUMNS:
                raise ValueError(f"Cannot update column: {key}")
            if not _SAFE_IDENTIFIER_RE.match(key):
                raise ValueError(f"Unsafe column name: {key!r}")
            if key == "metadata":
                set_parts.append("metadata = CAST(:metadata AS jsonb)")
                params["metadata"] = json.dumps(value)
            elif key == "duration_seconds":
                set_parts.append("duration_seconds = :duration_seconds")
                params["duration_seconds"] = float(value)
            else:
                set_parts.append(f"{key} = :{key}")
                params[key] = value

        set_clause = ", ".join(set_parts)
        log.info("update_pipeline_run", run_id=str(run_id), fields=list(fields.keys()))

        stmt = text(f"""
            UPDATE public.pipeline_runs
            SET {set_clause}
            WHERE id = :run_id
            RETURNING {_COLUMNS}
        """)
        row = self._session.execute(stmt, params).fetchone()
        if row is None:
            return None
        self._session.commit()
        return self._row_to_response(row)

    def get_run(self, run_id: UUID) -> PipelineRunResponse | None:
        log.info("get_pipeline_run", run_id=str(run_id))
        stmt = text(f"""
            SELECT {_COLUMNS}
            FROM public.pipeline_runs
            WHERE id = :run_id
        """)
        row = self._session.execute(stmt, {"run_id": str(run_id)}).fetchone()
        if row is None:
            return None
        return self._row_to_response(row)

    def list_runs(
        self,
        *,
        status: str | None = None,
        started_after: datetime | None = None,
        started_before: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> PipelineRunList:
        clauses: list[str] = []
        params: dict = {}

        if status is not None:
            clauses.append("status = :status")
            params["status"] = status
        if started_after is not None:
            clauses.append("started_at >= :started_after")
            params["started_after"] = started_after
        if started_before is not None:
            clauses.append("started_at <= :started_before")
            params["started_before"] = started_before

        where = "WHERE " + " AND ".join(clauses) if clauses else ""

        count_stmt = text(f"SELECT COUNT(*) FROM public.pipeline_runs {where}")
        total = self._session.execute(count_stmt, params).scalar_one()

        params["limit"] = limit
        params["offset"] = offset
        select_stmt = text(f"""
            SELECT {_COLUMNS}
            FROM public.pipeline_runs
            {where}
            ORDER BY started_at DESC
            LIMIT :limit OFFSET :offset
        """)
        rows = self._session.execute(select_stmt, params).fetchall()

        return PipelineRunList(
            items=[self._row_to_response(r) for r in rows],
            total=total,
            offset=offset,
            limit=limit,
        )

    def update_heartbeat(self, run_id: UUID) -> None:
        """Touch heartbeat_at for a running pipeline to signal liveness."""
        self._session.execute(
            text(
                "UPDATE public.pipeline_runs "
                "SET heartbeat_at = now() "
                "WHERE id = :run_id AND status = 'running'"
            ),
            {"run_id": str(run_id)},
        )
        self._session.commit()

    def mark_stale_runs_failed(self, stale_minutes: int = 10) -> list[str]:
        """Mark pipeline runs as failed if heartbeat is older than *stale_minutes*.

        Returns list of run IDs that were marked stale.
        """
        rows = self._session.execute(
            text(
                "UPDATE public.pipeline_runs "
                "SET status = 'failed', "
                "    error_message = 'Stale: heartbeat timeout', "
                "    finished_at = now() "
                "WHERE status = 'running' "
                "  AND heartbeat_at IS NOT NULL "
                "  AND heartbeat_at < now() - make_interval(mins => :mins) "
                "RETURNING id::text"
            ),
            {"mins": stale_minutes},
        ).fetchall()
        if rows:
            self._session.commit()
        return [r[0] for r in rows]

    def get_latest_run(
        self,
        run_type: str | None = None,
    ) -> PipelineRunResponse | None:
        params: dict = {}
        where = ""
        if run_type is not None:
            where = "WHERE run_type = :run_type"
            params["run_type"] = run_type

        stmt = text(f"""
            SELECT {_COLUMNS}
            FROM public.pipeline_runs
            {where}
            ORDER BY started_at DESC
            LIMIT 1
        """)
        row = self._session.execute(stmt, params).fetchone()
        if row is None:
            return None
        return self._row_to_response(row)

    # ── Dashboard health composite (#509) ───────────────────────────────

    def get_latest_run_per_type(self) -> dict[str, PipelineRunResponse]:
        """Latest run per ``run_type`` — used by the dashboard health card.

        Uses DISTINCT ON to return the most recent row per ``run_type`` in
        a single round-trip. Scoped by RLS to the current tenant.
        """
        stmt = text(f"""
            SELECT DISTINCT ON (run_type) {_COLUMNS}
            FROM public.pipeline_runs
            ORDER BY run_type, started_at DESC
        """)
        rows = self._session.execute(stmt).fetchall()
        return {row._mapping["run_type"]: self._row_to_response(row) for row in rows}

    def get_recent_days_summary(self, days: int = 7) -> list[dict]:
        """Day-by-day pipeline activity for the health history strip.

        Returns the latest ``full`` run per day, or the worst-status run
        when multiple ran in a day. Missing days are filled in by the
        caller (the SQL only returns days with at least one run).
        """
        stmt = text("""
            WITH runs AS (
                SELECT
                    DATE(started_at) AS run_date,
                    status,
                    duration_seconds,
                    ROW_NUMBER() OVER (
                        PARTITION BY DATE(started_at)
                        ORDER BY
                            CASE status
                                WHEN 'failed'  THEN 0
                                WHEN 'warning' THEN 1
                                WHEN 'running' THEN 2
                                WHEN 'success' THEN 3
                                ELSE 4
                            END,
                            started_at DESC
                    ) AS rn
                FROM public.pipeline_runs
                WHERE started_at >= CURRENT_DATE - make_interval(days => :days - 1)
                  AND run_type = 'full'
            )
            SELECT run_date, status, duration_seconds
            FROM runs
            WHERE rn = 1
            ORDER BY run_date
        """)
        rows = self._session.execute(stmt, {"days": days}).mappings().all()
        return [dict(r) for r in rows]

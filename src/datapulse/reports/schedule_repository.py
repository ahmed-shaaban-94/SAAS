"""Repository for report schedule CRUD."""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.reports.schedule_models import (
    ReportScheduleCreate,
    ReportScheduleResponse,
    ReportScheduleUpdate,
)


class ScheduleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _row_to_response(row: dict) -> ReportScheduleResponse:
        recipients = row.get("recipients", [])
        if isinstance(recipients, str):
            recipients = json.loads(recipients)
        parameters = row.get("parameters", {})
        if isinstance(parameters, str):
            parameters = json.loads(parameters)
        return ReportScheduleResponse(
            id=row["id"],
            name=row["name"],
            report_type=row["report_type"],
            cron_expression=row["cron_expression"],
            recipients=recipients,
            parameters=parameters,
            enabled=row["enabled"],
            last_run_at=row.get("last_run_at"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_schedules(self) -> list[ReportScheduleResponse]:
        stmt = text("""
            SELECT id, name, report_type, cron_expression, recipients,
                   parameters, enabled, last_run_at, created_at, updated_at
            FROM public.report_schedules
            ORDER BY created_at DESC
        """)
        rows = self._session.execute(stmt).mappings().all()
        return [self._row_to_response(dict(r)) for r in rows]

    def create_schedule(self, data: ReportScheduleCreate) -> ReportScheduleResponse:
        stmt = text("""
            INSERT INTO public.report_schedules
                (name, report_type, cron_expression, recipients, parameters, enabled)
            VALUES
                (:name, :report_type, :cron_expression,
                 :recipients::jsonb, :parameters::jsonb, :enabled)
            RETURNING id, name, report_type, cron_expression, recipients,
                      parameters, enabled, last_run_at, created_at, updated_at
        """)
        row = (
            self._session.execute(
                stmt,
                {
                    "name": data.name,
                    "report_type": data.report_type,
                    "cron_expression": data.cron_expression,
                    "recipients": json.dumps(data.recipients),
                    "parameters": json.dumps(data.parameters),
                    "enabled": data.enabled,
                },
            )
            .mappings()
            .first()
        )
        self._session.flush()
        return self._row_to_response(dict(row))  # type: ignore[arg-type]

    def update_schedule(
        self, schedule_id: int, data: ReportScheduleUpdate
    ) -> ReportScheduleResponse | None:
        updates = []
        params: dict = {"id": schedule_id}
        if data.name is not None:
            updates.append("name = :name")
            params["name"] = data.name
        if data.cron_expression is not None:
            updates.append("cron_expression = :cron_expression")
            params["cron_expression"] = data.cron_expression
        if data.recipients is not None:
            updates.append("recipients = :recipients::jsonb")
            params["recipients"] = json.dumps(data.recipients)
        if data.parameters is not None:
            updates.append("parameters = :parameters::jsonb")
            params["parameters"] = json.dumps(data.parameters)
        if data.enabled is not None:
            updates.append("enabled = :enabled")
            params["enabled"] = data.enabled

        if not updates:
            return None

        updates.append("updated_at = NOW()")
        set_clause = ", ".join(updates)

        stmt = text(f"""
            UPDATE public.report_schedules
            SET {set_clause}
            WHERE id = :id
            RETURNING id, name, report_type, cron_expression, recipients,
                      parameters, enabled, last_run_at, created_at, updated_at
        """)  # noqa: S608
        row = self._session.execute(stmt, params).mappings().first()
        self._session.flush()
        return self._row_to_response(dict(row)) if row else None

    def delete_schedule(self, schedule_id: int) -> bool:
        stmt = text("DELETE FROM public.report_schedules WHERE id = :id")
        result = self._session.execute(stmt, {"id": schedule_id})
        self._session.flush()
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]

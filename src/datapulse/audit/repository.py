"""Repository for audit log queries."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.core.sql import build_where


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(
        self,
        *,
        action: str | None = None,
        endpoint: str | None = None,
        method: str | None = None,
        user_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        # Wildcards are wrapped at the call site per build_where's contract;
        # the helper binds the value as-is. Date bounds are kept as literal
        # extra_clauses because they need a ``CAST(... AS timestamptz)`` on
        # the value — a shape the tuple-form helper intentionally does not
        # support (operators don't encode value transforms).
        endpoint_pattern = f"%{endpoint}%" if endpoint else None

        extra: list[str] = []
        date_params: dict = {}
        if start_date:
            extra.append("created_at >= CAST(:start_date AS timestamptz)")
            date_params["start_date"] = start_date
        if end_date:
            # End side is "< next_day" so the range is half-open — matches the
            # inclusive-end semantics the UI presents to the user.
            extra.append(
                "created_at < CAST(CAST(:end_date AS date) + INTERVAL '1 day' AS timestamptz)"
            )
            date_params["end_date"] = end_date

        where_body, params = build_where(
            [
                ("action", "=", "action", action),
                ("endpoint", "ILIKE", "endpoint", endpoint_pattern),
                ("method", "=", "method", method),
                ("user_id", "=", "user_id", user_id),
            ],
            extra_clauses=extra,
        )
        params.update(date_params)
        where = f"WHERE {where_body}" if where_body != "1=1" else ""

        count_sql = text(f"SELECT COUNT(*) FROM public.audit_log {where}")  # noqa: S608
        total = self._session.execute(count_sql, params).scalar() or 0

        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size

        sql = text(f"""
            SELECT id, action, endpoint, method, ip_address, user_id,
                   response_status, duration_ms, created_at
            FROM public.audit_log
            {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)  # noqa: S608
        rows = self._session.execute(sql, params).mappings().all()
        return [dict(r) for r in rows], total

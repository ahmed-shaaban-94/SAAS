"""Repository for audit log queries."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


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
        conditions: list[str] = []
        params: dict = {}

        if action:
            conditions.append("action = :action")
            params["action"] = action
        if endpoint:
            conditions.append("endpoint ILIKE :endpoint")
            params["endpoint"] = f"%{endpoint}%"
        if method:
            conditions.append("method = :method")
            params["method"] = method
        if user_id:
            conditions.append("user_id = :user_id")
            params["user_id"] = user_id
        if start_date:
            conditions.append("created_at >= CAST(:start_date AS timestamptz)")
            params["start_date"] = start_date
        if end_date:
            conditions.append(
                "created_at < CAST(CAST(:end_date AS date) + INTERVAL '1 day' AS timestamptz)"
            )
            params["end_date"] = end_date

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

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

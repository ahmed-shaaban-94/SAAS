"""Repository for chart annotations CRUD."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


class AnnotationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_by_chart(self, chart_id: str) -> list[dict]:
        sql = text("""
            SELECT id, chart_id, data_point, note, color, user_id, created_at
            FROM public.annotations
            WHERE chart_id = :cid
            ORDER BY created_at DESC
        """)
        rows = self._session.execute(sql, {"cid": chart_id}).mappings().all()
        return [dict(r) for r in rows]

    def create(
        self,
        tenant_id: int,
        user_id: str,
        chart_id: str,
        data_point: str,
        note: str,
        color: str,
    ) -> dict:
        sql = text("""
            INSERT INTO public.annotations
                (tenant_id, user_id, chart_id, data_point, note, color)
            VALUES (:tid, :uid, :cid, :dp, :note, :color)
            RETURNING id, chart_id, data_point, note, color, user_id, created_at
        """)
        row = (
            self._session.execute(
                sql,
                {
                    "tid": tenant_id,
                    "uid": user_id,
                    "cid": chart_id,
                    "dp": data_point,
                    "note": note,
                    "color": color,
                },
            )
            .mappings()
            .first()
        )
        self._session.flush()
        return dict(row) if row else {}

    def delete(self, annotation_id: int, user_id: str) -> bool:
        sql = text("DELETE FROM public.annotations WHERE id = :aid AND user_id = :uid")
        result = self._session.execute(sql, {"aid": annotation_id, "uid": user_id})
        self._session.flush()
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]

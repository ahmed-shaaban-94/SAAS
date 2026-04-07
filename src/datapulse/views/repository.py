"""Repository for saved views CRUD."""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session


class ViewsRepository:
    MAX_VIEWS_PER_USER = 20

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_views(self, user_id: str) -> list[dict]:
        sql = text("""
            SELECT id, name, page_path, filters, is_default, created_at
            FROM public.saved_views
            WHERE user_id = :uid
            ORDER BY is_default DESC, created_at DESC
        """)
        rows = self._session.execute(sql, {"uid": user_id}).mappings().all()
        return [dict(r) for r in rows]

    def get_view(self, view_id: int, user_id: str) -> dict | None:
        sql = text("""
            SELECT id, name, page_path, filters, is_default, created_at
            FROM public.saved_views
            WHERE id = :vid AND user_id = :uid
        """)
        row = self._session.execute(sql, {"vid": view_id, "uid": user_id}).mappings().first()
        return dict(row) if row else None

    def count_views(self, user_id: str) -> int:
        sql = text("SELECT COUNT(*) FROM public.saved_views WHERE user_id = :uid")
        return self._session.execute(sql, {"uid": user_id}).scalar() or 0

    def create_view(
        self,
        tenant_id: int,
        user_id: str,
        name: str,
        page_path: str,
        filters: dict,
        is_default: bool,
    ) -> dict:
        sql = text("""
            INSERT INTO public.saved_views
                (tenant_id, user_id, name, page_path, filters, is_default)
            VALUES (:tid, :uid, :name, :path, :filters, :default)
            RETURNING id, name, page_path, filters, is_default, created_at
        """)
        row = (
            self._session.execute(
                sql,
                {
                    "tid": tenant_id,
                    "uid": user_id,
                    "name": name,
                    "path": page_path,
                    "filters": json.dumps(filters),
                    "default": is_default,
                },
            )
            .mappings()
            .first()
        )
        self._session.flush()
        return dict(row) if row else {}

    def update_view(self, view_id: int, user_id: str, **fields: object) -> dict | None:
        sets: list[str] = []
        params: dict = {"vid": view_id, "uid": user_id}
        if "name" in fields and fields["name"] is not None:
            sets.append("name = :name")
            params["name"] = fields["name"]
        if "filters" in fields and fields["filters"] is not None:
            sets.append("filters = :filters")
            params["filters"] = json.dumps(fields["filters"])
        if "is_default" in fields and fields["is_default"] is not None:
            sets.append("is_default = :default")
            params["default"] = fields["is_default"]
        if not sets:
            return self.get_view(view_id, user_id)
        sql = text(f"""
            UPDATE public.saved_views SET {", ".join(sets)}
            WHERE id = :vid AND user_id = :uid
            RETURNING id, name, page_path, filters, is_default, created_at
        """)
        row = self._session.execute(sql, params).mappings().first()
        self._session.flush()
        return dict(row) if row else None

    def delete_view(self, view_id: int, user_id: str) -> bool:
        sql = text("DELETE FROM public.saved_views WHERE id = :vid AND user_id = :uid")
        result = self._session.execute(sql, {"vid": view_id, "uid": user_id})
        self._session.flush()
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]

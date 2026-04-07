"""Repository for notifications CRUD."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


class NotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_notifications(
        self, user_id: str, unread_only: bool = False, limit: int = 20
    ) -> list[dict]:
        where = "WHERE (user_id = :uid OR user_id IS NULL)"
        if unread_only:
            where += " AND read = false"
        sql = text(f"""
            SELECT id, type, title, message, link, read, created_at
            FROM public.notifications
            {where}
            ORDER BY created_at DESC
            LIMIT :lim
        """)
        rows = self._session.execute(sql, {"uid": user_id, "lim": limit}).mappings().all()
        return [dict(r) for r in rows]

    def unread_count(self, user_id: str) -> int:
        sql = text("""
            SELECT COUNT(*) FROM public.notifications
            WHERE (user_id = :uid OR user_id IS NULL) AND read = false
        """)
        return self._session.execute(sql, {"uid": user_id}).scalar() or 0

    def mark_read(self, notification_id: int, user_id: str) -> bool:
        sql = text("""
            UPDATE public.notifications SET read = true
            WHERE id = :nid AND (user_id = :uid OR user_id IS NULL)
        """)
        result = self._session.execute(sql, {"nid": notification_id, "uid": user_id})
        self._session.flush()
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]

    def mark_all_read(self, user_id: str) -> int:
        sql = text("""
            UPDATE public.notifications SET read = true
            WHERE (user_id = :uid OR user_id IS NULL) AND read = false
        """)
        result = self._session.execute(sql, {"uid": user_id})
        self._session.flush()
        return result.rowcount or 0  # type: ignore[attr-defined]

    def create(
        self,
        tenant_id: int,
        type_: str,
        title: str,
        message: str,
        link: str | None,
        user_id: str | None,
    ) -> dict:
        sql = text("""
            INSERT INTO public.notifications (tenant_id, user_id, type, title, message, link)
            VALUES (:tid, :uid, :type, :title, :msg, :link)
            RETURNING id, type, title, message, link, read, created_at
        """)
        row = (
            self._session.execute(
                sql,
                {
                    "tid": tenant_id,
                    "uid": user_id,
                    "type": type_,
                    "title": title,
                    "msg": message,
                    "link": link,
                },
            )
            .mappings()
            .first()
        )
        self._session.flush()
        return dict(row) if row else {}

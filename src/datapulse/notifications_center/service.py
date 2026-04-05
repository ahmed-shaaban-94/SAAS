"""Service layer for notification center."""

from __future__ import annotations

from datapulse.notifications_center.models import NotificationCount, NotificationResponse
from datapulse.notifications_center.repository import NotificationRepository


class NotificationService:
    def __init__(self, repo: NotificationRepository) -> None:
        self._repo = repo

    def list_notifications(
        self, user_id: str, unread_only: bool = False, limit: int = 20
    ) -> list[NotificationResponse]:
        rows = self._repo.list_notifications(user_id, unread_only, limit)
        return [NotificationResponse(**r) for r in rows]

    def unread_count(self, user_id: str) -> NotificationCount:
        count = self._repo.unread_count(user_id)
        return NotificationCount(unread=count)

    def mark_read(self, notification_id: int, user_id: str) -> None:
        self._repo.mark_read(notification_id, user_id)

    def mark_all_read(self, user_id: str) -> None:
        self._repo.mark_all_read(user_id)

    def create_notification(
        self,
        tenant_id: int,
        type_: str,
        title: str,
        message: str,
        link: str | None = None,
        user_id: str | None = None,
    ) -> NotificationResponse:
        row = self._repo.create(tenant_id, type_, title, message, link, user_id)
        return NotificationResponse(**row)

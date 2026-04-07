"""Service layer for audit log queries."""

from __future__ import annotations

from datapulse.audit.models import AuditLogEntry, AuditLogPage
from datapulse.audit.repository import AuditRepository


class AuditService:
    def __init__(self, repo: AuditRepository) -> None:
        self._repo = repo

    def list_entries(
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
    ) -> AuditLogPage:
        rows, total = self._repo.list(
            action=action,
            endpoint=endpoint,
            method=method,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
        return AuditLogPage(
            items=[AuditLogEntry(**r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

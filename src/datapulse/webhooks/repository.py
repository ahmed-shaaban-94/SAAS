"""Data access for outbound webhooks — subscriptions and delivery log."""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class WebhookRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    # ── Subscriptions ─────────────────────────────────────────────────────────

    def create_subscription(
        self,
        tenant_id: int,
        event_type: str,
        target_url: str,
        secret: str,
    ) -> dict[str, Any]:
        row = (
            self._s.execute(
                text(
                    "INSERT INTO webhooks.subscriptions "
                    "(tenant_id, event_type, target_url, secret) "
                    "VALUES (:tid, :evt, :url, :sec) "
                    "RETURNING id, event_type, target_url, is_active, created_at"
                ),
                {"tid": tenant_id, "evt": event_type, "url": target_url, "sec": secret},
            )
            .mappings()
            .one()
        )
        return dict(row)

    def list_subscriptions(self, tenant_id: int) -> list[dict[str, Any]]:
        rows = (
            self._s.execute(
                text(
                    "SELECT id, event_type, target_url, is_active, created_at "
                    "FROM webhooks.subscriptions "
                    "WHERE tenant_id = :tid ORDER BY created_at DESC"
                ),
                {"tid": tenant_id},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_subscription(self, subscription_id: int, tenant_id: int) -> dict[str, Any] | None:
        row = (
            self._s.execute(
                text(
                    "SELECT id, event_type, target_url, secret, is_active, created_at "
                    "FROM webhooks.subscriptions "
                    "WHERE id = :sid AND tenant_id = :tid"
                ),
                {"sid": subscription_id, "tid": tenant_id},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def delete_subscription(self, subscription_id: int, tenant_id: int) -> bool:
        result = self._s.execute(
            text("DELETE FROM webhooks.subscriptions WHERE id = :sid AND tenant_id = :tid"),
            {"sid": subscription_id, "tid": tenant_id},
        )
        return result.rowcount > 0  # type: ignore[attr-defined]

    def get_active_subscribers(self, tenant_id: int, event_type: str) -> list[dict[str, Any]]:
        rows = (
            self._s.execute(
                text(
                    "SELECT id, target_url, secret FROM webhooks.subscriptions "
                    "WHERE tenant_id = :tid AND event_type = :evt AND is_active = true"
                ),
                {"tid": tenant_id, "evt": event_type},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    # ── Delivery log ──────────────────────────────────────────────────────────

    def create_delivery(
        self,
        subscription_id: int,
        tenant_id: int,
        event_type: str,
        payload: dict[str, Any],
        next_retry_at: datetime.datetime | None = None,
    ) -> int:
        row = self._s.execute(
            text(
                "INSERT INTO webhooks.delivery_log "
                "(subscription_id, tenant_id, event_type, payload, status, next_retry_at) "
                "VALUES (:sub, :tid, :evt, :pay::jsonb, 'pending', :retry) "
                "RETURNING id"
            ),
            {
                "sub": subscription_id,
                "tid": tenant_id,
                "evt": event_type,
                "pay": __import__("json").dumps(payload),
                "retry": next_retry_at,
            },
        ).scalar_one()
        return int(row)

    def mark_sent(self, delivery_id: int) -> None:
        self._s.execute(
            text(
                "UPDATE webhooks.delivery_log "
                "SET status = 'sent', delivered_at = now(), last_error = NULL "
                "WHERE id = :did"
            ),
            {"did": delivery_id},
        )

    def mark_failed(
        self,
        delivery_id: int,
        error: str,
        attempt_count: int,
        next_retry_at: datetime.datetime | None,
        dead: bool = False,
    ) -> None:
        status = "dead" if dead else "failed"
        self._s.execute(
            text(
                "UPDATE webhooks.delivery_log "
                "SET status = :st, last_error = :err, attempt_count = :ac, "
                "next_retry_at = :retry "
                "WHERE id = :did"
            ),
            {
                "st": status,
                "err": error[:2000],
                "ac": attempt_count,
                "retry": next_retry_at,
                "did": delivery_id,
            },
        )

    def list_deliveries(
        self,
        tenant_id: int,
        subscription_id: int | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        filters = ["tenant_id = :tid"]
        params: dict[str, Any] = {"tid": tenant_id, "lim": limit}
        if subscription_id is not None:
            filters.append("subscription_id = :sub")
            params["sub"] = subscription_id
        if status:
            filters.append("status = :st")
            params["st"] = status
        where = " AND ".join(filters)
        rows = (
            self._s.execute(
                text(
                    f"SELECT id, subscription_id, event_type, payload, status, "
                    f"attempt_count, next_retry_at, last_error, delivered_at, created_at "
                    f"FROM webhooks.delivery_log "
                    f"WHERE {where} ORDER BY created_at DESC LIMIT :lim"
                ),
                params,
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_delivery(self, delivery_id: int, tenant_id: int) -> dict[str, Any] | None:
        row = (
            self._s.execute(
                text(
                    "SELECT id, subscription_id, event_type, payload, status, "
                    "attempt_count, next_retry_at, last_error, delivered_at, created_at "
                    "FROM webhooks.delivery_log "
                    "WHERE id = :did AND tenant_id = :tid"
                ),
                {"did": delivery_id, "tid": tenant_id},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def get_pending_retries(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return deliveries due for retry — used by the scheduler job."""
        rows = (
            self._s.execute(
                text(
                    "SELECT dl.id, dl.subscription_id, dl.tenant_id, dl.event_type, "
                    "dl.payload, dl.attempt_count, s.target_url, s.secret "
                    "FROM webhooks.delivery_log dl "
                    "JOIN webhooks.subscriptions s ON s.id = dl.subscription_id "
                    "WHERE dl.status = 'failed' AND dl.next_retry_at <= now() "
                    "ORDER BY dl.next_retry_at LIMIT :lim"
                ),
                {"lim": limit},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def reset_for_replay(self, delivery_id: int, tenant_id: int) -> bool:
        result = self._s.execute(
            text(
                "UPDATE webhooks.delivery_log "
                "SET status = 'failed', next_retry_at = now(), attempt_count = 0 "
                "WHERE id = :did AND tenant_id = :tid AND status IN ('failed', 'dead')"
            ),
            {"did": delivery_id, "tid": tenant_id},
        )
        return result.rowcount > 0  # type: ignore[attr-defined]

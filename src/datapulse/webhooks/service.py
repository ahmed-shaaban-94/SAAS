"""Outbound webhook service — subscription CRUD, fire_event, retry."""

from __future__ import annotations

import threading
from typing import Any

from sqlalchemy.orm import Session

from datapulse.logging import get_logger
from datapulse.webhooks import dispatcher
from datapulse.webhooks.repository import WebhookRepository

log = get_logger(__name__)


class WebhookService:
    def __init__(self, repo: WebhookRepository) -> None:
        self._repo = repo

    # ── Subscriptions ─────────────────────────────────────────────────────────

    def create_subscription(
        self,
        tenant_id: int,
        event_type: str,
        target_url: str,
        secret: str,
    ) -> dict[str, Any]:
        return self._repo.create_subscription(tenant_id, event_type, target_url, secret)

    def list_subscriptions(self, tenant_id: int) -> list[dict[str, Any]]:
        return self._repo.list_subscriptions(tenant_id)

    def delete_subscription(self, subscription_id: int, tenant_id: int) -> bool:
        return self._repo.delete_subscription(subscription_id, tenant_id)

    # ── Delivery log ──────────────────────────────────────────────────────────

    def list_deliveries(
        self,
        tenant_id: int,
        subscription_id: int | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._repo.list_deliveries(tenant_id, subscription_id, status, limit)

    def replay_delivery(self, delivery_id: int, tenant_id: int) -> bool:
        return self._repo.reset_for_replay(delivery_id, tenant_id)

    # ── Fire event ────────────────────────────────────────────────────────────

    def fire_event(self, event_type: str, tenant_id: int, payload: dict[str, Any]) -> None:
        """Enqueue delivery for all active subscribers and attempt dispatch in background.

        This method is safe to call from within a request handler or service —
        it commits the delivery records immediately so they survive a crash,
        then dispatches in a daemon thread (non-blocking).
        """
        subscribers = self._repo.get_active_subscribers(tenant_id, event_type)
        if not subscribers:
            return

        delivery_ids: list[tuple[int, str, str]] = []
        for sub in subscribers:
            did = self._repo.create_delivery(
                subscription_id=sub["id"],
                tenant_id=tenant_id,
                event_type=event_type,
                payload=payload,
            )
            delivery_ids.append((did, sub["target_url"], sub["secret"]))

        for did, url, secret in delivery_ids:
            threading.Thread(
                target=self._attempt_delivery,
                args=(did, url, secret, event_type, payload, 0),
                daemon=True,
            ).start()

    def _attempt_delivery(
        self,
        delivery_id: int,
        target_url: str,
        secret: str,
        event_type: str,
        payload: dict[str, Any],
        attempt_count: int,
    ) -> None:
        """Execute one delivery attempt and update the log (runs in background thread)."""
        from datapulse.core.db_session import open_tenant_session

        # Open a fresh session — we're in a background thread, not a request context.
        # tenant_id is not needed for RLS here because we're accessing via delivery_id PK,
        # but we pass a system-level session (tenant_id=0 bypasses RLS for internal workers).
        session = open_tenant_session("0")
        repo = WebhookRepository(session)
        try:
            dispatcher.dispatch(target_url, secret, event_type, payload)
            repo.mark_sent(delivery_id)
            session.commit()
        except Exception as exc:
            new_count = attempt_count + 1
            retry_at = dispatcher.next_retry_at(new_count)
            dead = retry_at is None
            repo.mark_failed(
                delivery_id=delivery_id,
                error=str(exc),
                attempt_count=new_count,
                next_retry_at=retry_at,
                dead=dead,
            )
            session.commit()
            log.warning(
                "webhook_delivery_failed",
                delivery_id=delivery_id,
                attempt=new_count,
                dead=dead,
                error=str(exc),
            )
        finally:
            session.close()

    # ── Retry (called by scheduler) ───────────────────────────────────────────

    def retry_pending(self) -> int:
        """Attempt delivery for all overdue failed records. Returns count attempted."""
        rows = self._repo.get_pending_retries()
        for row in rows:
            threading.Thread(
                target=self._attempt_delivery,
                args=(
                    row["id"],
                    row["target_url"],
                    row["secret"],
                    row["event_type"],
                    row["payload"],
                    row["attempt_count"],
                ),
                daemon=True,
            ).start()
        return len(rows)


def fire_event(
    event_type: str,
    tenant_id: int,
    payload: dict[str, Any],
    session: Session,
) -> None:
    """Module-level convenience to fire a webhook event from any service.

    Creates a WebhookService from the provided session and fires the event.
    The session must already have RLS set (i.e. be the tenant's session).
    """
    svc = WebhookService(WebhookRepository(session))
    svc.fire_event(event_type, tenant_id, payload)

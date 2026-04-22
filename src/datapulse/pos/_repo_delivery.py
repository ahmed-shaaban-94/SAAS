"""Delivery dispatch + rider routing — repository mixin (issue #628).

Covers pos.riders and pos.deliveries tables added in migration 105.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from datapulse.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

log = get_logger(__name__)


class DeliveryRepoMixin:
    """Mixin for :class:`PosRepository` — requires ``self._session``."""

    _session: Session

    # ─── Riders ──────────────────────────────────────────────────────────────

    def list_available_riders(self, *, tenant_id: int) -> list[dict[str, Any]]:
        """Return all riders with status='available' for the given tenant."""
        rows = self._session.execute(
            text("""
                SELECT id, tenant_id, name, phone, status,
                       current_terminal_id, created_at, updated_at
                  FROM pos.riders
                 WHERE tenant_id = :tenant_id
                   AND status    = 'available'
                 ORDER BY name
            """),
            {"tenant_id": tenant_id},
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_rider(self, *, rider_id: int, tenant_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            text("""
                SELECT id, tenant_id, name, phone, status,
                       current_terminal_id, created_at, updated_at
                  FROM pos.riders
                 WHERE id = :rider_id AND tenant_id = :tenant_id
            """),
            {"rider_id": rider_id, "tenant_id": tenant_id},
        ).mappings().one_or_none()
        return dict(row) if row else None

    # ─── Deliveries ───────────────────────────────────────────────────────────

    def create_delivery(
        self,
        *,
        tenant_id: int,
        transaction_id: int,
        address: str,
        landmark: str | None,
        channel: str,
        assigned_rider_id: int | None,
        delivery_fee: object,
        eta_minutes: int | None,
        notes: str | None,
    ) -> dict[str, Any]:
        """Insert a new delivery record and return it with rider data."""
        row = self._session.execute(
            text("""
                INSERT INTO pos.deliveries
                    (tenant_id, transaction_id, address, landmark, channel,
                     assigned_rider_id, delivery_fee, eta_minutes, notes)
                VALUES
                    (:tenant_id, :transaction_id, :address, :landmark, :channel,
                     :assigned_rider_id, :delivery_fee, :eta_minutes, :notes)
                RETURNING
                    id, tenant_id, transaction_id, address, landmark, channel,
                    assigned_rider_id, delivery_fee, eta_minutes, status,
                    notes, created_at, updated_at
            """),
            {
                "tenant_id": tenant_id,
                "transaction_id": transaction_id,
                "address": address,
                "landmark": landmark,
                "channel": channel,
                "assigned_rider_id": assigned_rider_id,
                "delivery_fee": delivery_fee,
                "eta_minutes": eta_minutes,
                "notes": notes,
            },
        ).mappings().one()

        if assigned_rider_id is not None:
            self._session.execute(
                text("""
                    UPDATE pos.riders
                       SET status     = 'busy',
                           updated_at = now()
                     WHERE id = :rider_id AND tenant_id = :tenant_id
                """),
                {"rider_id": assigned_rider_id, "tenant_id": tenant_id},
            )

        return dict(row)

    def get_delivery_by_transaction(
        self, *, transaction_id: int, tenant_id: int
    ) -> dict[str, Any] | None:
        row = self._session.execute(
            text("""
                SELECT d.id, d.tenant_id, d.transaction_id, d.address,
                       d.landmark, d.channel, d.assigned_rider_id,
                       d.delivery_fee, d.eta_minutes, d.status,
                       d.notes, d.created_at, d.updated_at,
                       r.name  AS rider_name,
                       r.phone AS rider_phone,
                       r.status AS rider_status,
                       r.current_terminal_id AS rider_terminal_id,
                       r.created_at AS rider_created_at,
                       r.updated_at AS rider_updated_at
                  FROM pos.deliveries  d
             LEFT JOIN pos.riders      r ON r.id = d.assigned_rider_id
                 WHERE d.transaction_id = :transaction_id
                   AND d.tenant_id      = :tenant_id
            """),
            {"transaction_id": transaction_id, "tenant_id": tenant_id},
        ).mappings().one_or_none()
        return dict(row) if row else None

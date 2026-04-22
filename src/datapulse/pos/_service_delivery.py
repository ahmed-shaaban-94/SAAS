"""Delivery dispatch + rider routing — service mixin (issue #628).

ETA v1: static offset of 20 minutes when the caller does not supply eta_minutes.
A future migration can replace this with a geospatial routing engine.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from datapulse.logging import get_logger
from datapulse.pos.exceptions import RiderNotFoundError, RiderUnavailableError
from datapulse.pos.models.delivery import (
    AvailableRidersResponse,
    CreateDeliveryRequest,
    DeliveryResponse,
    RiderResponse,
    RiderStatus,
)

if TYPE_CHECKING:
    from datapulse.pos.repository import PosRepository

log = get_logger(__name__)

_DEFAULT_ETA_MINUTES = 20


def _build_rider(row: dict) -> RiderResponse:
    return RiderResponse(
        id=row["id"],
        tenant_id=row["tenant_id"],
        name=row["name"],
        phone=row["phone"],
        status=RiderStatus(row["status"]),
        current_terminal_id=row.get("current_terminal_id"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _build_delivery(row: dict) -> DeliveryResponse:
    rider: RiderResponse | None = None
    if row.get("rider_name"):
        rider = RiderResponse(
            id=row["assigned_rider_id"],
            tenant_id=row["tenant_id"],
            name=row["rider_name"],
            phone=row["rider_phone"],
            status=RiderStatus(row["rider_status"]),
            current_terminal_id=row.get("rider_terminal_id"),
            created_at=row["rider_created_at"],
            updated_at=row["rider_updated_at"],
        )
    return DeliveryResponse(
        id=row["id"],
        tenant_id=row["tenant_id"],
        transaction_id=row["transaction_id"],
        address=row["address"],
        landmark=row.get("landmark"),
        channel=row["channel"],
        assigned_rider_id=row.get("assigned_rider_id"),
        rider=rider,
        delivery_fee=row["delivery_fee"],
        eta_minutes=row.get("eta_minutes"),
        status=row["status"],
        notes=row.get("notes"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class DeliveryMixin:
    """Mixin providing delivery dispatch + rider routing.

    Requires ``self._repo`` to be set by :meth:`PosService.__init__`.
    """

    _repo: PosRepository

    def list_available_riders(self, *, tenant_id: int) -> AvailableRidersResponse:
        """Return all riders currently available for dispatch."""
        rows = self._repo.list_available_riders(tenant_id=tenant_id)
        riders = [_build_rider(r) for r in rows]
        return AvailableRidersResponse(riders=riders, total=len(riders))

    def create_delivery(
        self,
        *,
        tenant_id: int,
        body: CreateDeliveryRequest,
    ) -> DeliveryResponse:
        """Create a delivery order for a completed transaction.

        Validates rider availability when assigned_rider_id is provided.
        Marks the rider as busy on dispatch.
        Falls back to ``_DEFAULT_ETA_MINUTES`` when eta_minutes is not supplied.
        """
        if body.assigned_rider_id is not None:
            rider_row = self._repo.get_rider(rider_id=body.assigned_rider_id, tenant_id=tenant_id)
            if rider_row is None:
                raise RiderNotFoundError(body.assigned_rider_id)
            if rider_row["status"] != RiderStatus.available:
                raise RiderUnavailableError(body.assigned_rider_id, rider_row["status"])

        eta = body.eta_minutes if body.eta_minutes is not None else _DEFAULT_ETA_MINUTES
        fee = body.delivery_fee if body.delivery_fee is not None else Decimal("0")

        self._repo.create_delivery(
            tenant_id=tenant_id,
            transaction_id=body.transaction_id,
            address=body.address,
            landmark=body.landmark,
            channel=body.channel,
            assigned_rider_id=body.assigned_rider_id,
            delivery_fee=fee,
            eta_minutes=eta,
            notes=body.notes,
        )

        full_row = self._repo.get_delivery_by_transaction(
            transaction_id=body.transaction_id, tenant_id=tenant_id
        )
        if full_row is None:
            raise ValueError(f"Delivery not found for transaction {body.transaction_id}")
        return _build_delivery(full_row)

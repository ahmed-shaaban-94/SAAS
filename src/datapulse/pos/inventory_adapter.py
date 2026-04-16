"""Adapter wiring the real InventoryService + ExpiryService to the POS protocol.

Until Plan A (the inventory module) was merged, POS used
``MockInventoryService``. This adapter wraps the real services and
adapts their sync, filter-based API to the async, simple-param API
that ``InventoryServiceProtocol`` defines.

Usage in ``api/deps.py``::

    def get_pos_inventory(
        session: SessionDep,
    ) -> InventoryServiceProtocol:
        inv_repo = InventoryRepository(session)
        exp_repo = ExpiryRepository(session)
        inv_svc  = InventoryService(inv_repo)
        exp_svc  = ExpiryService(exp_repo)
        return InventoryAdapter(inv_svc, exp_svc)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from datapulse.expiry.models import ExpiryFilter
from datapulse.expiry.service import ExpiryService
from datapulse.inventory.models import AdjustmentRequest, InventoryFilter
from datapulse.inventory.service import InventoryService
from datapulse.pos.inventory_contract import (
    BatchInfo,
    ReorderAlert,
    StockLevel,
    StockMovement,
)


class InventoryAdapter:
    """Bridges real Inventory/Expiry services to the POS async protocol.

    All methods are ``async`` to satisfy the protocol even though the
    underlying services are synchronous. This avoids blocking the event
    loop in production; for truly heavy queries consider wrapping with
    ``asyncio.to_thread`` in the future.
    """

    def __init__(
        self,
        inventory_service: InventoryService,
        expiry_service: ExpiryService,
    ) -> None:
        self._inv = inventory_service
        self._exp = expiry_service

    async def get_stock_level(self, drug_code: str, site_code: str) -> StockLevel:
        """Map real stock levels to POS StockLevel stub."""
        filters = InventoryFilter(drug_code=drug_code, limit=1)
        levels = self._inv.get_stock_level_detail(drug_code, filters)

        if not levels:
            return StockLevel(
                drug_code=drug_code,
                site_code=site_code,
                quantity_on_hand=Decimal("0"),
                quantity_reserved=Decimal("0"),
                quantity_available=Decimal("0"),
                reorder_point=Decimal("0"),
            )

        # Find the matching site; fall back to the first result
        match = next(
            (sl for sl in levels if sl.site_code == site_code),
            levels[0],
        )
        qty = Decimal(str(match.current_quantity))

        # Reorder point from alerts (optional — default to 0)
        reorder_point = Decimal("0")
        alerts = self._inv.get_reorder_alerts(InventoryFilter(drug_code=drug_code, limit=1))
        matching_alert = next(
            (a for a in alerts if a.site_code == site_code),
            None,
        )
        if matching_alert is not None:
            reorder_point = Decimal(str(matching_alert.reorder_point))

        return StockLevel(
            drug_code=drug_code,
            site_code=site_code,
            quantity_on_hand=qty,
            quantity_reserved=Decimal("0"),
            quantity_available=qty,
            reorder_point=reorder_point,
        )

    async def check_batch_expiry(
        self,
        drug_code: str,
        site_code: str,
    ) -> list[BatchInfo]:
        """Return batches sorted by FEFO from the real expiry service."""
        filters = ExpiryFilter(drug_code=drug_code, site_code=site_code, limit=50)
        batches = self._exp.get_batches(filters)

        results: list[BatchInfo] = []
        for b in batches:
            # Only include active batches with positive quantity
            if b.computed_status in ("quarantined", "written_off"):
                continue
            qty = Decimal(str(b.current_quantity))
            if qty <= 0:
                continue
            results.append(
                BatchInfo(
                    batch_number=b.batch_number,
                    expiry_date=b.expiry_date,
                    quantity_available=qty,
                )
            )

        # Sort FEFO: earliest expiry first
        far_future = date.max
        results.sort(key=lambda b: b.expiry_date or far_future)
        return results

    async def record_movement(self, movement: StockMovement) -> None:
        """Record a POS stock movement as a bronze adjustment.

        POS movements (sale, return, void) are translated into
        stock adjustments that the dbt pipeline picks up on the next run.
        """
        adj_type = {
            "sale": "correction",
            "return": "correction",
            "void": "correction",
        }.get(movement.movement_type, "correction")

        self._inv.create_adjustment(
            tenant_id=0,  # Tenant set via RLS session variable
            request=AdjustmentRequest(
                drug_code=movement.drug_code,
                site_code=movement.site_code,
                adjustment_type=adj_type,
                quantity=movement.quantity_delta,
                batch_number=movement.batch_number,
                reason=f"POS {movement.movement_type}: ref={movement.reference_id}",
            ),
        )

    async def get_reorder_alerts(self, site_code: str) -> list[ReorderAlert]:
        """Return drugs at or below reorder point for a site."""
        filters = InventoryFilter(limit=100)
        alerts = self._inv.get_reorder_alerts(filters)

        return [
            ReorderAlert(
                drug_code=a.drug_code,
                site_code=a.site_code,
                quantity_available=Decimal(str(a.current_quantity)),
                reorder_point=Decimal(str(a.reorder_point)),
            )
            for a in alerts
            if a.site_code == site_code
        ]

"""Inventory service — business logic layer with Redis caching."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from datapulse.cache import cache_get, cache_set, current_tenant_id, get_cache_version
from datapulse.inventory.models import (
    AdjustmentRequest,
    InventoryCount,
    InventoryFilter,
    ReorderAlert,
    StockLevel,
    StockMovement,
    StockReconciliation,
    StockValuation,
)
from datapulse.inventory.repository import InventoryRepository
from datapulse.logging import get_logger

log = get_logger(__name__)

_CACHE_PREFIX = "datapulse:inventory"
_TTL = 300  # 5 minutes


def _cache_key(method: str, params: dict[str, Any] | None = None) -> str:
    """Build a deterministic, versioned, tenant-scoped cache key."""
    tid = current_tenant_id.get("")
    tenant_segment = f"t{tid}" if tid else "t0"
    version = get_cache_version()
    prefix = f"dp:{version}:{tenant_segment}:inv"
    if params:
        raw = json.dumps(params, sort_keys=True, default=str)
        h = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]  # noqa: S324
        return f"{prefix}:{method}:{h}"
    return f"{prefix}:{method}"


class InventoryService:
    """Inventory business logic with Redis-backed caching.

    All read methods check the cache first; writes invalidate nothing
    (TTL-based expiry ensures fresh data after the next pipeline run).
    """

    def __init__(
        self,
        repo: InventoryRepository,
    ) -> None:
        self._repo = repo

    # ── Stock Levels ──────────────────────────────────────────────────────

    def get_stock_levels(self, filters: InventoryFilter) -> list[StockLevel]:
        key = _cache_key("stock_levels", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_stock_levels(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    def get_stock_level_detail(self, drug_code: str, filters: InventoryFilter) -> list[StockLevel]:
        key = _cache_key("stock_level_detail", {"drug_code": drug_code, **filters.model_dump()})
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_stock_level_by_drug(drug_code, filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Movements ─────────────────────────────────────────────────────────

    def get_movements(self, filters: InventoryFilter) -> list[StockMovement]:
        key = _cache_key("movements", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_movements(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    def get_movements_by_drug(
        self, drug_code: str, filters: InventoryFilter
    ) -> list[StockMovement]:
        key = _cache_key("movements_by_drug", {"drug_code": drug_code, **filters.model_dump()})
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_movements_by_drug(drug_code, filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Valuation ─────────────────────────────────────────────────────────

    def get_valuation(self, filters: InventoryFilter) -> list[StockValuation]:
        key = _cache_key("valuation", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_valuation(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    def get_valuation_by_drug(
        self, drug_code: str, filters: InventoryFilter
    ) -> list[StockValuation]:
        key = _cache_key("valuation_by_drug", {"drug_code": drug_code, **filters.model_dump()})
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_valuation_by_drug(drug_code, filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Reorder Alerts ────────────────────────────────────────────────────

    def get_reorder_alerts(self, filters: InventoryFilter) -> list[ReorderAlert]:
        key = _cache_key("reorder_alerts", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_reorder_alerts(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Physical Counts ───────────────────────────────────────────────────

    def get_counts(self, filters: InventoryFilter) -> list[InventoryCount]:
        key = _cache_key("counts", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_counts(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Reconciliation ────────────────────────────────────────────────────

    def get_reconciliation(self, filters: InventoryFilter) -> list[StockReconciliation]:
        key = _cache_key("reconciliation", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_reconciliation(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Adjustments (write) ───────────────────────────────────────────────

    def create_adjustment(self, tenant_id: int, request: AdjustmentRequest) -> None:
        """Create a manual stock adjustment.

        Inserts directly into bronze.stock_adjustments; dbt staging picks it
        up on the next pipeline run. Logs a warning if the resulting stock
        may drop below the reorder point (non-blocking — no exception raised).
        """
        self._repo.create_adjustment(tenant_id, request)

        # Post-write: check if stock may now be below reorder point
        if request.quantity < 0 or request.adjustment_type in ("damage", "shrinkage", "write_off"):
            alerts = self._repo.get_reorder_alerts(
                InventoryFilter(drug_code=request.drug_code, limit=10)
            )
            below = [a for a in alerts if a.site_code == request.site_code]
            if below:
                log.warning(
                    "reorder_alert_triggered",
                    drug_code=request.drug_code,
                    site_code=request.site_code,
                    current_quantity=float(below[0].current_quantity),
                    reorder_point=float(below[0].reorder_point),
                )

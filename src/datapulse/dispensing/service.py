"""Dispensing analytics service — business logic with Redis caching."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from datapulse.cache import cache_get, cache_set, current_tenant_id, get_cache_version
from datapulse.dispensing.models import (
    DaysOfStock,
    DispenseRate,
    DispensingFilter,
    StockoutRisk,
    VelocityClassification,
)
from datapulse.dispensing.repository import DispensingRepository
from datapulse.inventory.models import StockReconciliation
from datapulse.logging import get_logger

log = get_logger(__name__)

_CACHE_PREFIX = "datapulse:dispensing"
_TTL = 300  # 5 minutes


def _cache_key(method: str, params: dict[str, Any] | None = None) -> str:
    """Build a deterministic, versioned, tenant-scoped cache key."""
    tid = current_tenant_id.get("")
    tenant_segment = f"t{tid}" if tid else "t0"
    version = get_cache_version()
    prefix = f"dp:{version}:{tenant_segment}:disp"
    if params:
        raw = json.dumps(params, sort_keys=True, default=str)
        h = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]  # noqa: S324
        return f"{prefix}:{method}:{h}"
    return f"{prefix}:{method}"


class DispensingService:
    """Dispensing analytics business logic with Redis-backed caching.

    All read methods check the cache first; TTL-based expiry ensures
    fresh data after the next dbt pipeline run.
    """

    def __init__(self, repo: DispensingRepository) -> None:
        self._repo = repo

    # ── Dispense Rates ────────────────────────────────────────────────────────

    def get_dispense_rates(self, filters: DispensingFilter) -> list[DispenseRate]:
        key = _cache_key("dispense_rates", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_dispense_rates(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Days of Stock ─────────────────────────────────────────────────────────

    def get_days_of_stock(self, filters: DispensingFilter) -> list[DaysOfStock]:
        key = _cache_key("days_of_stock", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_days_of_stock(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Product Velocity ──────────────────────────────────────────────────────

    def get_velocity(self, filters: DispensingFilter) -> list[VelocityClassification]:
        key = _cache_key("velocity", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_velocity(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Stockout Risk ─────────────────────────────────────────────────────────

    def get_stockout_risk(self, filters: DispensingFilter) -> list[StockoutRisk]:
        key = _cache_key("stockout_risk", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_stockout_risk(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Reconciliation ────────────────────────────────────────────────────────

    def get_reconciliation(self, filters: DispensingFilter) -> list[StockReconciliation]:
        key = _cache_key("reconciliation", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_reconciliation(filters)
        cache_set(key, result, ttl=_TTL)
        return result

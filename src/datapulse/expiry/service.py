"""Expiry service — business logic with Redis caching."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from typing import Any

from datapulse.cache import cache_get, cache_set, current_tenant_id, get_cache_version
from datapulse.expiry.fefo import select_batches_fefo
from datapulse.expiry.models import (
    BatchInfo,
    ExpiryAlert,
    ExpiryCalendarDay,
    ExpiryExposureTier,
    ExpiryFilter,
    ExpirySummary,
    FefoRequest,
    FefoResponse,
    QuarantineRequest,
    WriteOffRequest,
)
from datapulse.expiry.repository import ExpiryRepository
from datapulse.logging import get_logger

log = get_logger(__name__)

_CACHE_PREFIX = "datapulse:expiry"
_TTL = 300  # 5 minutes


def _cache_key(method: str, params: dict[str, Any] | None = None) -> str:
    """Build a deterministic, versioned, tenant-scoped cache key."""
    tid = current_tenant_id.get("")
    tenant_segment = f"t{tid}" if tid else "t0"
    version = get_cache_version()
    prefix = f"dp:{version}:{tenant_segment}:expiry"
    if params:
        raw = json.dumps(params, sort_keys=True, default=str)
        h = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]  # noqa: S324
        return f"{prefix}:{method}:{h}"
    return f"{prefix}:{method}"


class ExpiryService:
    """Expiry business logic with Redis-backed caching.

    Quarantine and write-off operations invalidate nothing —
    TTL-based expiry ensures fresh data after the next pipeline run.
    """

    def __init__(self, repo: ExpiryRepository) -> None:
        self._repo = repo

    # ── Batch List ─────────────────────────────────────────────────────────

    def get_batches(self, filters: ExpiryFilter) -> list[BatchInfo]:
        key = _cache_key("batches", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_batches(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    def get_batches_by_drug(self, drug_code: str, filters: ExpiryFilter) -> list[BatchInfo]:
        key = _cache_key("batches_by_drug", {"drug_code": drug_code, **filters.model_dump()})
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_batches_by_drug(drug_code, filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Alerts ─────────────────────────────────────────────────────────────

    def get_near_expiry(self, days_threshold: int, filters: ExpiryFilter) -> list[ExpiryAlert]:
        key = _cache_key("near_expiry", {"days": days_threshold, **filters.model_dump()})
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_near_expiry(days_threshold, filters)
        cache_set(key, result, ttl=_TTL)
        return result

    def get_expired(self, filters: ExpiryFilter) -> list[ExpiryAlert]:
        key = _cache_key("expired", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_expired(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Summary ────────────────────────────────────────────────────────────

    def get_expiry_summary(self, filters: ExpiryFilter) -> list[ExpirySummary]:
        key = _cache_key("summary", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_expiry_summary(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Exposure tiers (tenant-aggregate EGP per 30/60/90 bucket) ──────────

    def get_exposure_tiers(self, filters: ExpiryFilter) -> list[ExpiryExposureTier]:
        """Return EGP exposure aggregated to the three design-handoff tiers.

        Always returns exactly three rows (30d / 60d / 90d) so the UI can
        render deterministic summary chips.
        """
        key = _cache_key("exposure_tiers", filters.model_dump())
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_exposure_tiers(filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── Calendar ───────────────────────────────────────────────────────────

    def get_expiry_calendar(
        self, start_date: date, end_date: date, filters: ExpiryFilter
    ) -> list[ExpiryCalendarDay]:
        key = _cache_key(
            "calendar",
            {"start": str(start_date), "end": str(end_date), **filters.model_dump()},
        )
        cached = cache_get(key)
        if cached is not None:
            return cached
        result = self._repo.get_expiry_calendar(start_date, end_date, filters)
        cache_set(key, result, ttl=_TTL)
        return result

    # ── FEFO ────────────────────────────────────────────────────────────────

    def select_fefo(self, request: FefoRequest) -> FefoResponse:
        """Apply the FEFO algorithm to select batches for a dispense request."""
        batches = self._repo.get_active_batches_for_fefo(request.drug_code, request.site_code)
        selected, remaining = select_batches_fefo(batches, Decimal(str(request.required_quantity)))

        return FefoResponse(
            drug_code=request.drug_code,
            site_code=request.site_code,
            required_quantity=request.required_quantity,
            fulfilled=remaining == 0,
            remaining_unfulfilled=remaining,
            selections=[
                {
                    "batch_number": s.batch_number,
                    "expiry_date": s.expiry_date.isoformat(),
                    "available_quantity": float(s.available_quantity),
                    "allocated_quantity": float(s.allocated_quantity),
                }
                for s in selected
            ],
        )

    # ── Write ──────────────────────────────────────────────────────────────

    def quarantine_batch(self, tenant_id: int, request: QuarantineRequest) -> None:
        """Move a batch to quarantine status and create a stock adjustment event."""
        self._repo.quarantine_batch(tenant_id, request)
        log.info(
            "quarantine_applied",
            tenant_id=tenant_id,
            drug_code=request.drug_code,
            batch_number=request.batch_number,
        )

    def write_off_batch(self, tenant_id: int, request: WriteOffRequest) -> None:
        """Write off a batch and record the quantity reduction."""
        self._repo.write_off_batch(tenant_id, request)
        log.info(
            "write_off_applied",
            tenant_id=tenant_id,
            drug_code=request.drug_code,
            batch_number=request.batch_number,
            quantity=float(request.quantity),
        )

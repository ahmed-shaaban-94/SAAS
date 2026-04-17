"""DetailService — per-entity detail pages, feature store, and lifecycle."""

from __future__ import annotations

from datapulse.analytics.detail_repository import DetailRepository
from datapulse.analytics.feature_store_repository import FeatureStoreRepository
from datapulse.analytics.models import (
    CustomerAnalytics,
    LifecycleDistribution,
    ProductLifecycle,
    ProductPerformance,
    RevenueDailyRolling,
    RevenueSiteRolling,
    SeasonalityDaily,
    SeasonalityMonthly,
    SiteDetail,
    StaffPerformance,
)
from datapulse.cache_decorator import cached
from datapulse.logging import get_logger

log = get_logger(__name__)

_CACHE_PREFIX = "datapulse:analytics"


class DetailService:
    """Per-entity detail pages, feature store rolling metrics, and lifecycle data."""

    def __init__(
        self,
        detail_repo: DetailRepository | None = None,
        feature_store_repo: FeatureStoreRepository | None = None,
    ) -> None:
        self._detail_repo = detail_repo
        self._feature_store_repo = feature_store_repo

    # ── Entity detail ────────────────────────────────────────────────────────

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_product_detail(self, product_key: int) -> ProductPerformance | None:
        """Detailed performance for a single product (cached 300s)."""
        log.info("product_detail", product_key=product_key)
        if self._detail_repo is None:
            raise RuntimeError("DetailRepository not configured")
        return self._detail_repo.get_product_detail(product_key)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_customer_detail(self, customer_key: int) -> CustomerAnalytics | None:
        """Detailed analytics for a single customer (cached 300s)."""
        log.info("customer_detail", customer_key=customer_key)
        if self._detail_repo is None:
            raise RuntimeError("DetailRepository not configured")
        return self._detail_repo.get_customer_detail(customer_key)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_staff_detail(self, staff_key: int) -> StaffPerformance | None:
        """Detailed performance for a single staff member (cached 300s)."""
        log.info("staff_detail", staff_key=staff_key)
        if self._detail_repo is None:
            raise RuntimeError("DetailRepository not configured")
        return self._detail_repo.get_staff_detail(staff_key)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_site_detail(self, site_key: int) -> SiteDetail | None:
        """Detailed metrics for a single site."""
        log.info("site_detail", site_key=site_key)
        if self._detail_repo is None:
            raise RuntimeError("DetailRepository not configured")
        return self._detail_repo.get_site_detail(site_key)

    # ── Feature store ────────────────────────────────────────────────────────

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_revenue_daily_rolling(
        self,
        days: int = 90,
        limit: int = 200,
    ) -> list[RevenueDailyRolling]:
        """Daily revenue with rolling MAs and trend ratios (cached 300s)."""
        if self._feature_store_repo is None:
            raise RuntimeError("FeatureStoreRepository not configured")
        rows = self._feature_store_repo.get_revenue_daily_rolling(days=days, limit=limit)
        return [RevenueDailyRolling(**r) for r in rows]

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_revenue_site_rolling(
        self,
        site_key: int | None = None,
        days: int = 30,
        limit: int = 200,
    ) -> list[RevenueSiteRolling]:
        """Per-site rolling with cross-site comparison (cached 300s)."""
        if self._feature_store_repo is None:
            raise RuntimeError("FeatureStoreRepository not configured")
        rows = self._feature_store_repo.get_revenue_site_rolling(
            site_key=site_key,
            days=days,
            limit=limit,
        )
        return [RevenueSiteRolling(**r) for r in rows]

    @cached(ttl=600, prefix=_CACHE_PREFIX)
    def get_seasonality_monthly(self) -> list[SeasonalityMonthly]:
        """Monthly seasonal indices (cached 600s)."""
        if self._feature_store_repo is None:
            raise RuntimeError("FeatureStoreRepository not configured")
        rows = self._feature_store_repo.get_seasonality_monthly()
        return [SeasonalityMonthly(**r) for r in rows]

    @cached(ttl=600, prefix=_CACHE_PREFIX)
    def get_seasonality_daily(self) -> list[SeasonalityDaily]:
        """Day-of-week seasonal indices (cached 600s)."""
        if self._feature_store_repo is None:
            raise RuntimeError("FeatureStoreRepository not configured")
        rows = self._feature_store_repo.get_seasonality_daily()
        return [SeasonalityDaily(**r) for r in rows]

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_product_lifecycle(
        self,
        phase: str | None = None,
        limit: int = 50,
    ) -> list[ProductLifecycle]:
        """Product lifecycle classification (cached 300s)."""
        if self._feature_store_repo is None:
            raise RuntimeError("FeatureStoreRepository not configured")
        rows = self._feature_store_repo.get_product_lifecycle(phase=phase, limit=limit)
        return [ProductLifecycle(**r) for r in rows]

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_lifecycle_distribution(self) -> LifecycleDistribution:
        """Distribution of products across lifecycle phases (cached 300s)."""
        if self._feature_store_repo is None:
            raise RuntimeError("FeatureStoreRepository not configured")
        data = self._feature_store_repo.get_lifecycle_distribution()
        return LifecycleDistribution(**data)

"""KPIService — dashboard KPIs, date range, filter options."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Any

from datapulse.analytics.models import (
    AnalyticsFilter,
    DashboardData,
    DataDateRange,
    DateRange,
    FilterOptions,
    KPISummary,
)
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.cache import (
    cache_get,
    cache_get_many,
    cache_set,
    current_tenant_id,
    get_cache_version,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

_CACHE_PREFIX = "datapulse:analytics"


def _cache_key(method: str, params: dict[str, Any] | None = None) -> str:
    """Build a deterministic, versioned, tenant-scoped cache key."""
    tid = current_tenant_id.get("")
    tenant_segment = f"t{tid}" if tid else "t0"
    version = get_cache_version()
    prefix = f"dp:{version}:{tenant_segment}"
    if params:
        raw = json.dumps(params, sort_keys=True, default=str)
        h = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]
        return f"{prefix}:{method}:{h}"
    return f"{prefix}:{method}"


class KPIService:
    """KPI summary, dashboard data, date range, and filter options."""

    def __init__(self, repo: AnalyticsRepository) -> None:
        self._repo = repo

    def _default_filter(self, filters: AnalyticsFilter | None = None) -> AnalyticsFilter:
        if filters is not None:
            return filters
        _, max_date = self._repo.get_data_date_range()
        end = max_date or date.today()
        return AnalyticsFilter(
            date_range=DateRange(
                start_date=end - timedelta(days=30),
                end_date=end,
            )
        )

    def get_date_range(self) -> DataDateRange:
        """Return the min/max dates of available data (cached 3600s)."""
        key = _cache_key("date_range")
        cached_val = cache_get(key)
        if cached_val is not None:
            log.debug("cache_hit", key=key)
            return DataDateRange(**cached_val)

        min_date, max_date = self._repo.get_data_date_range()
        if min_date is None or max_date is None:
            today = date.today()
            return DataDateRange(min_date=today - timedelta(days=365), max_date=today)
        result = DataDateRange(min_date=min_date, max_date=max_date)
        cache_set(key, result.model_dump(mode="json"), ttl=3600)
        return result

    def get_dashboard_summary(self, target_date: date | None = None) -> KPISummary:
        """KPI cards for dashboard header (cached 600s)."""
        if target_date is None:
            date_range_key = _cache_key("date_range")
            multi = cache_get_many([date_range_key])
            if date_range_key in multi:
                dr = multi[date_range_key]
                target = date.fromisoformat(dr["max_date"])
            else:
                _, max_date = self._repo.get_data_date_range()
                target = max_date or date.today()
                cache_set(
                    date_range_key,
                    {"min_date": str(target), "max_date": str(target)},
                    ttl=3600,
                )
        else:
            target = target_date

        key = _cache_key("summary", {"target_date": str(target)})
        cached_val = cache_get(key)
        if cached_val is not None:
            log.debug("cache_hit", key=key)
            return KPISummary(**cached_val)

        log.info("dashboard_summary", target_date=str(target))
        result = self._repo.get_kpi_summary(target)
        cache_set(key, result.model_dump(mode="json"), ttl=600)
        return result

    def get_filter_options(self) -> FilterOptions:
        """Return available filter values for slicers/dropdowns (cached 3600s)."""
        key = _cache_key("filter_options")
        cached_val = cache_get(key)
        if cached_val is not None:
            log.debug("cache_hit", key=key)
            return FilterOptions(**cached_val)

        log.info("filter_options")
        result = self._repo.get_filter_options()
        cache_set(key, result.model_dump(mode="json"), ttl=3600)
        return result

    def get_dashboard_data(
        self,
        target_date: date | None = None,
        filters: AnalyticsFilter | None = None,
    ) -> DashboardData:
        """Composite dashboard payload — KPI + trends + rankings + filters (cached 600s)."""
        _, max_date = self._repo.get_data_date_range()
        end = max_date or date.today()

        if filters is None:
            filters = AnalyticsFilter(
                date_range=DateRange(
                    start_date=end - timedelta(days=30),
                    end_date=end,
                )
            )
        elif filters.date_range is None:
            filters = AnalyticsFilter(
                date_range=DateRange(
                    start_date=end - timedelta(days=30),
                    end_date=end,
                ),
                site_key=filters.site_key,
                category=filters.category,
                brand=filters.brand,
                staff_key=filters.staff_key,
                limit=filters.limit,
            )

        key = _cache_key("dashboard", filters.model_dump(exclude_none=True))
        cached_val = cache_get(key)
        if cached_val is not None:
            log.debug("cache_hit", key=key)
            return DashboardData(**cached_val)

        log.info("dashboard_data", filters=filters.model_dump())
        kpi = self._repo.get_kpi_summary_range(filters)

        result = DashboardData(
            kpi=kpi,
            daily_trend=self._repo.get_daily_trend(filters),
            monthly_trend=self._repo.get_monthly_trend(filters),
            top_products=self._repo.get_top_products(filters),
            top_customers=self._repo.get_top_customers(filters),
            top_staff=self._repo.get_top_staff(filters),
            filter_options=self.get_filter_options(),
        )
        cache_set(key, result.model_dump(mode="json"), ttl=600)
        return result

"""RankingService — trends, rankings, comparisons, advanced analytics, diagnostics."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Any

from datapulse.analytics.advanced_repository import AdvancedRepository
from datapulse.analytics.comparison_repository import ComparisonRepository
from datapulse.analytics.diagnostics import DiagnosticsRepository
from datapulse.analytics.hierarchy_repository import HierarchyRepository
from datapulse.analytics.models import (
    ABCAnalysis,
    AnalyticsFilter,
    DateRange,
    HeatmapData,
    ProductHierarchy,
    RankingResult,
    ReturnAnalysis,
    ReturnsTrend,
    SegmentSummary,
    TopMovers,
    TrendResult,
    WaterfallAnalysis,
)
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.cache import current_tenant_id, get_cache_version
from datapulse.cache_decorator import cached
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


class RankingService:
    """Revenue trends, rankings, comparisons, hierarchy, and advanced analytics."""

    def __init__(
        self,
        repo: AnalyticsRepository,
        comparison_repo: ComparisonRepository | None = None,
        diagnostics_repo: DiagnosticsRepository | None = None,
        hierarchy_repo: HierarchyRepository | None = None,
        advanced_repo: AdvancedRepository | None = None,
    ) -> None:
        self._repo = repo
        self._comparison_repo = comparison_repo
        self._diagnostics_repo = diagnostics_repo
        self._hierarchy_repo = hierarchy_repo
        self._advanced_repo = advanced_repo

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

    # ── Trend methods ────────────────────────────────────────────────────────

    @cached(ttl=90, prefix=_CACHE_PREFIX)
    def get_revenue_trends(self, filters: AnalyticsFilter | None = None) -> dict[str, TrendResult]:
        """Daily and monthly revenue trends (cached 90s)."""
        f = self._default_filter(filters)
        log.info("revenue_trends", filters=f.model_dump())
        return {
            "daily": self._repo.get_daily_trend(f),
            "monthly": self._repo.get_monthly_trend(f),
        }

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_daily_trend(self, filters: AnalyticsFilter | None = None) -> TrendResult:
        """Daily revenue trend only (cached 300s)."""
        f = self._default_filter(filters)
        log.info("daily_trend", filters=f.model_dump())
        return self._repo.get_daily_trend(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_monthly_trend(self, filters: AnalyticsFilter | None = None) -> TrendResult:
        """Monthly revenue trend only (cached 300s)."""
        f = self._default_filter(filters)
        log.info("monthly_trend", filters=f.model_dump())
        return self._repo.get_monthly_trend(f)

    # ── Ranking methods ──────────────────────────────────────────────────────

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_product_insights(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        """Top products by net revenue (cached 300s)."""
        f = self._default_filter(filters)
        log.info("product_insights", filters=f.model_dump())
        return self._repo.get_top_products(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_customer_insights(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        """Top customers by net revenue (cached 300s)."""
        f = self._default_filter(filters)
        log.info("customer_insights", filters=f.model_dump())
        return self._repo.get_top_customers(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_site_comparison(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        """Site ranking by net revenue (cached 300s)."""
        f = self._default_filter(filters)
        log.info("site_comparison", filters=f.model_dump())
        return self._repo.get_site_performance(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_staff_leaderboard(self, filters: AnalyticsFilter | None = None) -> RankingResult:
        """Staff ranking by net revenue (cached 300s)."""
        f = self._default_filter(filters)
        log.info("staff_leaderboard", filters=f.model_dump())
        return self._repo.get_top_staff(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_origin_breakdown(self, filters: AnalyticsFilter | None = None) -> list[dict]:
        """Revenue breakdown by product origin (cached 300s)."""
        f = self._default_filter(filters)
        return self._repo.get_origin_breakdown(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_return_report(self, filters: AnalyticsFilter | None = None) -> list[ReturnAnalysis]:
        """Top returns by amount (cached 300s)."""
        f = self._default_filter(filters)
        log.info("return_report", filters=f.model_dump())
        return self._repo.get_return_analysis(f)

    # ── Comparison ───────────────────────────────────────────────────────────

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_top_movers(
        self,
        entity_type: str,
        filters: AnalyticsFilter | None = None,
        limit: int = 5,
    ) -> TopMovers:
        """Top gainers and losers vs previous period (cached 300s)."""
        if self._comparison_repo is None:
            raise RuntimeError("ComparisonRepository not configured")

        current_f = self._default_filter(filters)
        log.info("top_movers", entity_type=entity_type, filters=current_f.model_dump())

        if current_f.date_range is not None:
            dr = current_f.date_range
            duration = dr.end_date - dr.start_date
            prev_end = dr.start_date - timedelta(days=1)
            prev_start = prev_end - duration
            previous_f = AnalyticsFilter(
                date_range=DateRange(start_date=prev_start, end_date=prev_end),
                site_key=current_f.site_key,
                category=current_f.category,
                brand=current_f.brand,
                staff_key=current_f.staff_key,
                limit=current_f.limit,
            )
        else:
            _, max_date = self._repo.get_data_date_range()
            end = max_date or date.today()
            current_f = AnalyticsFilter(
                date_range=DateRange(start_date=end - timedelta(days=30), end_date=end)
            )
            previous_f = AnalyticsFilter(
                date_range=DateRange(
                    start_date=end - timedelta(days=61),
                    end_date=end - timedelta(days=31),
                )
            )

        return self._comparison_repo.get_top_movers(entity_type, current_f, previous_f, limit)

    # ── Hierarchy ────────────────────────────────────────────────────────────

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_product_hierarchy(self, filters: AnalyticsFilter | None = None) -> ProductHierarchy:
        """Category > Brand > Product hierarchy view (cached 300s)."""
        if self._hierarchy_repo is None:
            raise RuntimeError("HierarchyRepository not configured")
        f = self._default_filter(filters)
        log.info("product_hierarchy", filters=f.model_dump())
        return self._hierarchy_repo.get_product_hierarchy(f)

    # ── Advanced analytics ───────────────────────────────────────────────────

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_abc_analysis(
        self, entity: str = "product", filters: AnalyticsFilter | None = None
    ) -> ABCAnalysis:
        """ABC/Pareto analysis for products or customers (cached 300s)."""
        if self._advanced_repo is None:
            raise RuntimeError("AdvancedRepository not configured")
        f = self._default_filter(filters)
        return self._advanced_repo.get_abc_analysis(f, entity)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_heatmap(self, year: int) -> HeatmapData:
        """Calendar heatmap — daily revenue for a year (cached 300s)."""
        if self._advanced_repo is None:
            raise RuntimeError("AdvancedRepository not configured")
        return self._advanced_repo.get_heatmap_data(year)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_returns_trend(self, filters: AnalyticsFilter | None = None) -> ReturnsTrend:
        """Monthly returns trend (cached 300s)."""
        if self._advanced_repo is None:
            raise RuntimeError("AdvancedRepository not configured")
        f = self._default_filter(filters)
        return self._advanced_repo.get_returns_trend(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_segment_summary(self) -> list[SegmentSummary]:
        """Customer RFM segment summary (cached 300s)."""
        if self._advanced_repo is None:
            raise RuntimeError("AdvancedRepository not configured")
        return self._advanced_repo.get_segment_summary()

    # ── Why Engine (diagnostics) ─────────────────────────────────────────────

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_why_changed(
        self,
        filters: AnalyticsFilter | None = None,
        limit: int = 15,
    ) -> WaterfallAnalysis:
        """Decompose revenue change into dimension-level drivers (cached 300s)."""
        if self._diagnostics_repo is None:
            raise RuntimeError("DiagnosticsRepository not configured")

        current_f = self._default_filter(filters)
        log.info("why_changed", filters=current_f.model_dump())

        if current_f.date_range is not None:
            dr = current_f.date_range
            duration = dr.end_date - dr.start_date
            prev_end = dr.start_date - timedelta(days=1)
            prev_start = prev_end - duration
            previous_f = AnalyticsFilter(
                date_range=DateRange(start_date=prev_start, end_date=prev_end),
                site_key=current_f.site_key,
                category=current_f.category,
                brand=current_f.brand,
                staff_key=current_f.staff_key,
                limit=current_f.limit,
            )
        else:
            _, max_date = self._repo.get_data_date_range()
            end = max_date or date.today()
            current_f = AnalyticsFilter(
                date_range=DateRange(start_date=end - timedelta(days=30), end_date=end)
            )
            previous_f = AnalyticsFilter(
                date_range=DateRange(
                    start_date=end - timedelta(days=61),
                    end_date=end - timedelta(days=31),
                )
            )

        return self._diagnostics_repo.get_revenue_drivers(current_f, previous_f, limit=limit)

"""BreakdownService — billing and customer-type breakdowns."""

from __future__ import annotations

from datetime import date, timedelta

from datapulse.analytics.breakdown_repository import BreakdownRepository
from datapulse.analytics.models import (
    AnalyticsFilter,
    BillingBreakdown,
    CustomerTypeBreakdown,
    DateRange,
)
from datapulse.analytics.repository import AnalyticsRepository
from datapulse.cache_decorator import cached
from datapulse.logging import get_logger

log = get_logger(__name__)

_CACHE_PREFIX = "datapulse:analytics"


class BreakdownService:
    """Billing method and customer-type breakdown analytics."""

    def __init__(
        self,
        repo: AnalyticsRepository,
        breakdown_repo: BreakdownRepository | None = None,
    ) -> None:
        self._repo = repo
        self._breakdown_repo = breakdown_repo

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

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_billing_breakdown(self, filters: AnalyticsFilter | None = None) -> BillingBreakdown:
        """Billing method distribution (cached 300s)."""
        if self._breakdown_repo is None:
            raise RuntimeError("BreakdownRepository not configured")
        f = self._default_filter(filters)
        log.info("billing_breakdown", filters=f.model_dump())
        return self._breakdown_repo.get_billing_breakdown(f)

    @cached(ttl=300, prefix=_CACHE_PREFIX)
    def get_customer_type_breakdown(
        self, filters: AnalyticsFilter | None = None
    ) -> CustomerTypeBreakdown:
        """Walk-in vs insurance vs other distribution by month (cached 300s)."""
        if self._breakdown_repo is None:
            raise RuntimeError("BreakdownRepository not configured")
        f = self._default_filter(filters)
        log.info("customer_type_breakdown", filters=f.model_dump())
        return self._breakdown_repo.get_customer_type_breakdown(f)

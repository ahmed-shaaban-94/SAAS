"""Extra tests for AnalyticsService — covers methods not in test_analytics_service.py.

Covers: get_date_range, get_dashboard_data, get_filter_options,
get_product_detail, get_customer_detail, get_staff_detail, get_site_detail,
get_billing_breakdown, get_customer_type_breakdown, get_top_movers,
get_product_hierarchy, get_abc_analysis, get_heatmap, get_returns_trend,
get_segment_summary, and detail_repo-not-configured error paths.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from datapulse.analytics.advanced_repository import AdvancedRepository
from datapulse.analytics.models import (
    BillingBreakdown,
    CustomerAnalytics,
    CustomerTypeBreakdown,
    DataDateRange,
    FilterOptions,
    HeatmapData,
    ProductHierarchy,
    ProductPerformance,
    SiteDetail,
    StaffPerformance,
    TopMovers,
)
from datapulse.analytics.service import AnalyticsService


class TestGetDateRange:
    def test_with_data(self, analytics_service, mock_repo):
        mock_repo.get_data_date_range.return_value = (date(2023, 1, 1), date(2025, 12, 31))
        result = analytics_service.get_date_range()
        assert isinstance(result, DataDateRange)
        assert result.min_date == date(2023, 1, 1)
        assert result.max_date == date(2025, 12, 31)

    def test_with_null_dates(self, analytics_service, mock_repo):
        mock_repo.get_data_date_range.return_value = (None, None)
        result = analytics_service.get_date_range()
        assert isinstance(result, DataDateRange)
        assert result.max_date == date.today()


class TestGetFilterOptions:
    def test_returns_options(self, analytics_service, mock_repo):
        expected = FilterOptions(categories=["Cat A"], brands=["Brand B"], sites=[], staff=[])
        mock_repo.get_filter_options.return_value = expected
        result = analytics_service.get_filter_options()
        assert result == expected


class TestDetailMethods:
    def test_product_detail_delegates(self, analytics_service, mock_detail_repo):
        expected = create_autospec(ProductPerformance, instance=True)
        mock_detail_repo.get_product_detail.return_value = expected
        result = analytics_service.get_product_detail(1)
        assert result is expected
        mock_detail_repo.get_product_detail.assert_called_once_with(1)

    def test_customer_detail_delegates(self, analytics_service, mock_detail_repo):
        expected = create_autospec(CustomerAnalytics, instance=True)
        mock_detail_repo.get_customer_detail.return_value = expected
        result = analytics_service.get_customer_detail(1)
        assert result is expected

    def test_staff_detail_delegates(self, analytics_service, mock_detail_repo):
        expected = create_autospec(StaffPerformance, instance=True)
        mock_detail_repo.get_staff_detail.return_value = expected
        result = analytics_service.get_staff_detail(1)
        assert result is expected

    def test_site_detail_delegates(self, analytics_service, mock_detail_repo):
        expected = create_autospec(SiteDetail, instance=True)
        mock_detail_repo.get_site_detail.return_value = expected
        result = analytics_service.get_site_detail(1)
        assert result is expected


class TestDetailRepoNotConfigured:
    def test_product_detail_raises_without_repo(self, mock_repo):
        svc = AnalyticsService(mock_repo)  # no detail_repo
        with pytest.raises(RuntimeError, match="DetailRepository not configured"):
            svc.get_product_detail(1)

    def test_customer_detail_raises_without_repo(self, mock_repo):
        svc = AnalyticsService(mock_repo)
        with pytest.raises(RuntimeError, match="DetailRepository not configured"):
            svc.get_customer_detail(1)

    def test_staff_detail_raises_without_repo(self, mock_repo):
        svc = AnalyticsService(mock_repo)
        with pytest.raises(RuntimeError, match="DetailRepository not configured"):
            svc.get_staff_detail(1)

    def test_site_detail_raises_without_repo(self, mock_repo):
        svc = AnalyticsService(mock_repo)
        with pytest.raises(RuntimeError, match="DetailRepository not configured"):
            svc.get_site_detail(1)


class TestBreakdownMethods:
    def test_billing_breakdown_delegates(self, analytics_service, mock_breakdown_repo):
        expected = BillingBreakdown(items=[], total_transactions=0, total_net_amount=Decimal("0"))
        mock_breakdown_repo.get_billing_breakdown.return_value = expected
        result = analytics_service.get_billing_breakdown()
        assert result is expected

    def test_billing_breakdown_raises_without_repo(self, mock_repo):
        svc = AnalyticsService(mock_repo)
        with pytest.raises(RuntimeError, match="BreakdownRepository not configured"):
            svc.get_billing_breakdown()

    def test_customer_type_breakdown_delegates(self, analytics_service, mock_breakdown_repo):
        expected = CustomerTypeBreakdown(items=[])
        mock_breakdown_repo.get_customer_type_breakdown.return_value = expected
        result = analytics_service.get_customer_type_breakdown()
        assert result is expected

    def test_customer_type_breakdown_raises_without_repo(self, mock_repo):
        svc = AnalyticsService(mock_repo)
        with pytest.raises(RuntimeError, match="BreakdownRepository not configured"):
            svc.get_customer_type_breakdown()


class TestTopMovers:
    def test_delegates_with_date_range(self, analytics_service, mock_comparison_repo):
        from datapulse.analytics.models import AnalyticsFilter, DateRange

        expected = TopMovers(gainers=[], losers=[], entity_type="product")
        mock_comparison_repo.get_top_movers.return_value = expected

        f = AnalyticsFilter(
            date_range=DateRange(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
        )
        result = analytics_service.get_top_movers("product", f, limit=5)
        assert result is expected
        mock_comparison_repo.get_top_movers.assert_called_once()

    def test_delegates_without_date_range(self, analytics_service, mock_comparison_repo):
        expected = TopMovers(gainers=[], losers=[], entity_type="product")
        mock_comparison_repo.get_top_movers.return_value = expected
        result = analytics_service.get_top_movers("product", None, limit=5)
        assert result is expected

    def test_raises_without_repo(self, mock_repo):
        svc = AnalyticsService(mock_repo)
        with pytest.raises(RuntimeError, match="ComparisonRepository not configured"):
            svc.get_top_movers("product")


class TestHierarchyMethods:
    def test_product_hierarchy_delegates(self, analytics_service, mock_hierarchy_repo):
        expected = ProductHierarchy(categories=[])
        mock_hierarchy_repo.get_product_hierarchy.return_value = expected
        result = analytics_service.get_product_hierarchy()
        assert result is expected

    def test_product_hierarchy_raises_without_repo(self, mock_repo):
        svc = AnalyticsService(mock_repo)
        with pytest.raises(RuntimeError, match="HierarchyRepository not configured"):
            svc.get_product_hierarchy()


class TestAdvancedMethods:
    def test_abc_analysis_raises_without_repo(self, mock_repo):
        svc = AnalyticsService(mock_repo)
        with pytest.raises(RuntimeError, match="AdvancedRepository not configured"):
            svc.get_abc_analysis()

    def test_heatmap_raises_without_repo(self, mock_repo):
        svc = AnalyticsService(mock_repo)
        with pytest.raises(RuntimeError, match="AdvancedRepository not configured"):
            svc.get_heatmap(2025)

    def test_returns_trend_raises_without_repo(self, mock_repo):
        svc = AnalyticsService(mock_repo)
        with pytest.raises(RuntimeError, match="AdvancedRepository not configured"):
            svc.get_returns_trend()

    def test_segment_summary_raises_without_repo(self, mock_repo):
        svc = AnalyticsService(mock_repo)
        with pytest.raises(RuntimeError, match="AdvancedRepository not configured"):
            svc.get_segment_summary()

    def test_abc_analysis_delegates(
        self,
        mock_repo,
        mock_detail_repo,
        mock_breakdown_repo,
        mock_comparison_repo,
        mock_hierarchy_repo,
    ):
        adv_repo = create_autospec(AdvancedRepository, instance=True)
        from datapulse.analytics.models import ABCAnalysis

        expected = ABCAnalysis(
            items=[],
            total=Decimal("0"),
            class_a_count=0,
            class_b_count=0,
            class_c_count=0,
            class_a_pct=Decimal("0"),
            class_b_pct=Decimal("0"),
            class_c_pct=Decimal("0"),
        )
        adv_repo.get_abc_analysis.return_value = expected
        svc = AnalyticsService(
            mock_repo,
            mock_detail_repo,
            mock_breakdown_repo,
            mock_comparison_repo,
            mock_hierarchy_repo,
            adv_repo,
        )
        result = svc.get_abc_analysis("product")
        assert result is expected

    def test_heatmap_delegates(
        self,
        mock_repo,
        mock_detail_repo,
        mock_breakdown_repo,
        mock_comparison_repo,
        mock_hierarchy_repo,
    ):
        adv_repo = create_autospec(AdvancedRepository, instance=True)
        expected = HeatmapData(cells=[], year=2025, min_value=Decimal("0"), max_value=Decimal("0"))
        adv_repo.get_heatmap_data.return_value = expected
        svc = AnalyticsService(
            mock_repo,
            mock_detail_repo,
            mock_breakdown_repo,
            mock_comparison_repo,
            mock_hierarchy_repo,
            adv_repo,
        )
        result = svc.get_heatmap(2025)
        assert result is expected

    def test_segment_summary_delegates(
        self,
        mock_repo,
        mock_detail_repo,
        mock_breakdown_repo,
        mock_comparison_repo,
        mock_hierarchy_repo,
    ):
        adv_repo = create_autospec(AdvancedRepository, instance=True)
        adv_repo.get_segment_summary.return_value = []
        svc = AnalyticsService(
            mock_repo,
            mock_detail_repo,
            mock_breakdown_repo,
            mock_comparison_repo,
            mock_hierarchy_repo,
            adv_repo,
        )
        result = svc.get_segment_summary()
        assert result == []

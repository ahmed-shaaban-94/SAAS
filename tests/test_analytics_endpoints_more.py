"""Additional analytics endpoint tests to cover remaining uncovered routes."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi.testclient import TestClient

from datapulse.analytics.models import (
    ABCAnalysis,
    BillingBreakdown,
    CustomerTypeBreakdown,
    HeatmapData,
    ProductHierarchy,
    ReturnsTrend,
    TopMovers,
)
from datapulse.analytics.service import AnalyticsService
from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_analytics_service

MOCK_USER = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "preferred_username": "test",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}


@pytest.fixture()
def mock_service() -> MagicMock:
    return create_autospec(AnalyticsService, instance=True)


@pytest.fixture()
def client(mock_service: MagicMock) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_analytics_service] = lambda: mock_service
    return TestClient(app)


class TestBillingBreakdown:
    def test_billing_breakdown(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_billing_breakdown.return_value = BillingBreakdown(
            items=[], total_transactions=0, total_sales=Decimal("0")
        )
        resp = client.get("/api/v1/analytics/billing-breakdown")
        assert resp.status_code == 200


class TestCustomerTypeBreakdown:
    def test_customer_type_breakdown(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_customer_type_breakdown.return_value = CustomerTypeBreakdown(items=[])
        resp = client.get("/api/v1/analytics/customer-type-breakdown")
        assert resp.status_code == 200


class TestTopMovers:
    def test_top_movers(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_top_movers.return_value = TopMovers(
            gainers=[], losers=[], entity_type="product"
        )
        resp = client.get("/api/v1/analytics/top-movers")
        assert resp.status_code == 200


class TestProductHierarchy:
    def test_product_hierarchy(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_product_hierarchy.return_value = ProductHierarchy(categories=[])
        resp = client.get("/api/v1/analytics/products/by-category")
        assert resp.status_code == 200


class TestABCAnalysis:
    def test_abc_analysis(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_abc_analysis.return_value = ABCAnalysis(
            items=[],
            total=Decimal("0"),
            class_a_count=0,
            class_b_count=0,
            class_c_count=0,
            class_a_pct=Decimal("0"),
            class_b_pct=Decimal("0"),
            class_c_pct=Decimal("0"),
        )
        resp = client.get("/api/v1/analytics/abc-analysis")
        assert resp.status_code == 200


class TestHeatmap:
    def test_heatmap(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_heatmap.return_value = HeatmapData(
            cells=[], min_value=Decimal("0"), max_value=Decimal("0")
        )
        resp = client.get("/api/v1/analytics/heatmap")
        assert resp.status_code == 200


class TestReturnsTrend:
    def test_returns_trend(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_returns_trend.return_value = ReturnsTrend(
            points=[],
            total_returns=0,
            total_return_amount=Decimal("0"),
            avg_return_rate=Decimal("0"),
        )
        resp = client.get("/api/v1/analytics/returns/trend")
        assert resp.status_code == 200


class TestSegmentSummary:
    def test_segment_summary(self, client: TestClient, mock_service: MagicMock):
        mock_service.get_segment_summary.return_value = []
        resp = client.get("/api/v1/analytics/segments/summary")
        assert resp.status_code == 200


class TestFilterBuildingEdgeCases:
    def test_with_filter_params(self, client: TestClient, mock_service: MagicMock):
        """Test _to_filter with actual filter parameters (covers lines 103, 113)."""
        mock_service.get_billing_breakdown.return_value = BillingBreakdown(
            items=[], total_transactions=0, total_sales=Decimal("0")
        )
        resp = client.get(
            "/api/v1/analytics/billing-breakdown",
            params={"start_date": "2025-01-01", "end_date": "2025-06-30", "site_key": "1"},
        )
        assert resp.status_code == 200
        mock_service.get_billing_breakdown.assert_called_once()

"""Tests for the top 10 most-connected analytics API endpoints.

T2.7 — Testing Fortress tier: covers /summary, /trends/daily, /trends/monthly,
/products/top, /customers/top, /staff/top, /sites, /returns,
/customer-health, and /customers/churn.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi.testclient import TestClient

from datapulse.analytics.models import (
    CustomerHealthScore,
    KPISummary,
    RankingItem,
    RankingResult,
    ReturnAnalysis,
    TimeSeriesPoint,
    TrendResult,
)
from datapulse.analytics.service import AnalyticsService
from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_analytics_service, get_tenant_session

MOCK_USER = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "preferred_username": "test",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def mock_service() -> MagicMock:
    return create_autospec(AnalyticsService, instance=True)


@pytest.fixture()
def client(mock_service: MagicMock) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_analytics_service] = lambda: mock_service
    return TestClient(app)


# ------------------------------------------------------------------
# Helper builders
# ------------------------------------------------------------------


def _kpi() -> KPISummary:
    return KPISummary(
        today_gross=Decimal("500"),
        mtd_gross=Decimal("3000"),
        ytd_gross=Decimal("30000"),
        daily_transactions=20,
        daily_customers=10,
    )


def _trend() -> TrendResult:
    return TrendResult(
        points=[TimeSeriesPoint(period="2025-01", value=Decimal("100"))],
        total=Decimal("100"),
        average=Decimal("100"),
        minimum=Decimal("100"),
        maximum=Decimal("100"),
    )


def _ranking() -> RankingResult:
    return RankingResult(
        items=[
            RankingItem(
                rank=1,
                key=1,
                name="A",
                value=Decimal("500"),
                pct_of_total=Decimal("100"),
            )
        ],
        total=Decimal("500"),
    )


# ------------------------------------------------------------------
# 1. /summary
# ------------------------------------------------------------------


class TestSummary:
    def test_summary_default_date(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_dashboard_summary.return_value = _kpi()
        resp = client.get("/api/v1/analytics/summary")
        assert resp.status_code == 200
        mock_service.get_dashboard_summary.assert_called_once_with(None)

    def test_summary_with_date(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_dashboard_summary.return_value = _kpi()
        resp = client.get("/api/v1/analytics/summary", params={"target_date": "2025-06-01"})
        assert resp.status_code == 200


# ------------------------------------------------------------------
# 2. /trends/daily
# ------------------------------------------------------------------


class TestDailyTrend:
    def test_daily_trend(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_daily_trend.return_value = _trend()
        resp = client.get("/api/v1/analytics/trends/daily")
        assert resp.status_code == 200
        mock_service.get_daily_trend.assert_called_once()

    def test_daily_trend_response_structure(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.get_daily_trend.return_value = _trend()
        resp = client.get("/api/v1/analytics/trends/daily")
        data = resp.json()
        assert "points" in data
        assert "total" in data


# ------------------------------------------------------------------
# 3. /trends/monthly
# ------------------------------------------------------------------


class TestMonthlyTrend:
    def test_monthly_trend(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_monthly_trend.return_value = _trend()
        resp = client.get("/api/v1/analytics/trends/monthly")
        assert resp.status_code == 200
        mock_service.get_monthly_trend.assert_called_once()


# ------------------------------------------------------------------
# 4. /products/top
# ------------------------------------------------------------------


class TestTopProducts:
    def test_top_products(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_product_insights.return_value = _ranking()
        resp = client.get("/api/v1/analytics/products/top")
        assert resp.status_code == 200
        mock_service.get_product_insights.assert_called_once()

    def test_top_products_response_structure(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.get_product_insights.return_value = _ranking()
        resp = client.get("/api/v1/analytics/products/top")
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "A"


# ------------------------------------------------------------------
# 5. /customers/top
# ------------------------------------------------------------------


class TestTopCustomers:
    def test_top_customers(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_customer_insights.return_value = _ranking()
        resp = client.get("/api/v1/analytics/customers/top")
        assert resp.status_code == 200
        mock_service.get_customer_insights.assert_called_once()


# ------------------------------------------------------------------
# 6. /staff/top
# ------------------------------------------------------------------


class TestTopStaff:
    def test_top_staff(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_staff_leaderboard.return_value = _ranking()
        resp = client.get("/api/v1/analytics/staff/top")
        assert resp.status_code == 200
        mock_service.get_staff_leaderboard.assert_called_once()


# ------------------------------------------------------------------
# 7. /sites
# ------------------------------------------------------------------


class TestSites:
    def test_sites(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_site_comparison.return_value = _ranking()
        resp = client.get("/api/v1/analytics/sites")
        assert resp.status_code == 200
        mock_service.get_site_comparison.assert_called_once()


# ------------------------------------------------------------------
# 8. /returns
# ------------------------------------------------------------------


class TestReturns:
    def test_returns_list(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_return_report.return_value = [
            ReturnAnalysis(
                drug_name="Panadol",
                customer_name="Acme Pharmacy",
                return_quantity=Decimal("5"),
                return_amount=Decimal("250"),
                return_count=2,
            )
        ]
        resp = client.get("/api/v1/analytics/returns")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["drug_name"] == "Panadol"

    def test_returns_empty(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_return_report.return_value = []
        resp = client.get("/api/v1/analytics/returns")
        assert resp.status_code == 200
        assert resp.json() == []


# ------------------------------------------------------------------
# 9. /customer-health
# ------------------------------------------------------------------


class TestCustomerHealth:
    def test_customer_health_empty(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_customer_health.return_value = []
        resp = client.get("/api/v1/analytics/customer-health")
        assert resp.status_code == 200
        assert resp.json() == []
        mock_service.get_customer_health.assert_called_once_with(band=None, limit=50)

    def test_customer_health_with_data(self, client: TestClient, mock_service: MagicMock) -> None:
        mock_service.get_customer_health.return_value = [
            CustomerHealthScore(
                customer_key=1,
                customer_name="Top Buyer",
                health_score=Decimal("85"),
                health_band="Thriving",
                recency_days=3,
                frequency_3m=12,
                monetary_3m=Decimal("5000"),
                return_rate=Decimal("0.02"),
                product_diversity=8,
                trend="improving",
            )
        ]
        resp = client.get("/api/v1/analytics/customer-health")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["customer_name"] == "Top Buyer"
        assert data[0]["health_band"] == "Thriving"

    def test_customer_health_with_band_filter(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.get_customer_health.return_value = []
        resp = client.get(
            "/api/v1/analytics/customer-health",
            params={"band": "At Risk", "limit": 10},
        )
        assert resp.status_code == 200
        mock_service.get_customer_health.assert_called_once_with(band="At Risk", limit=10)


# ------------------------------------------------------------------
# 10. /customers/churn
# ------------------------------------------------------------------


class TestChurnPredictions:
    """Tests for /customers/churn — uses ChurnRepository directly via get_tenant_session."""

    def test_churn_predictions_empty(self) -> None:
        mock_session = MagicMock()
        mock_session.execute.return_value.mappings.return_value.all.return_value = []

        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        app.dependency_overrides[get_tenant_session] = lambda: mock_session
        client = TestClient(app)

        resp = client.get("/api/v1/analytics/customers/churn")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_churn_predictions_with_data(self) -> None:
        churn_row = {
            "customer_key": 42,
            "customer_name": "Risky Corp",
            "health_score": Decimal("25"),
            "health_band": "Critical",
            "recency_days": 90,
            "frequency_3m": 0,
            "monetary_3m": Decimal("0"),
            "trend": "declining",
            "rfm_segment": "Lost",
            "churn_probability": Decimal("0.92"),
            "risk_level": "high",
        }
        mock_session = MagicMock()
        mock_session.execute.return_value.mappings.return_value.all.return_value = [churn_row]

        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        app.dependency_overrides[get_tenant_session] = lambda: mock_session
        client = TestClient(app)

        resp = client.get("/api/v1/analytics/customers/churn")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["customer_name"] == "Risky Corp"
        assert data[0]["risk_level"] == "high"

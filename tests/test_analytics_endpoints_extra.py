"""Extra tests for analytics API endpoints — covers uncovered paths."""

from __future__ import annotations

from decimal import Decimal

from datapulse.analytics.models import (
    CustomerAnalytics,
    FilterOptions,
    KPISummary,
    ProductPerformance,
    RankingItem,
    RankingResult,
    SiteDetail,
    StaffPerformance,
    TimeSeriesPoint,
    TrendResult,
)


def _kpi():
    return KPISummary(
        today_net=Decimal("500"),
        mtd_net=Decimal("3000"),
        ytd_net=Decimal("30000"),
        daily_transactions=20,
        daily_customers=10,
    )


def _trend():
    return TrendResult(
        points=[TimeSeriesPoint(period="2025-01", value=Decimal("100"))],
        total=Decimal("100"),
        average=Decimal("100"),
        minimum=Decimal("100"),
        maximum=Decimal("100"),
    )


def _ranking():
    return RankingResult(
        items=[
            RankingItem(rank=1, key=1, name="A", value=Decimal("500"), pct_of_total=Decimal("100"))
        ],
        total=Decimal("500"),
    )


class TestDashboardEndpoint:
    def test_get_dashboard(self, api_client):
        client, mock_repo, _ = api_client
        mock_repo.get_kpi_summary.return_value = _kpi()
        mock_repo.get_daily_trend.return_value = _trend()
        mock_repo.get_monthly_trend.return_value = _trend()
        mock_repo.get_top_products.return_value = _ranking()
        mock_repo.get_top_customers.return_value = _ranking()
        mock_repo.get_top_staff.return_value = _ranking()
        mock_repo.get_filter_options.return_value = FilterOptions(
            categories=[], brands=[], sites=[], staff=[]
        )
        resp = client.get("/api/v1/analytics/dashboard")
        assert resp.status_code == 200


class TestDateRangeEndpoint:
    def test_get_date_range(self, api_client):
        client, mock_repo, _ = api_client
        resp = client.get("/api/v1/analytics/date-range")
        assert resp.status_code == 200


class TestFilterOptionsEndpoint:
    def test_get_filter_options(self, api_client):
        client, mock_repo, _ = api_client
        mock_repo.get_filter_options.return_value = FilterOptions(
            categories=["Cat A"], brands=["Brand B"], sites=[], staff=[]
        )
        resp = client.get("/api/v1/analytics/filters/options")
        assert resp.status_code == 200


class TestDateRangeFilterValidation:
    def test_partial_date_range_returns_422(self, api_client):
        """Providing only start_date without end_date should 422."""
        client, mock_repo, _ = api_client
        mock_repo.get_daily_trend.return_value = _trend()
        resp = client.get("/api/v1/analytics/trends/daily?start_date=2025-01-01")
        assert resp.status_code == 422


class TestDetailEndpoints:
    def test_product_detail_found(self, api_client):
        client, _, mock_detail_repo = api_client
        mock_detail_repo.get_product_detail.return_value = ProductPerformance(
            product_key=1,
            drug_code="D001",
            drug_name="Aspirin",
            drug_brand="Bayer",
            drug_category="Pain",
            total_quantity=Decimal("500"),
            total_sales=Decimal("10000"),
            total_net_amount=Decimal("9000"),
            return_rate=Decimal("0.05"),
            unique_customers=42,
        )
        resp = client.get("/api/v1/analytics/products/1")
        assert resp.status_code == 200

    def test_product_detail_not_found(self, api_client):
        client, _, mock_detail_repo = api_client
        mock_detail_repo.get_product_detail.return_value = None
        resp = client.get("/api/v1/analytics/products/999")
        assert resp.status_code == 404

    def test_customer_detail_found(self, api_client):
        client, _, mock_detail_repo = api_client
        mock_detail_repo.get_customer_detail.return_value = CustomerAnalytics(
            customer_key=1,
            customer_id="C001",
            customer_name="Customer A",
            total_quantity=Decimal("300"),
            total_net_amount=Decimal("15000"),
            transaction_count=120,
            unique_products=25,
            return_count=3,
        )
        resp = client.get("/api/v1/analytics/customers/1")
        assert resp.status_code == 200

    def test_customer_detail_not_found(self, api_client):
        client, _, mock_detail_repo = api_client
        mock_detail_repo.get_customer_detail.return_value = None
        resp = client.get("/api/v1/analytics/customers/999")
        assert resp.status_code == 404

    def test_staff_detail_found(self, api_client):
        client, _, mock_detail_repo = api_client
        mock_detail_repo.get_staff_detail.return_value = StaffPerformance(
            staff_key=1,
            staff_id="S001",
            staff_name="Staff A",
            staff_position="Pharmacist",
            total_net_amount=Decimal("50000"),
            transaction_count=500,
            avg_transaction_value=Decimal("100"),
            unique_customers=200,
        )
        resp = client.get("/api/v1/analytics/staff/1")
        assert resp.status_code == 200

    def test_staff_detail_not_found(self, api_client):
        client, _, mock_detail_repo = api_client
        mock_detail_repo.get_staff_detail.return_value = None
        resp = client.get("/api/v1/analytics/staff/999")
        assert resp.status_code == 404

    def test_site_detail_found(self, api_client):
        client, _, mock_detail_repo = api_client
        mock_detail_repo.get_site_detail.return_value = SiteDetail(
            site_key=1,
            site_code="SITE01",
            site_name="Main",
            area_manager="Mgr A",
            total_net_amount=Decimal("100000"),
            transaction_count=1000,
            unique_customers=500,
            unique_staff=50,
            walk_in_ratio=Decimal("0.6"),
            insurance_ratio=Decimal("0.3"),
            return_rate=Decimal("0.02"),
        )
        resp = client.get("/api/v1/analytics/sites/1")
        assert resp.status_code == 200

    def test_site_detail_not_found(self, api_client):
        client, _, mock_detail_repo = api_client
        mock_detail_repo.get_site_detail.return_value = None
        resp = client.get("/api/v1/analytics/sites/999")
        assert resp.status_code == 404

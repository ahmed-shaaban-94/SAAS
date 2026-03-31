"""Tests for FastAPI analytics endpoints."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from datapulse.analytics.models import (
    CustomerAnalytics,
    KPISummary,
    ProductPerformance,
    RankingItem,
    RankingResult,
    ReturnAnalysis,
    TimeSeriesPoint,
    TrendResult,
)


def _make_trend_result() -> TrendResult:
    """Helper to build a minimal TrendResult for mocking."""
    return TrendResult(
        points=[TimeSeriesPoint(period="2025-01-01", value=Decimal("100"))],
        total=Decimal("100"),
        average=Decimal("100"),
        minimum=Decimal("100"),
        maximum=Decimal("100"),
    )


def _make_ranking_result() -> RankingResult:
    """Helper to build a minimal RankingResult for mocking."""
    return RankingResult(
        items=[
            RankingItem(
                rank=1,
                key=1,
                name="Item A",
                value=Decimal("500"),
                pct_of_total=Decimal("100"),
            ),
        ],
        total=Decimal("500"),
    )


def _make_kpi_summary() -> KPISummary:
    """Helper to build a KPISummary for mocking."""
    return KPISummary(
        today_net=Decimal("1000"),
        mtd_net=Decimal("5000"),
        ytd_net=Decimal("50000"),
        daily_transactions=42,
        daily_customers=15,
    )


def test_health_endpoint(api_client):
    """GET /health returns 200 with status info."""
    client, mock_repo, mock_detail_repo = api_client
    with patch("datapulse.api.routes.health.get_engine") as mock_engine:
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None
        resp = client.get("/health")
    assert resp.status_code == 200
    assert "status" in resp.json()


def test_summary_endpoint(api_client):
    """GET /api/v1/analytics/summary returns 200 with KPI data."""
    client, mock_repo, mock_detail_repo = api_client
    mock_repo.get_kpi_summary.return_value = _make_kpi_summary()

    resp = client.get("/api/v1/analytics/summary")

    assert resp.status_code == 200
    data = resp.json()
    assert "today_net" in data
    assert "mtd_net" in data
    assert "ytd_net" in data


def test_daily_trend_endpoint(api_client):
    """GET /api/v1/analytics/trends/daily returns 200."""
    client, mock_repo, mock_detail_repo = api_client
    trend = _make_trend_result()
    mock_repo.get_daily_trend.return_value = trend
    mock_repo.get_monthly_trend.return_value = trend

    resp = client.get("/api/v1/analytics/trends/daily")

    assert resp.status_code == 200
    data = resp.json()
    assert "points" in data
    assert "total" in data


def test_monthly_trend_endpoint(api_client):
    """GET /api/v1/analytics/trends/monthly returns 200."""
    client, mock_repo, mock_detail_repo = api_client
    trend = _make_trend_result()
    mock_repo.get_daily_trend.return_value = trend
    mock_repo.get_monthly_trend.return_value = trend

    resp = client.get("/api/v1/analytics/trends/monthly")

    assert resp.status_code == 200
    data = resp.json()
    assert "points" in data
    assert "total" in data


def test_top_products_endpoint(api_client):
    """GET /api/v1/analytics/products/top returns 200."""
    client, mock_repo, mock_detail_repo = api_client
    mock_repo.get_top_products.return_value = _make_ranking_result()

    resp = client.get("/api/v1/analytics/products/top")

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


def test_top_customers_endpoint(api_client):
    """GET /api/v1/analytics/customers/top returns 200."""
    client, mock_repo, mock_detail_repo = api_client
    mock_repo.get_top_customers.return_value = _make_ranking_result()

    resp = client.get("/api/v1/analytics/customers/top")

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


def test_top_staff_endpoint(api_client):
    """GET /api/v1/analytics/staff/top returns 200."""
    client, mock_repo, mock_detail_repo = api_client
    mock_repo.get_top_staff.return_value = _make_ranking_result()

    resp = client.get("/api/v1/analytics/staff/top")

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


def test_sites_endpoint(api_client):
    """GET /api/v1/analytics/sites returns 200."""
    client, mock_repo, mock_detail_repo = api_client
    mock_repo.get_site_performance.return_value = _make_ranking_result()

    resp = client.get("/api/v1/analytics/sites")

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


def test_returns_endpoint(api_client):
    """GET /api/v1/analytics/returns returns 200."""
    client, mock_repo, mock_detail_repo = api_client
    mock_repo.get_return_analysis.return_value = [
        ReturnAnalysis(
            drug_name="Drug X",
            customer_name="Customer A",
            return_quantity=Decimal("10"),
            return_amount=Decimal("250"),
            return_count=3,
        ),
    ]

    resp = client.get("/api/v1/analytics/returns")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1


def test_product_detail_found(api_client):
    """GET /api/v1/analytics/products/1 returns product detail."""
    client, mock_repo, mock_detail_repo = api_client
    mock_detail_repo.get_product_detail.return_value = ProductPerformance(
        product_key=1,
        drug_code="D001",
        drug_name="Aspirin",
        drug_brand="BrandA",
        drug_category="Analgesic",
        total_quantity=Decimal("500"),
        total_sales=Decimal("10000"),
        total_net_amount=Decimal("9000"),
        return_rate=Decimal("0.02"),
        unique_customers=50,
    )

    resp = client.get("/api/v1/analytics/products/1")
    assert resp.status_code == 200
    assert resp.json()["drug_name"] == "Aspirin"


def test_product_detail_not_found(api_client):
    """GET /api/v1/analytics/products/999 returns 404."""
    client, mock_repo, mock_detail_repo = api_client
    mock_detail_repo.get_product_detail.return_value = None

    resp = client.get("/api/v1/analytics/products/999")
    assert resp.status_code == 404


def test_customer_detail_found(api_client):
    """GET /api/v1/analytics/customers/1 returns customer detail."""
    client, mock_repo, mock_detail_repo = api_client
    mock_detail_repo.get_customer_detail.return_value = CustomerAnalytics(
        customer_key=1,
        customer_id="C001",
        customer_name="Pharmacy X",
        total_quantity=Decimal("1000"),
        total_net_amount=Decimal("50000"),
        transaction_count=200,
        unique_products=30,
        return_count=5,
    )

    resp = client.get("/api/v1/analytics/customers/1")
    assert resp.status_code == 200
    assert resp.json()["customer_name"] == "Pharmacy X"


def test_customer_detail_not_found(api_client):
    """GET /api/v1/analytics/customers/999 returns 404."""
    client, mock_repo, mock_detail_repo = api_client
    mock_detail_repo.get_customer_detail.return_value = None

    resp = client.get("/api/v1/analytics/customers/999")
    assert resp.status_code == 404


def test_invalid_date_range_one_date(api_client):
    """Passing only start_date without end_date returns 422."""
    client, mock_repo, mock_detail_repo = api_client

    resp = client.get(
        "/api/v1/analytics/trends/daily",
        params={"start_date": "2025-01-01"},
    )

    assert resp.status_code == 422


def test_limit_validation(api_client):
    """Passing limit=0 returns 422 (minimum is 1)."""
    client, mock_repo, mock_detail_repo = api_client

    resp = client.get(
        "/api/v1/analytics/products/top",
        params={"limit": 0},
    )

    assert resp.status_code == 422

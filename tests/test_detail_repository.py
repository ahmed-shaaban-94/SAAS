"""Tests for datapulse.analytics.detail_repository — all methods with mocked session."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.analytics.detail_repository import DetailRepository


@pytest.fixture()
def detail_repo():
    session = MagicMock()
    return DetailRepository(session), session


def _mock_mappings(session, fetchone_val=None):
    """Set up mock chain: session.execute().mappings().fetchone()."""
    mock_exec = MagicMock()
    mock_maps = MagicMock()
    mock_exec.mappings.return_value = mock_maps
    mock_maps.fetchone.return_value = fetchone_val
    session.execute.return_value = mock_exec


class TestMonthlyTrend:
    def test_valid_table_and_key(self, detail_repo):
        repo, session = detail_repo
        session.execute.return_value.fetchall.return_value = [
            ("2025-01", Decimal("5000")),
            ("2025-02", Decimal("6000")),
        ]
        result = repo._get_monthly_trend("public_marts.agg_sales_by_product", "product_key", 1)
        assert len(result) == 2
        assert result[0].period == "2025-01"
        assert result[0].value == Decimal("5000")

    def test_invalid_table_raises(self, detail_repo):
        repo, _ = detail_repo
        with pytest.raises(ValueError, match="Invalid table"):
            repo._get_monthly_trend("evil_table", "product_key", 1)

    def test_invalid_key_col_raises(self, detail_repo):
        repo, _ = detail_repo
        with pytest.raises(ValueError, match="Invalid key column"):
            repo._get_monthly_trend("public_marts.agg_sales_by_product", "evil_col", 1)


class TestGetProductDetail:
    def test_found(self, detail_repo):
        repo, session = detail_repo
        _mock_mappings(
            session,
            fetchone_val={
                "product_key": 1,
                "drug_code": "D001",
                "drug_name": "Aspirin",
                "drug_brand": "Bayer",
                "drug_category": "Pain",
                "total_quantity": Decimal("500"),
                "total_sales": Decimal("10000"),
                "return_rate": Decimal("0.05"),
                "unique_customers": 42,
                "trend_points": None,
            },
        )

        result = repo.get_product_detail(1)
        assert result is not None
        assert result.product_key == 1
        assert result.drug_name == "Aspirin"
        assert result.total_sales == Decimal("10000")
        assert result.total_net_amount == Decimal("10000")

    def test_not_found(self, detail_repo):
        repo, session = detail_repo
        _mock_mappings(session, fetchone_val=None)
        result = repo.get_product_detail(999)
        assert result is None


class TestGetCustomerDetail:
    def test_found(self, detail_repo):
        repo, session = detail_repo
        _mock_mappings(
            session,
            fetchone_val={
                "customer_key": 1,
                "customer_id": "C001",
                "customer_name": "Customer A",
                "total_quantity": Decimal("300"),
                "total_sales": Decimal("15000"),
                "transaction_count": 120,
                "unique_products": 25,
                "return_count": 3,
                "trend_points": None,
            },
        )

        result = repo.get_customer_detail(1)
        assert result is not None
        assert result.customer_key == 1
        assert result.customer_name == "Customer A"

    def test_not_found(self, detail_repo):
        repo, session = detail_repo
        _mock_mappings(session, fetchone_val=None)
        result = repo.get_customer_detail(999)
        assert result is None


class TestGetStaffDetail:
    def test_found(self, detail_repo):
        repo, session = detail_repo
        _mock_mappings(
            session,
            fetchone_val={
                "staff_key": 1,
                "staff_id": "S001",
                "staff_name": "Staff A",
                "position": "Pharmacist",
                "total_sales": Decimal("50000"),
                "transaction_count": 500,
                "avg_transaction_value": Decimal("100"),
                "unique_customers": 200,
                "trend_points": None,
            },
        )

        result = repo.get_staff_detail(1)
        assert result is not None
        assert result.staff_key == 1
        assert result.staff_name == "Staff A"
        assert result.avg_transaction_value == Decimal("100")

    def test_found_null_avg(self, detail_repo):
        repo, session = detail_repo
        _mock_mappings(
            session,
            fetchone_val={
                "staff_key": 1,
                "staff_id": "S001",
                "staff_name": "Staff A",
                "position": "Pharmacist",
                "total_sales": Decimal("50000"),
                "transaction_count": 0,
                "avg_transaction_value": None,
                "unique_customers": 200,
                "trend_points": None,
            },
        )

        result = repo.get_staff_detail(1)
        assert result is not None
        assert result.avg_transaction_value == Decimal("0")

    def test_not_found(self, detail_repo):
        repo, session = detail_repo
        _mock_mappings(session, fetchone_val=None)
        result = repo.get_staff_detail(999)
        assert result is None


class TestGetSiteDetail:
    def test_found(self, detail_repo):
        repo, session = detail_repo
        _mock_mappings(
            session,
            fetchone_val={
                "site_key": 1,
                "site_code": "SITE01",
                "site_name": "Main Branch",
                "area_manager": "Manager A",
                "total_sales": Decimal("100000"),
                "transaction_count": 1000,
                "unique_customers": 500,
                "unique_staff": 50,
                "walk_in_ratio": Decimal("0.6"),
                "insurance_ratio": Decimal("0.3"),
                "return_rate": Decimal("0.02"),
                "trend_points": None,
            },
        )

        result = repo.get_site_detail(1)
        assert result is not None
        assert result.site_key == 1
        assert result.site_name == "Main Branch"
        assert result.walk_in_ratio == Decimal("0.6000")

    def test_found_null_fields(self, detail_repo):
        repo, session = detail_repo
        _mock_mappings(
            session,
            fetchone_val={
                "site_key": 1,
                "site_code": None,
                "site_name": "Main Branch",
                "area_manager": None,
                "total_sales": Decimal("100000"),
                "transaction_count": 1000,
                "unique_customers": 500,
                "unique_staff": 50,
                "walk_in_ratio": Decimal("0.6"),
                "insurance_ratio": Decimal("0.3"),
                "return_rate": Decimal("0.02"),
                "trend_points": None,
            },
        )

        result = repo.get_site_detail(1)
        assert result is not None
        assert result.site_code == ""
        assert result.area_manager == ""

    def test_not_found(self, detail_repo):
        repo, session = detail_repo
        _mock_mappings(session, fetchone_val=None)
        result = repo.get_site_detail(999)
        assert result is None

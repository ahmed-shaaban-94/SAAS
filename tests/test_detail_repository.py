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
        # Main query returns a row
        session.execute.return_value.fetchone.return_value = (
            1,
            "D001",
            "Aspirin",
            "Bayer",
            "Pain",
            Decimal("500"),
            Decimal("10000"),
            Decimal("0.05"),
            42,
        )
        # Trend query (called after main)
        session.execute.return_value.fetchall.return_value = [
            ("2025-01", Decimal("3000")),
        ]

        result = repo.get_product_detail(1)
        assert result is not None
        assert result.product_key == 1
        assert result.drug_name == "Aspirin"
        assert result.total_sales == Decimal("10000")

    def test_not_found(self, detail_repo):
        repo, session = detail_repo
        session.execute.return_value.fetchone.return_value = None
        result = repo.get_product_detail(999)
        assert result is None


class TestGetCustomerDetail:
    def test_found(self, detail_repo):
        repo, session = detail_repo
        session.execute.return_value.fetchone.return_value = (
            1,
            "C001",
            "Customer A",
            Decimal("300"),
            Decimal("15000"),
            120,
            25,
            3,
        )
        session.execute.return_value.fetchall.return_value = []

        result = repo.get_customer_detail(1)
        assert result is not None
        assert result.customer_key == 1
        assert result.customer_name == "Customer A"

    def test_not_found(self, detail_repo):
        repo, session = detail_repo
        session.execute.return_value.fetchone.return_value = None
        result = repo.get_customer_detail(999)
        assert result is None


class TestGetStaffDetail:
    def test_found(self, detail_repo):
        repo, session = detail_repo
        session.execute.return_value.fetchone.return_value = (
            1,
            "S001",
            "Staff A",
            "Pharmacist",
            Decimal("50000"),
            500,
            Decimal("100"),
            200,
        )
        session.execute.return_value.fetchall.return_value = []

        result = repo.get_staff_detail(1)
        assert result is not None
        assert result.staff_key == 1
        assert result.staff_name == "Staff A"
        assert result.avg_transaction_value == Decimal("100")

    def test_found_null_avg(self, detail_repo):
        repo, session = detail_repo
        session.execute.return_value.fetchone.return_value = (
            1,
            "S001",
            "Staff A",
            "Pharmacist",
            Decimal("50000"),
            0,
            None,
            200,  # avg_transaction_value is None when 0 transactions
        )
        session.execute.return_value.fetchall.return_value = []

        result = repo.get_staff_detail(1)
        assert result is not None
        assert result.avg_transaction_value == Decimal("0")

    def test_not_found(self, detail_repo):
        repo, session = detail_repo
        session.execute.return_value.fetchone.return_value = None
        result = repo.get_staff_detail(999)
        assert result is None


class TestGetSiteDetail:
    def test_found(self, detail_repo):
        repo, session = detail_repo
        session.execute.return_value.fetchone.return_value = (
            1,
            "SITE01",
            "Main Branch",
            "Manager A",
            Decimal("100000"),
            1000,
            500,
            50,
            Decimal("0.6"),
            Decimal("0.3"),
            Decimal("0.02"),
        )
        session.execute.return_value.fetchall.return_value = []

        result = repo.get_site_detail(1)
        assert result is not None
        assert result.site_key == 1
        assert result.site_name == "Main Branch"
        assert result.walk_in_ratio == Decimal("0.6000")

    def test_found_null_fields(self, detail_repo):
        repo, session = detail_repo
        session.execute.return_value.fetchone.return_value = (
            1,
            None,
            "Main Branch",
            None,
            Decimal("100000"),
            1000,
            500,
            50,
            Decimal("0.6"),
            Decimal("0.3"),
            Decimal("0.02"),
        )
        session.execute.return_value.fetchall.return_value = []

        result = repo.get_site_detail(1)
        assert result is not None
        assert result.site_code == ""
        assert result.area_manager == ""

    def test_not_found(self, detail_repo):
        repo, session = detail_repo
        session.execute.return_value.fetchone.return_value = None
        result = repo.get_site_detail(999)
        assert result is None

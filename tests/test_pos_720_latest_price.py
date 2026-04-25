"""Unit tests for issue #720 — latest unit price via mv_latest_unit_price.

Verifies that catalog repo methods return prices sourced from the MV
(via LEFT JOIN) and fall back to 0 when no MV row exists.

Pattern follows existing tests in test_pos_repository.py:
  mock_session.execute.return_value.mappings().<mode>() returns rows.
"""

from __future__ import annotations

import re
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.pos.repository import PosRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_session() -> MagicMock:
    """Fully mocked SQLAlchemy Session."""
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> PosRepository:
    return PosRepository(mock_session)


def _configure_execute_all(mock_session: MagicMock, rows: list[dict]) -> None:
    """Wire mock_session.execute so .mappings().all() returns *rows*."""
    mapping_mock = MagicMock()
    mapping_mock.all.return_value = rows
    chain = MagicMock()
    chain.mappings.return_value = mapping_mock
    mock_session.execute.return_value = chain


def _configure_execute_first(mock_session: MagicMock, row: dict | None) -> None:
    """Wire mock_session.execute so .mappings().first() returns *row*."""
    mapping_mock = MagicMock()
    mapping_mock.first.return_value = row
    chain = MagicMock()
    chain.mappings.return_value = mapping_mock
    mock_session.execute.return_value = chain


# ---------------------------------------------------------------------------
# search_dim_products — price from MV
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchDimProductsPrice:
    def test_search_returns_price_from_mv(
        self, repo: PosRepository, mock_session: MagicMock
    ) -> None:
        """When MV provides a price, search result must carry that price."""
        _configure_execute_all(
            mock_session,
            [
                {
                    "drug_code": "DRUG001",
                    "drug_name": "Paracetamol 500mg",
                    "drug_brand": "BrandA",
                    "drug_cluster": None,
                    "drug_category": "OTC",
                    "unit_price": Decimal("12.5000"),
                }
            ],
        )

        results = repo.search_dim_products("paracetamol")

        assert len(results) == 1
        assert results[0]["unit_price"] == Decimal("12.5000")
        mock_session.execute.assert_called_once()

    def test_search_returns_zero_when_mv_empty(
        self, repo: PosRepository, mock_session: MagicMock
    ) -> None:
        """When MV has no matching row COALESCE must produce 0 (mocked as 0)."""
        _configure_execute_all(
            mock_session,
            [
                {
                    "drug_code": "DRUG002",
                    "drug_name": "Ibuprofen 200mg",
                    "drug_brand": None,
                    "drug_cluster": None,
                    "drug_category": "OTC",
                    "unit_price": Decimal("0"),
                }
            ],
        )

        results = repo.search_dim_products("ibuprofen")

        assert results[0]["unit_price"] == Decimal("0")

    def test_search_sql_contains_mv_join(
        self, repo: PosRepository, mock_session: MagicMock
    ) -> None:
        """SQL issued by search_dim_products must reference the MV and COALESCE."""
        _configure_execute_all(mock_session, [])

        repo.search_dim_products("test")

        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        assert "mv_latest_unit_price" in sql_text
        assert "COALESCE" in sql_text
        assert "current_setting" in sql_text


# ---------------------------------------------------------------------------
# get_product_by_code — price from MV
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetProductByCodePrice:
    def test_returns_price_from_mv(self, repo: PosRepository, mock_session: MagicMock) -> None:
        """get_product_by_code must propagate the MV-sourced price."""
        _configure_execute_first(
            mock_session,
            {
                "drug_code": "DRUG001",
                "drug_name": "Paracetamol 500mg",
                "drug_brand": "BrandA",
                "drug_cluster": None,
                "drug_category": "OTC",
                "unit_price": Decimal("15.7500"),
            },
        )

        result = repo.get_product_by_code("DRUG001")

        assert result is not None
        assert result["unit_price"] == Decimal("15.7500")

    def test_returns_zero_when_mv_empty(self, repo: PosRepository, mock_session: MagicMock) -> None:
        """When MV has no row for the product, price must be 0."""
        _configure_execute_first(
            mock_session,
            {
                "drug_code": "DRUG002",
                "drug_name": "Ibuprofen 200mg",
                "drug_brand": None,
                "drug_cluster": None,
                "drug_category": "OTC",
                "unit_price": Decimal("0"),
            },
        )

        result = repo.get_product_by_code("DRUG002")

        assert result is not None
        assert result["unit_price"] == Decimal("0")

    def test_returns_none_when_not_found(
        self, repo: PosRepository, mock_session: MagicMock
    ) -> None:
        """get_product_by_code must return None when DB returns no row."""
        _configure_execute_first(mock_session, None)

        result = repo.get_product_by_code("DOES_NOT_EXIST")

        assert result is None


# ---------------------------------------------------------------------------
# get_drug_detail — price from MV
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetDrugDetailPrice:
    def test_returns_price_from_mv(self, repo: PosRepository, mock_session: MagicMock) -> None:
        """get_drug_detail must propagate the MV-sourced price."""
        _configure_execute_first(
            mock_session,
            {
                "drug_code": "DRUG001",
                "drug_name": "Paracetamol 500mg",
                "drug_brand": "BrandA",
                "drug_cluster": None,
                "drug_category": "OTC",
                "unit_price": Decimal("20.0000"),
                "counseling_text": "Take with food.",
                "active_ingredient": "Paracetamol",
            },
        )

        result = repo.get_drug_detail("DRUG001")

        assert result is not None
        assert result["unit_price"] == Decimal("20.0000")

    def test_drug_detail_sql_contains_mv_join(
        self, repo: PosRepository, mock_session: MagicMock
    ) -> None:
        """SQL issued by get_drug_detail must reference the MV."""
        _configure_execute_first(mock_session, None)

        repo.get_drug_detail("DRUG001")

        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        assert "mv_latest_unit_price" in sql_text
        assert "COALESCE" in sql_text


# ---------------------------------------------------------------------------
# list_catalog_products — price from MV
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListCatalogProductsPrice:
    def test_returns_price_from_mv(self, repo: PosRepository, mock_session: MagicMock) -> None:
        """list_catalog_products must propagate the MV-sourced price."""
        _configure_execute_all(
            mock_session,
            [
                {
                    "drug_code": "DRUG001",
                    "drug_name": "Paracetamol 500mg",
                    "drug_brand": "BrandA",
                    "drug_cluster": None,
                    "drug_category": "OTC",
                    "unit_price": Decimal("18.2500"),
                }
            ],
        )

        results = repo.list_catalog_products(cursor=None, limit=50)

        assert results[0]["unit_price"] == Decimal("18.2500")

    def test_list_catalog_sql_contains_mv_join(
        self, repo: PosRepository, mock_session: MagicMock
    ) -> None:
        """SQL issued by list_catalog_products must reference the MV."""
        _configure_execute_all(mock_session, [])

        repo.list_catalog_products(cursor=None, limit=10)

        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        assert "mv_latest_unit_price" in sql_text
        assert "COALESCE" in sql_text
        assert "current_setting" in sql_text


# ---------------------------------------------------------------------------
# Migration idempotency check
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_migration_is_idempotent() -> None:
    """Migration 117 must use DO $$ IF NOT EXISTS pattern for idempotency."""
    import pathlib

    migration_path = (
        pathlib.Path(__file__).parent.parent / "migrations" / "118_mv_latest_unit_price.sql"
    )
    assert migration_path.exists(), f"Migration file not found: {migration_path}"

    sql = migration_path.read_text(encoding="utf-8")

    # Must be wrapped in a PL/pgSQL anonymous block (DO $$)
    assert re.search(r"DO\s+\$\$", sql), "Migration must use DO $$ anonymous block"

    # Must check IF NOT EXISTS before creating the MV
    assert "IF NOT EXISTS" in sql, "Migration must guard MV creation with IF NOT EXISTS"

    # Must create the materialized view
    assert "CREATE MATERIALIZED VIEW" in sql, "Migration must create the materialized view"

    # Must create a unique index (required for REFRESH CONCURRENTLY)
    assert "CREATE UNIQUE INDEX" in sql, (
        "Migration must create a unique index for REFRESH CONCURRENTLY"
    )

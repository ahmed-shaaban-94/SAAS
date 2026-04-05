"""Tests for SearchRepository."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datapulse.analytics.search_repository import SearchRepository


@pytest.fixture()
def mock_session():
    return MagicMock()


@pytest.fixture()
def repo(mock_session):
    return SearchRepository(mock_session)


def _make_mapping_rows(rows: list[dict]):
    """Helper to build mock mapping results."""
    mock_result = MagicMock()
    mock_mappings = MagicMock()
    mock_mappings.all.return_value = [MagicMock(**r) for r in rows]
    mock_result.mappings.return_value = mock_mappings
    return mock_result


class TestSearchProducts:
    def test_search_products(self, repo, mock_session):
        """Search returns product results shaped correctly."""
        rows = [
            {"key": "P001", "name": "Widget A", "category": "Electronics", "score": 0.9},
        ]
        mock_session.execute.return_value = _make_mapping_rows(rows)

        results = repo._search_products("Widget", 5)

        assert len(results) == 1
        assert results[0]["key"] == "P001"
        assert results[0]["name"] == "Widget A"
        assert results[0]["subtitle"] == "Electronics"
        assert results[0]["type"] == "product"


class TestSearchCustomers:
    def test_search_customers(self, repo, mock_session):
        """Search returns customer results shaped correctly."""
        rows = [
            {"key": "C001", "name": "Acme Corp", "score": 0.8},
        ]
        mock_session.execute.return_value = _make_mapping_rows(rows)

        results = repo._search_customers("Acme", 5)

        assert len(results) == 1
        assert results[0]["key"] == "C001"
        assert results[0]["name"] == "Acme Corp"
        assert results[0]["subtitle"] == ""
        assert results[0]["type"] == "customer"


class TestSearchStaff:
    def test_search_staff(self, repo, mock_session):
        """Search returns staff results shaped correctly."""
        rows = [
            {"key": "S001", "name": "John Doe", "score": 0.85},
        ]
        mock_session.execute.return_value = _make_mapping_rows(rows)

        results = repo._search_staff("John", 5)

        assert len(results) == 1
        assert results[0]["key"] == "S001"
        assert results[0]["name"] == "John Doe"
        assert results[0]["type"] == "staff"


class TestSearchAll:
    def test_search_empty_query(self, repo, mock_session):
        """Search with various inputs still returns dict structure."""
        mock_session.execute.return_value = _make_mapping_rows([])

        results = repo.search("test", 10)

        assert "products" in results
        assert "customers" in results
        assert "staff" in results
        assert results["products"] == []
        assert results["customers"] == []
        assert results["staff"] == []

    def test_search_limit_per_type(self, repo, mock_session):
        """Limit is divided across types (at least 3 per type)."""
        mock_session.execute.return_value = _make_mapping_rows([])

        repo.search("q", 9)

        # Should be called 3 times (products, customers, staff)
        assert mock_session.execute.call_count == 3

    def test_search_product_null_category(self, repo, mock_session):
        """Product with None category shows empty subtitle."""
        rows = [
            {"key": "P002", "name": "Gadget", "category": None, "score": 0.7},
        ]
        mock_session.execute.return_value = _make_mapping_rows(rows)

        results = repo._search_products("Gadget", 5)

        assert results[0]["subtitle"] == ""

"""Unit tests for PosRepository — catalog pharma.drug_catalog UNION coverage."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.pos.repository import PosRepository

pytestmark = pytest.mark.unit


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> PosRepository:
    return PosRepository(mock_session)


def _make_execute(rows, *, mode: str = "first"):
    mapping_mock = MagicMock()
    if mode == "first":
        mapping_mock.first.return_value = rows
    elif mode == "all":
        mapping_mock.all.return_value = rows
    chain = MagicMock()
    chain.mappings.return_value = mapping_mock
    return chain


class TestCatalogPharmaUnion:
    """Verify the catalog repo UNIONs pharma.drug_catalog for SAP material lookups."""

    def test_search_dim_products_unions_pharma_catalog(
        self, repo: PosRepository, mock_session: MagicMock
    ):
        mock_session.execute.return_value = _make_execute([], mode="all")
        repo.search_dim_products("para", limit=10)
        sql = str(mock_session.execute.call_args[0][0])
        assert "pharma.drug_catalog" in sql
        assert "UNION ALL" in sql
        assert "material_code" in sql
        assert "name_en" in sql
        assert "NOT EXISTS" in sql

    def test_search_dim_products_filters_catalog_with_dim_product_dups(
        self, repo: PosRepository, mock_session: MagicMock
    ):
        mock_session.execute.return_value = _make_execute([], mode="all")
        repo.search_dim_products("x")
        sql = str(mock_session.execute.call_args[0][0])
        assert "p2.drug_code = c.material_code" in sql

    def test_get_product_by_code_falls_back_to_pharma_catalog(
        self, repo: PosRepository, mock_session: MagicMock
    ):
        mock_session.execute.return_value = _make_execute(None, mode="first")
        repo.get_product_by_code("500001")
        sql = str(mock_session.execute.call_args[0][0])
        assert "pharma.drug_catalog" in sql
        assert "UNION ALL" in sql
        assert "c.material_code = :drug_code" in sql

    def test_get_product_by_code_returns_dict_when_catalog_hits(
        self, repo: PosRepository, mock_session: MagicMock
    ):
        row = {
            "drug_code": "500001",
            "drug_name": "PARACETAMOL 500MG",
            "drug_brand": "PHARCO",
            "drug_cluster": "OTC",
            "drug_category": "PAIN & FEVER",
            "unit_price": Decimal("3.6"),
        }
        mock_session.execute.return_value = _make_execute(row, mode="first")
        result = repo.get_product_by_code("500001")
        assert result == row

    def test_list_catalog_products_unions_pharma_catalog(
        self, repo: PosRepository, mock_session: MagicMock
    ):
        mock_session.execute.return_value = _make_execute([], mode="all")
        repo.list_catalog_products(cursor=None, limit=200)
        sql = str(mock_session.execute.call_args[0][0])
        assert "pharma.drug_catalog" in sql
        assert "UNION ALL" in sql
        assert "combined" in sql
        assert "drug_code > :cursor" in sql

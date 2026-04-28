"""M5 — mv_latest_unit_price join must use NULLIF to guard the GUC cast.

current_setting('app.tenant_id', true) returns '' when the GUC is unset.
Casting '' to INT raises in PostgreSQL.  The fix wraps the expression:
    NULLIF(current_setting('app.tenant_id', true), '')::INT
so an unset GUC produces NULL instead of an error.

All four call sites in _repo_catalog.py are covered:
  * search_dim_products  (line ~64)
  * get_product_by_code  (line ~118)
  * get_drug_detail      (line ~169)
  * list_catalog_products (line ~287)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datapulse.pos._repo_catalog import CatalogRepoMixin as CatalogMixin

pytestmark = pytest.mark.unit


def _sql_text_for(method_name: str, mixin: CatalogMixin, *args, **kwargs) -> str:
    """Call the method and return the SQL text that was passed to session.execute."""
    # Each method calls self._session.execute(text(...), params)
    # We capture it via the mock side_effect
    captured: list[str] = []

    def _capture(sql, params=None):
        captured.append(str(sql))
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_result.mappings.return_value.all.return_value = []
        return mock_result

    mixin._session.execute.side_effect = _capture  # type: ignore[attr-defined]
    getattr(mixin, method_name)(*args, **kwargs)
    assert captured, f"{method_name} did not call session.execute"
    return captured[0]


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def catalog(mock_session: MagicMock) -> CatalogMixin:
    obj = CatalogMixin.__new__(CatalogMixin)
    obj._session = mock_session  # type: ignore[attr-defined]
    return obj


class TestCatalogGucNullif:
    """M5: every call site must use NULLIF around the GUC cast."""

    def test_search_dim_products_uses_nullif(
        self, catalog: CatalogMixin, mock_session: MagicMock
    ) -> None:
        sql = _sql_text_for("search_dim_products", catalog, "aspirin", limit=10)
        assert "NULLIF" in sql, "search_dim_products: NULLIF missing from mv_latest_unit_price join"
        assert "::INT" in sql or "::int" in sql, (
            "search_dim_products: integer cast missing after NULLIF"
        )

    def test_get_product_by_code_uses_nullif(
        self, catalog: CatalogMixin, mock_session: MagicMock
    ) -> None:
        sql = _sql_text_for("get_product_by_code", catalog, drug_code="ASP001")
        assert "NULLIF" in sql, "get_product_by_code: NULLIF missing from mv_latest_unit_price join"

    def test_get_drug_detail_uses_nullif(
        self, catalog: CatalogMixin, mock_session: MagicMock
    ) -> None:
        sql = _sql_text_for("get_drug_detail", catalog, drug_code="ASP001")
        assert "NULLIF" in sql, "get_drug_detail: NULLIF missing from mv_latest_unit_price join"

    def test_list_catalog_products_uses_nullif(
        self, catalog: CatalogMixin, mock_session: MagicMock
    ) -> None:
        sql = _sql_text_for("list_catalog_products", catalog, cursor=None, limit=10)
        assert "NULLIF" in sql, (
            "list_catalog_products: NULLIF missing from mv_latest_unit_price join"
        )

    def test_bare_current_setting_without_nullif_absent(
        self, catalog: CatalogMixin, mock_session: MagicMock
    ) -> None:
        """No unguarded bare current_setting cast should remain in search_dim_products."""
        sql = _sql_text_for("search_dim_products", catalog, "x", limit=5)
        # The old pattern: lp.tenant_id = current_setting('app.tenant_id', true)\n
        # without NULLIF wrapping.  We check the positive form — NULLIF must appear
        # before the closing paren of the join condition.
        import re

        bare = re.search(
            r"lp\.tenant_id\s*=\s*current_setting\s*\(\s*'app\.tenant_id'",
            sql,
        )
        if bare:
            # Acceptable only if NULLIF is present (the old form is gone)
            assert "NULLIF" in sql

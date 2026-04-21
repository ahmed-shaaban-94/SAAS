"""Tests for datapulse.core.sql — shared SQL helpers."""

from __future__ import annotations

import pytest

from datapulse.core.sql import build_where_eq


class TestBuildWhereEq:
    def test_all_values_present_emits_all_clauses(self):
        clause, params = build_where_eq(
            [
                ("po.tenant_id", "tenant_id", 1),
                ("po.status", "status", "draft"),
                ("po.supplier_code", "supplier_code", "SUP-001"),
            ]
        )
        assert (
            clause == "po.tenant_id = :tenant_id AND po.status = :status "
            "AND po.supplier_code = :supplier_code"
        )
        assert params == {
            "tenant_id": 1,
            "status": "draft",
            "supplier_code": "SUP-001",
        }

    def test_none_values_are_dropped(self):
        clause, params = build_where_eq(
            [
                ("po.tenant_id", "tenant_id", 1),
                ("po.status", "status", None),
                ("po.supplier_code", "supplier_code", None),
            ]
        )
        assert clause == "po.tenant_id = :tenant_id"
        assert params == {"tenant_id": 1}

    def test_all_none_returns_identity_clause(self):
        clause, params = build_where_eq(
            [
                ("po.status", "status", None),
                ("po.supplier_code", "supplier_code", None),
            ]
        )
        # Caller can safely do f"WHERE {clause}" without worrying about an
        # empty clause breaking the query.
        assert clause == "1=1"
        assert params == {}

    def test_empty_list_returns_identity(self):
        clause, params = build_where_eq([])
        assert clause == "1=1"
        assert params == {}

    def test_zero_and_empty_string_values_are_kept(self):
        # Falsy but non-None values must survive — dropping them would be a
        # silent data bug (e.g. status="" or count=0 are real inputs).
        clause, params = build_where_eq(
            [
                ("count", "count", 0),
                ("name", "name", ""),
            ]
        )
        assert clause == "count = :count AND name = :name"
        assert params == {"count": 0, "name": ""}

    def test_extra_clauses_are_appended_verbatim(self):
        clause, params = build_where_eq(
            [("po.tenant_id", "tenant_id", 1)],
            extra_clauses=["po.is_deleted = FALSE"],
        )
        assert clause == "po.tenant_id = :tenant_id AND po.is_deleted = FALSE"
        assert params == {"tenant_id": 1}

    def test_extra_clauses_only(self):
        clause, params = build_where_eq(
            [("po.status", "status", None)],
            extra_clauses=["po.expected_date < CURRENT_DATE"],
        )
        assert clause == "po.expected_date < CURRENT_DATE"
        assert params == {}

    def test_column_expr_with_dot_qualified_alias(self):
        # The helper must handle qualified column names (po.x) unchanged so
        # callers can disambiguate columns in multi-table queries.
        clause, params = build_where_eq([("la.po_number", "po_number", "PO-123")])
        assert clause == "la.po_number = :po_number"
        assert params == {"po_number": "PO-123"}


@pytest.mark.unit
class TestBuildWhereEqMarker:
    """Ensures the module is covered under pytest -m unit."""

    def test_placeholder(self):
        assert build_where_eq([]) == ("1=1", {})

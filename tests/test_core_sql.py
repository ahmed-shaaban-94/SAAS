"""Tests for datapulse.core.sql — shared SQL helpers."""

from __future__ import annotations

import pytest

from datapulse.core.sql import build_set_eq, build_where, build_where_eq


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


class TestBuildWhere:
    def test_mixed_operators(self):
        clause, params = build_where(
            [
                ("m.site_key", "=", "site_key", 1),
                ("m.movement_date", ">=", "start_date", "2026-01-01"),
                ("m.movement_date", "<=", "end_date", "2026-01-31"),
            ]
        )
        assert clause == (
            "m.site_key = :site_key AND m.movement_date >= :start_date "
            "AND m.movement_date <= :end_date"
        )
        assert params == {
            "site_key": 1,
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        }

    def test_none_values_dropped_regardless_of_operator(self):
        clause, params = build_where(
            [
                ("m.site_key", "=", "site_key", None),
                ("m.movement_date", ">=", "start_date", None),
                ("m.movement_date", "<=", "end_date", "2026-01-31"),
            ]
        )
        assert clause == "m.movement_date <= :end_date"
        assert params == {"end_date": "2026-01-31"}

    def test_unknown_operator_raises(self):
        # Defensive: never splice arbitrary operator text into SQL, since
        # a typo like "= ;DROP TABLE" would otherwise land in the query.
        with pytest.raises(ValueError, match="unsupported operator"):
            build_where([("col", "BETWEEN", "v", "foo")])

    def test_like_and_ilike_supported(self):
        # Wildcards (``%``, ``_``) are the caller's responsibility — they go
        # in the bound *value*, never in the operator or column_expr.
        clause, params = build_where(
            [
                ("endpoint", "ILIKE", "endpoint", "%analytics%"),
                ("user_id", "LIKE", "user_id", "svc_%"),
            ]
        )
        assert clause == "endpoint ILIKE :endpoint AND user_id LIKE :user_id"
        assert params == {"endpoint": "%analytics%", "user_id": "svc_%"}

    def test_not_equal_operators_both_forms(self):
        clause_bang, _ = build_where([("c", "!=", "v", 1)])
        clause_chev, _ = build_where([("c", "<>", "v", 1)])
        assert clause_bang == "c != :v"
        assert clause_chev == "c <> :v"

    def test_build_where_eq_is_shortcut(self):
        eq_clause, eq_params = build_where_eq([("c", "v", 5)])
        full_clause, full_params = build_where([("c", "=", "v", 5)])
        assert eq_clause == full_clause
        assert eq_params == full_params


class TestBuildSetEq:
    def test_all_present(self):
        body, params = build_set_eq(
            [
                ("role_id", "rid", 42),
                ("display_name", "name", "Alice"),
                ("is_active", "active", True),
            ]
        )
        assert body == "role_id = :rid, display_name = :name, is_active = :active"
        assert params == {"rid": 42, "name": "Alice", "active": True}

    def test_none_values_dropped(self):
        body, params = build_set_eq(
            [
                ("role_id", "rid", None),
                ("display_name", "name", "Alice"),
                ("is_active", "active", None),
            ]
        )
        assert body == "display_name = :name"
        assert params == {"name": "Alice"}

    def test_all_none_returns_empty(self):
        # Empty body signals "nothing to update" — callers must branch on
        # this, since UPDATE ... SET  WHERE ... is a syntax error.
        body, params = build_set_eq(
            [
                ("role_id", "rid", None),
                ("display_name", "name", None),
            ]
        )
        assert body == ""
        assert params == {}

    def test_false_and_zero_values_kept(self):
        # Same semantics as build_where_eq: falsy but non-None values survive.
        body, params = build_set_eq(
            [
                ("is_active", "active", False),
                ("count", "count", 0),
            ]
        )
        assert body == "is_active = :active, count = :count"
        assert params == {"active": False, "count": 0}

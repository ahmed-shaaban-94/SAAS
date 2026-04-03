"""Tests for the advanced filter DSL."""

from __future__ import annotations

import pytest

from datapulse.api.filters import (
    ALLOWED_FIELDS,
    FilterCondition,
    FilterOp,
    parse_filters,
)


class TestFilterOp:
    def test_all_ops_defined(self):
        assert len(FilterOp) == 10
        assert FilterOp.EQ.value == "eq"
        assert FilterOp.BETWEEN.value == "between"
        assert FilterOp.IS_NULL.value == "is_null"


class TestFilterCondition:
    def test_valid_field(self):
        fc = FilterCondition(field="net_sales", op=FilterOp.GTE, value="10000")
        assert fc.field == "net_sales"

    def test_invalid_field_raises(self):
        with pytest.raises(ValueError, match="not allowed"):
            FilterCondition(field="DROP_TABLE", op=FilterOp.EQ, value="x")

    def test_all_allowed_fields_accepted(self):
        for field in ALLOWED_FIELDS:
            fc = FilterCondition(field=field, op=FilterOp.EQ, value="test")
            assert fc.field == field


class TestParseFilters:
    def test_parses_single_filter(self):
        params = {"filter[net_sales][gte]": "10000"}
        filters = parse_filters(params)
        assert len(filters) == 1
        assert filters[0].field == "net_sales"
        assert filters[0].op == FilterOp.GTE
        assert filters[0].value == "10000"

    def test_parses_multiple_filters(self):
        params = {
            "filter[net_sales][gte]": "10000",
            "filter[category][eq]": "Pharma",
            "filter[date][between]": "2024-01-01,2024-12-31",
        }
        filters = parse_filters(params)
        assert len(filters) == 3

    def test_ignores_non_filter_params(self):
        params = {
            "limit": "10",
            "offset": "0",
            "filter[net_sales][gte]": "5000",
        }
        filters = parse_filters(params)
        assert len(filters) == 1

    def test_invalid_operator_skipped(self):
        params = {"filter[net_sales][invalid_op]": "10000"}
        filters = parse_filters(params)
        assert len(filters) == 0

    def test_invalid_field_skipped(self):
        params = {"filter[DROP_TABLE][eq]": "value"}
        filters = parse_filters(params)
        assert len(filters) == 0

    def test_in_operator(self):
        params = {"filter[category][in]": "Pharma,OTC,Supplement"}
        filters = parse_filters(params)
        assert len(filters) == 1
        assert filters[0].op == FilterOp.IN
        assert filters[0].value == "Pharma,OTC,Supplement"

    def test_like_operator(self):
        params = {"filter[brand][like]": "aspirin"}
        filters = parse_filters(params)
        assert len(filters) == 1
        assert filters[0].op == FilterOp.LIKE

    def test_empty_params(self):
        assert parse_filters({}) == []

    def test_is_null_operator(self):
        params = {"filter[category][is_null]": "true"}
        filters = parse_filters(params)
        assert len(filters) == 1
        assert filters[0].op == FilterOp.IS_NULL


class TestAllowedFields:
    def test_contains_expected_fields(self):
        assert "date" in ALLOWED_FIELDS
        assert "net_sales" in ALLOWED_FIELDS
        assert "category" in ALLOWED_FIELDS
        assert "brand" in ALLOWED_FIELDS
        assert "site_key" in ALLOWED_FIELDS
        assert "status" in ALLOWED_FIELDS

    def test_rejects_dangerous_fields(self):
        for bad_field in ["password", "1=1;--", "admin", "__proto__"]:
            assert bad_field not in ALLOWED_FIELDS

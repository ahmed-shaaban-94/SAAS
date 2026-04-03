"""Tests for multi-field sorting."""

from __future__ import annotations

from datapulse.api.sorting import (
    ALLOWED_SORT_FIELDS,
    SortField,
    parse_sort,
)


class TestParseSortField:
    def test_frozen(self):
        sf = SortField(field="net_sales", direction="desc")
        assert sf.field == "net_sales"
        assert sf.direction == "desc"


class TestParseSort:
    def test_single_field_desc(self):
        fields = parse_sort("net_sales:desc")
        assert len(fields) == 1
        assert fields[0].field == "net_sales"
        assert fields[0].direction == "desc"

    def test_single_field_asc(self):
        fields = parse_sort("name:asc")
        assert len(fields) == 1
        assert fields[0].direction == "asc"

    def test_default_direction_is_asc(self):
        fields = parse_sort("net_sales")
        assert len(fields) == 1
        assert fields[0].direction == "asc"

    def test_multiple_fields(self):
        fields = parse_sort("net_sales:desc,name:asc")
        assert len(fields) == 2
        assert fields[0].field == "net_sales"
        assert fields[0].direction == "desc"
        assert fields[1].field == "name"
        assert fields[1].direction == "asc"

    def test_none_returns_empty(self):
        assert parse_sort(None) == []

    def test_empty_string_returns_empty(self):
        assert parse_sort("") == []

    def test_rejects_unsafe_field(self):
        fields = parse_sort("DROP_TABLE:desc")
        assert len(fields) == 0

    def test_rejects_sql_injection(self):
        fields = parse_sort("net_sales;DROP TABLE sales:desc")
        assert len(fields) == 0

    def test_invalid_direction_defaults_to_asc(self):
        fields = parse_sort("net_sales:invalid")
        assert len(fields) == 1
        assert fields[0].direction == "asc"

    def test_spaces_handled(self):
        fields = parse_sort("  net_sales:desc , name:asc  ")
        assert len(fields) == 2

    def test_allowed_fields_comprehensive(self):
        assert "net_sales" in ALLOWED_SORT_FIELDS
        assert "date" in ALLOWED_SORT_FIELDS
        assert "quantity" in ALLOWED_SORT_FIELDS
        assert "started_at" in ALLOWED_SORT_FIELDS
        assert "status" in ALLOWED_SORT_FIELDS

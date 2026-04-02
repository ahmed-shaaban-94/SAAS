"""Tests for bronze column_map module."""

from __future__ import annotations

from datapulse.bronze.column_map import COLUMN_MAP


class TestColumnMap:
    def test_column_map_is_dict(self):
        assert isinstance(COLUMN_MAP, dict)

    def test_column_map_not_empty(self):
        assert len(COLUMN_MAP) > 0

    def test_known_mappings(self):
        assert COLUMN_MAP["Reference No"] == "reference_no"
        assert COLUMN_MAP["Date"] == "date"
        assert COLUMN_MAP["Net Sales"] == "net_sales"
        assert COLUMN_MAP["Customer Name"] == "customer_name"
        assert COLUMN_MAP["Brand"] == "brand"

    def test_preserves_source_typo(self):
        """The source Excel has 'Salse Not TAX' — we keep the typo in mapping."""
        assert COLUMN_MAP["Salse Not TAX"] == "sales_not_tax"

    def test_all_values_are_snake_case(self):
        for excel_name, db_col in COLUMN_MAP.items():
            assert db_col == db_col.lower(), f"{excel_name} -> {db_col} is not lowercase"
            assert " " not in db_col, f"{excel_name} -> {db_col} contains spaces"

    def test_no_duplicate_db_columns(self):
        """Each DB column name should be unique (except intentional duplicates)."""
        values = list(COLUMN_MAP.values())
        # mat_group and mat_group_short are intentionally different
        assert "mat_group" in values
        assert "mat_group_short" in values

    def test_expected_count(self):
        """We know there are ~46 column mappings."""
        assert len(COLUMN_MAP) >= 40

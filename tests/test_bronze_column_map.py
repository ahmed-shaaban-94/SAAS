"""Tests for datapulse.bronze.column_map — COLUMN_MAP integrity checks."""

from __future__ import annotations

import re

from datapulse.bronze.column_map import COLUMN_MAP
from datapulse.bronze.loader import ALLOWED_COLUMNS

SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class TestColumnMap:
    def test_column_map_non_empty(self):
        """COLUMN_MAP must not be empty."""
        assert len(COLUMN_MAP) > 0

    def test_all_keys_are_strings(self):
        """All keys in COLUMN_MAP are non-empty strings."""
        for key in COLUMN_MAP:
            assert isinstance(key, str), f"Key {key!r} is not a string"
            assert len(key) > 0, "Empty string key found"

    def test_all_values_are_strings(self):
        """All values in COLUMN_MAP are non-empty strings."""
        for val in COLUMN_MAP.values():
            assert isinstance(val, str), f"Value {val!r} is not a string"
            assert len(val) > 0, "Empty string value found"

    def test_all_values_are_snake_case(self):
        """All DB column names are lowercase snake_case (no spaces, no uppercase)."""
        for excel_col, db_col in COLUMN_MAP.items():
            assert SNAKE_CASE_RE.match(db_col), (
                f"Value {db_col!r} (for key {excel_col!r}) is not valid snake_case"
            )

    def test_no_spaces_in_values(self):
        """No DB column name contains spaces."""
        for db_col in COLUMN_MAP.values():
            assert " " not in db_col, f"Space found in DB column name: {db_col!r}"

    def test_allowed_columns_includes_column_map_values(self):
        """ALLOWED_COLUMNS contains all values from COLUMN_MAP."""
        for db_col in COLUMN_MAP.values():
            assert db_col in ALLOWED_COLUMNS, f"{db_col!r} not in ALLOWED_COLUMNS"

    def test_allowed_columns_includes_source_file(self):
        """ALLOWED_COLUMNS includes the 'source_file' lineage column."""
        assert "source_file" in ALLOWED_COLUMNS

    def test_allowed_columns_includes_source_quarter(self):
        """ALLOWED_COLUMNS includes the 'source_quarter' lineage column."""
        assert "source_quarter" in ALLOWED_COLUMNS

    # --- Specific known mappings ---

    def test_date_maps_to_date(self):
        assert COLUMN_MAP["Date"] == "date"

    def test_material_maps_to_material(self):
        assert COLUMN_MAP["Material"] == "material"

    def test_quantity_maps_to_quantity(self):
        assert COLUMN_MAP["Quantity"] == "quantity"

    def test_net_sales_maps_correctly(self):
        assert COLUMN_MAP["Net Sales"] == "net_sales"

    def test_gross_sales_maps_correctly(self):
        assert COLUMN_MAP["Gross Sales"] == "gross_sales"

    def test_customer_name_maps_correctly(self):
        assert COLUMN_MAP["Customer Name"] == "customer_name"

    def test_salse_not_tax_typo_preserved(self):
        """'Salse Not TAX' is intentional typo from source — mapped to 'sales_not_tax'."""
        assert COLUMN_MAP["Salse Not TAX"] == "sales_not_tax"

    def test_billing_type_duplicate_handled(self):
        """Polars auto-renamed duplicate 'Billing Type_1' maps to 'billing_type2'."""
        assert COLUMN_MAP["Billing Type_1"] == "billing_type2"

    def test_billing_type2_explicit_mapping(self):
        assert COLUMN_MAP["Billing Type2"] == "billing_type2"

    def test_site_name_maps_correctly(self):
        assert COLUMN_MAP["Site Name"] == "site_name"

    def test_reference_no_maps_correctly(self):
        assert COLUMN_MAP["Reference No"] == "reference_no"

    def test_person_name_maps_correctly(self):
        assert COLUMN_MAP["Person Name"] == "person_name"

    def test_column_count_reasonable(self):
        """COLUMN_MAP should have a reasonable number of entries (40+)."""
        assert len(COLUMN_MAP) >= 40, f"Expected 40+ entries, got {len(COLUMN_MAP)}"

    def test_allowed_columns_is_frozenset(self):
        """ALLOWED_COLUMNS is a frozenset (immutable)."""
        assert isinstance(ALLOWED_COLUMNS, frozenset)

    def test_no_duplicate_values_except_known(self):
        """Most DB column names should be unique (only known duplicates allowed)."""
        # billing_type2 appears twice (from Billing Type2 and Billing Type_1) — allowed
        values = list(COLUMN_MAP.values())
        from collections import Counter

        counts = Counter(values)
        duplicates = {v: c for v, c in counts.items() if c > 1}
        allowed_duplicates = {"billing_type2", "mat_group"}  # known duplicates
        unexpected = set(duplicates.keys()) - allowed_duplicates
        assert not unexpected, f"Unexpected duplicate DB column names: {unexpected}"

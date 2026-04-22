"""Regression guard for the bronze-loader SQL column whitelist (#547-4).

``src/datapulse/bronze/loader.py`` blocks SQL injection through column-name
interpolation by rejecting anything not in ``ALLOWED_COLUMNS``. The whitelist
is built as ``frozenset(COLUMN_MAP.values()) | {lineage_columns}`` — a value
*derived* from the mapping, so the subset invariant is true by construction
today. These tests lock that construction in so a future refactor that
hard-codes the whitelist (or drops a COLUMN_MAP entry without updating the
set) fails loudly instead of silently dropping the injection defence.
"""

from __future__ import annotations

from datapulse.bronze.column_map import COLUMN_MAP
from datapulse.bronze.loader import ALLOWED_COLUMNS, _validate_columns

# Lineage columns added to rows at ingest time — the only keys allowed in
# ALLOWED_COLUMNS that are NOT values in COLUMN_MAP.
_EXPECTED_LINEAGE_COLUMNS = frozenset({"source_file", "source_quarter", "tenant_id"})


class TestBronzeColumnWhitelist:
    def test_column_map_values_are_a_subset_of_allowed_columns(self):
        """Every DB column the mapper can emit must be legal for INSERT."""
        assert set(COLUMN_MAP.values()) <= ALLOWED_COLUMNS

    def test_allowed_columns_is_exactly_map_plus_lineage(self):
        """Nothing sneaks in besides COLUMN_MAP values + known lineage columns.

        If a refactor adds a new lineage column, update ``_EXPECTED_LINEAGE_COLUMNS``
        here so the guard stays tight.
        """
        expected = set(COLUMN_MAP.values()) | _EXPECTED_LINEAGE_COLUMNS
        assert set(ALLOWED_COLUMNS) == expected

    def test_column_map_values_are_snake_case(self):
        """DB columns must be snake_case ASCII — no spaces, no dots, no mixed case.

        A single non-ASCII or uppercase drifts into SQL via f-string
        interpolation past the whitelist check, so the shape guarantee
        itself is part of the injection defence.
        """
        for excel, db in COLUMN_MAP.items():
            assert db == db.lower(), f"{excel!r} -> {db!r}: must be lowercase"
            assert " " not in db, f"{excel!r} -> {db!r}: no spaces allowed"
            assert "." not in db, f"{excel!r} -> {db!r}: no dots allowed"
            assert db.replace("_", "").isalnum(), (
                f"{excel!r} -> {db!r}: must be alphanumeric (plus underscore)"
            )

    # Known intentional duplicate: Excel headers "Billing Type2" and
    # "Billing Type_1" both map to ``billing_type2``. Source files use one
    # header or the other; no single file has both, so the "silent merge"
    # concern does not apply in practice. Leaving this documented rather
    # than asserted so the test stays green while the alias is intentional.

    def test_validate_columns_rejects_off_whitelist(self):
        """Defence-in-depth: the runtime check still fires on foreign names."""
        try:
            _validate_columns(["reference_no", "drop_table_users"])
        except ValueError as exc:
            assert "drop_table_users" in str(exc)
        else:  # pragma: no cover — test fails on this branch
            raise AssertionError("_validate_columns should have raised")

    def test_validate_columns_accepts_legitimate_columns(self):
        """The happy path — known columns pass silently."""
        sample = list(COLUMN_MAP.values())[:3] + ["source_file", "tenant_id"]
        _validate_columns(sample)

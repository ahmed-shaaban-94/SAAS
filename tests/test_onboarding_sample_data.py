"""Tests for onboarding.sample_data — deterministic pharma demo dataset generator.

Phase 2 Task 2 / #401. Covers:
- Deterministic generation (same seed → same rows)
- Schema coverage (key bronze.sales columns populated with realistic values)
- Idempotency markers (source_file + source_quarter so clear-and-reload works)
- Insertion helper issues DELETE-then-batched-INSERT against the expected table
- Row counts + tenant scoping

RLS/integration-level verification is deferred to the droplet — these are
unit tests that run against a mocked SQLAlchemy Session.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datapulse.onboarding.sample_data import (
    SAMPLE_SOURCE_FILE,
    SAMPLE_SOURCE_QUARTER,
    build_sample_rows,
    clear_sample_rows,
    insert_sample_rows,
    load_sample,
)


@pytest.mark.unit
class TestBuildSampleRows:
    def test_default_row_count(self):
        """Default call generates exactly 5 000 rows."""
        rows = build_sample_rows()
        assert len(rows) == 5000

    def test_custom_row_count(self):
        """Caller can override row_count for tests and small demos."""
        rows = build_sample_rows(row_count=25)
        assert len(rows) == 25

    def test_deterministic_with_seed(self):
        """Same seed → byte-identical rows (critical for idempotency + snapshots)."""
        rows_a = build_sample_rows(row_count=50, seed=42)
        rows_b = build_sample_rows(row_count=50, seed=42)
        assert rows_a == rows_b

    def test_different_seeds_produce_different_data(self):
        """Safety: default seed isn't accidentally fixed inside the function."""
        rows_a = build_sample_rows(row_count=50, seed=42)
        rows_b = build_sample_rows(row_count=50, seed=99)
        assert rows_a != rows_b

    def test_every_row_tagged_with_sample_source_markers(self):
        """Idempotency scope — clear-and-reload must find these markers."""
        rows = build_sample_rows(row_count=100)
        for row in rows:
            assert row["source_file"] == SAMPLE_SOURCE_FILE
            assert row["source_quarter"] == SAMPLE_SOURCE_QUARTER

    def test_every_row_carries_tenant_id(self):
        """tenant_id stamped so RLS on bronze.sales scopes correctly."""
        rows = build_sample_rows(row_count=50, tenant_id=7)
        for row in rows:
            assert row["tenant_id"] == 7

    def test_required_bronze_columns_populated(self):
        """Row count, silver stage, and quality gates all depend on these."""
        required = {
            "reference_no",
            "date",
            "material",
            "material_desc",
            "category",
            "customer",
            "customer_name",
            "site",
            "site_name",
            "quantity",
            "net_sales",
            "gross_sales",
        }
        rows = build_sample_rows(row_count=20)
        for row in rows:
            for col in required:
                assert col in row, f"column {col!r} missing"
                assert row[col] is not None, f"column {col!r} is None"

    def test_financial_values_are_positive(self):
        """Sales pipeline quality gates flag negative financials — sample must be clean."""
        rows = build_sample_rows(row_count=200)
        for row in rows:
            assert row["quantity"] > 0
            assert row["net_sales"] > 0
            assert row["gross_sales"] >= row["net_sales"]

    def test_dates_span_a_reasonable_window(self):
        """Dashboards need variance across dates to show trends."""
        rows = build_sample_rows(row_count=500)
        dates = {row["date"] for row in rows}
        # At least 30 distinct days so the daily trend chart isn't a flatline.
        assert len(dates) >= 30

    def test_multiple_sites_represented(self):
        """Sample must look like a multi-branch chain, not one store."""
        rows = build_sample_rows(row_count=500)
        sites = {row["site"] for row in rows}
        # Plan says 10-branch chain; require ≥ 5 to pass once distribution is non-uniform.
        assert len(sites) >= 5

    def test_multiple_products_represented(self):
        """Ranking views assume ≥ a handful of SKUs."""
        rows = build_sample_rows(row_count=500)
        materials = {row["material"] for row in rows}
        assert len(materials) >= 20

    def test_reference_numbers_are_unique(self):
        """Bronze dedup + quality 'reference_no null rate' check both require uniqueness."""
        rows = build_sample_rows(row_count=500)
        refs = [row["reference_no"] for row in rows]
        assert len(set(refs)) == len(refs)


@pytest.mark.unit
class TestClearSampleRows:
    def test_issues_tenant_scoped_delete_with_sample_markers(self):
        """clear_sample_rows must only touch sample rows for the given tenant."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 12
        session.execute.return_value = mock_result

        deleted = clear_sample_rows(session, tenant_id=3)

        assert deleted == 12
        session.execute.assert_called_once()
        sql_text_obj = session.execute.call_args[0][0]
        sql = str(sql_text_obj)
        params = session.execute.call_args[0][1]
        assert "DELETE FROM bronze.sales" in sql
        assert "tenant_id = :tenant_id" in sql
        assert "source_file = :source_file" in sql
        assert "source_quarter = :source_quarter" in sql
        assert params == {
            "tenant_id": 3,
            "source_file": SAMPLE_SOURCE_FILE,
            "source_quarter": SAMPLE_SOURCE_QUARTER,
        }

    def test_returns_zero_when_nothing_to_delete(self):
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        session.execute.return_value = mock_result

        assert clear_sample_rows(session, tenant_id=1) == 0


@pytest.mark.unit
class TestInsertSampleRows:
    def test_batched_inserts_sum_to_total_rows(self):
        """Insert batches so a single huge INSERT never hits pgbouncer limits."""
        session = MagicMock()
        rows = build_sample_rows(row_count=250)

        inserted = insert_sample_rows(session, rows, tenant_id=1)

        assert inserted == 250
        # Must call execute at least once; each call should carry list-of-dicts params.
        assert session.execute.called

    def test_zero_rows_is_noop(self):
        """Empty list → no SQL issued, returns 0."""
        session = MagicMock()
        inserted = insert_sample_rows(session, [], tenant_id=1)
        assert inserted == 0
        session.execute.assert_not_called()

    def test_rejects_rows_with_mismatched_tenant(self):
        """Defence-in-depth: rows are built with tenant_id already; caller's
        tenant_id must agree, or we refuse to insert to avoid RLS cross-talk."""
        session = MagicMock()
        rows = build_sample_rows(row_count=5, tenant_id=1)
        with pytest.raises(ValueError, match="tenant_id mismatch"):
            insert_sample_rows(session, rows, tenant_id=99)


@pytest.mark.unit
class TestLoadSample:
    def test_orchestrates_clear_then_insert_and_returns_row_count(self):
        """High-level API: idempotent single-call loader."""
        session = MagicMock()

        # clear returns 7, insert returns the row_count generated
        clear_result = MagicMock()
        clear_result.rowcount = 7
        session.execute.return_value = clear_result

        rows_loaded = load_sample(session, tenant_id=1, row_count=30)

        assert rows_loaded == 30
        # First call is DELETE; subsequent are INSERT(s).
        first_sql = str(session.execute.call_args_list[0].args[0])
        assert "DELETE" in first_sql

    def test_default_row_count_is_five_thousand(self):
        """The DoD says 'curated 5 000-row pharma dataset'."""
        session = MagicMock()
        clear_result = MagicMock()
        clear_result.rowcount = 0
        session.execute.return_value = clear_result

        rows_loaded = load_sample(session, tenant_id=1)

        assert rows_loaded == 5000

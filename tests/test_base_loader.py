"""Tests for BronzeLoader ABC and LoadResult dataclass.

Covers:
  - BronzeLoader cannot be instantiated directly (is abstract)
  - LoadResult is frozen (immutable)
  - A concrete subclass can be created and run (using mocked engine)
  - run() returns correct LoadResult with rows_loaded, errors
  - Column whitelisting prevents injection (only allowed columns inserted)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest

from datapulse.bronze.base_loader import BronzeLoader, LoadResult

# ---------------------------------------------------------------------------
# LoadResult — immutability
# ---------------------------------------------------------------------------


class TestLoadResult:
    def test_is_frozen(self):
        result = LoadResult(
            source_type="excel",
            table_name="bronze.stock_receipts",
            rows_loaded=10,
            rows_skipped=0,
            errors=(),
        )
        with pytest.raises((AttributeError, TypeError)):
            result.rows_loaded = 999  # type: ignore[misc]

    def test_errors_is_tuple(self):
        result = LoadResult(
            source_type="excel",
            table_name="bronze.stock_receipts",
            rows_loaded=0,
            rows_skipped=0,
            errors=("err1", "err2"),
        )
        assert isinstance(result.errors, tuple)

    def test_fields_accessible(self):
        result = LoadResult(
            source_type="manual",
            table_name="bronze.batches",
            rows_loaded=42,
            rows_skipped=3,
            errors=(),
        )
        assert result.source_type == "manual"
        assert result.table_name == "bronze.batches"
        assert result.rows_loaded == 42
        assert result.rows_skipped == 3
        assert result.errors == ()


# ---------------------------------------------------------------------------
# BronzeLoader — abstract enforcement
# ---------------------------------------------------------------------------


class TestBronzeLoaderAbstract:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BronzeLoader()  # type: ignore[abstract]

    def test_subclass_without_all_methods_is_still_abstract(self):
        class IncompleteLoader(BronzeLoader):
            def discover(self):
                return []

            # Missing: read, validate, get_column_map, get_allowed_columns, get_target_table

        with pytest.raises(TypeError):
            IncompleteLoader()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Concrete subclass — run() integration
# ---------------------------------------------------------------------------


class _MinimalReceiptsLoader(BronzeLoader):
    """Minimal concrete implementation for testing."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def discover(self) -> list:
        return ["fake_source"]

    def read(self, source) -> pl.DataFrame:
        return pl.DataFrame(self._rows)

    def validate(self, df: pl.DataFrame) -> pl.DataFrame:
        return df

    def get_column_map(self) -> dict[str, str]:
        return {"drug_code": "drug_code", "quantity": "quantity"}

    def get_allowed_columns(self) -> frozenset[str]:
        return frozenset({"drug_code", "quantity"})

    def get_target_table(self) -> str:
        return "bronze.stock_receipts"


class TestConcreteLoader:
    def _make_engine(self):
        """Return a mock SQLAlchemy engine with a context-manager conn."""
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.begin = MagicMock(return_value=conn)
        return engine, conn

    def test_run_returns_load_result(self):
        rows = [{"drug_code": "ABC123", "quantity": 100.0}]
        loader = _MinimalReceiptsLoader(rows)
        engine, _ = self._make_engine()

        result = loader.run(engine, tenant_id=1)

        assert isinstance(result, LoadResult)
        assert result.rows_loaded == 1
        assert result.table_name == "bronze.stock_receipts"

    def test_run_with_empty_sources_returns_zero_rows(self):
        class EmptyLoader(_MinimalReceiptsLoader):
            def discover(self):
                return []

        loader = EmptyLoader([])
        engine, _ = self._make_engine()

        result = loader.run(engine, tenant_id=1)

        assert result.rows_loaded == 0
        assert result.errors == ()

    def test_run_captures_read_error_in_errors(self):
        class FailingLoader(_MinimalReceiptsLoader):
            def read(self, source):
                raise ValueError("Cannot read file")

        loader = FailingLoader([])
        engine, _ = self._make_engine()

        result = loader.run(engine, tenant_id=1)

        assert result.rows_loaded == 0
        assert len(result.errors) == 1
        assert "Cannot read file" in result.errors[0]

    def test_run_multiple_rows(self):
        rows = [
            {"drug_code": "A", "quantity": 10.0},
            {"drug_code": "B", "quantity": 20.0},
            {"drug_code": "C", "quantity": 30.0},
        ]
        loader = _MinimalReceiptsLoader(rows)
        engine, _ = self._make_engine()

        result = loader.run(engine, tenant_id=5)

        assert result.rows_loaded == 3

    def test_source_type_inferred_from_class_name(self):
        class ExcelReceiptsLoader(_MinimalReceiptsLoader):
            pass

        loader = ExcelReceiptsLoader([])
        assert loader._source_type() == "excel"

    def test_source_type_manual_for_generic_name(self):
        loader = _MinimalReceiptsLoader([])
        assert loader._source_type() == "manual"

    def test_column_whitelist_filters_extra_columns(self):
        """Columns not in get_allowed_columns() must be excluded from INSERT."""
        injection = "'; DROP TABLE bronze.stock_receipts;--"
        rows = [{"drug_code": "X", "quantity": 5.0, "injected_col": injection}]

        captured_sql: list[str] = []

        class TrackingLoader(_MinimalReceiptsLoader):
            pass

        loader = TrackingLoader(rows)
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)

        def capture_execute(stmt, *args, **kwargs):
            captured_sql.append(str(stmt))

        conn.execute = capture_execute
        engine = MagicMock()
        engine.begin = MagicMock(return_value=conn)

        loader.run(engine, tenant_id=1)

        # The injected column must not appear in any INSERT statement
        insert_statements = [s for s in captured_sql if "INSERT" in s.upper()]
        for stmt in insert_statements:
            assert "injected_col" not in stmt

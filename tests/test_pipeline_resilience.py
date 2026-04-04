"""Tests for Session 2: Data Pipeline Resilience audit fixes.

Covers:
- H3: Chunked bronze loader with per-file error handling
- Path traversal validation in file discovery
- M7: Custom SQL quality check timeout
- M8: BETWEEN filter validation
- M6: Forecasting min series length guard
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from datapulse.api.filters import FilterCondition, FilterOp, apply_filters, parse_filters


# ---------------------------------------------------------------------------
# Bronze loader: path traversal validation
# ---------------------------------------------------------------------------


class TestDiscoverFiles:
    """Tests for discover_files() path traversal protection."""

    def test_discovers_xlsx_files(self, tmp_path: Path):
        """Regular .xlsx files in the directory are discovered."""
        from datapulse.bronze.loader import discover_files

        (tmp_path / "Q1.2023.xlsx").write_bytes(b"PK")
        (tmp_path / "Q2.2023.xlsx").write_bytes(b"PK")
        files = discover_files(tmp_path)
        assert len(files) == 2
        assert all(f.suffix == ".xlsx" for f in files)

    def test_no_files_raises(self, tmp_path: Path):
        """Empty directory raises FileNotFoundError."""
        from datapulse.bronze.loader import discover_files

        with pytest.raises(FileNotFoundError, match="No .xlsx files found"):
            discover_files(tmp_path)

    @pytest.mark.skipif(os.name == "nt", reason="symlinks require admin on Windows")
    def test_blocks_symlink_traversal(self, tmp_path: Path):
        """Symlinks pointing outside source_dir are excluded."""
        from datapulse.bronze.loader import discover_files

        # Create a legit file
        (tmp_path / "legit.xlsx").write_bytes(b"PK")

        # Create a symlink pointing outside tmp_path
        outside = Path(tempfile.mkdtemp()) / "secret.xlsx"
        outside.write_bytes(b"PK")
        link = tmp_path / "evil.xlsx"
        link.symlink_to(outside)

        files = discover_files(tmp_path)
        # Should only find the legit file, not the symlink
        assert len(files) == 1
        assert files[0].name == "legit.xlsx"


# ---------------------------------------------------------------------------
# Bronze loader: per-file error handling
# ---------------------------------------------------------------------------


class TestReadAndConcat:
    """Tests for read_and_concat() per-file error handling."""

    @patch("datapulse.bronze.loader.read_single_file")
    def test_skips_bad_files(self, mock_read):
        """Malformed files are skipped; good files are returned."""
        from datapulse.bronze.loader import read_and_concat

        good_df = pl.DataFrame({"col": [1, 2, 3]})
        mock_read.side_effect = [
            good_df,
            ValueError("corrupt file"),
            good_df,
        ]
        files = [Path("a.xlsx"), Path("bad.xlsx"), Path("c.xlsx")]
        result = read_and_concat(files)
        assert result.shape[0] == 6  # 3 + 3

    @patch("datapulse.bronze.loader.read_single_file")
    def test_all_files_fail_raises(self, mock_read):
        """If ALL files fail, a ValueError is raised."""
        from datapulse.bronze.loader import read_and_concat

        mock_read.side_effect = ValueError("corrupt")
        files = [Path("a.xlsx"), Path("b.xlsx")]
        with pytest.raises(ValueError, match="All 2 file\\(s\\) failed"):
            read_and_concat(files)


# ---------------------------------------------------------------------------
# Bronze loader: chunked processing
# ---------------------------------------------------------------------------


class TestChunkedRun:
    """Tests for the chunked run() pipeline."""

    @patch("datapulse.bronze.loader.load_to_postgres", return_value=100)
    @patch("datapulse.bronze.loader.run_migrations")
    @patch("datapulse.bronze.loader._create_engine")
    @patch("datapulse.bronze.loader.save_parquet")
    @patch("datapulse.bronze.loader.rename_columns", side_effect=lambda df: df)
    @patch("datapulse.bronze.loader.read_and_concat")
    @patch("datapulse.bronze.loader.discover_files")
    @patch("datapulse.bronze.loader.get_settings")
    def test_processes_in_chunks(
        self,
        mock_settings,
        mock_discover,
        mock_read_concat,
        mock_rename,
        mock_save_pq,
        mock_engine,
        mock_migrations,
        mock_load,
    ):
        """Files are processed in chunks rather than all at once."""
        from datapulse.bronze.loader import run

        settings = MagicMock()
        settings.database_url = "postgresql://test"
        settings.parquet_dir = Path("/tmp")
        settings.bronze_batch_size = 1000
        mock_settings.return_value = settings

        # 6 files, chunk size 2 => 3 chunks
        files = [Path(f"Q{i}.xlsx") for i in range(6)]
        mock_discover.return_value = files
        mock_read_concat.return_value = pl.DataFrame({"a": [1, 2, 3]})
        mock_engine.return_value = MagicMock()

        run(
            source_dir=Path("/data"),
            database_url="postgresql://test",
            batch_size=1000,
            files_per_chunk=2,
        )

        # read_and_concat called 3 times (3 chunks of 2 files)
        assert mock_read_concat.call_count == 3
        # load_to_postgres called 3 times (once per chunk)
        assert mock_load.call_count == 3


# ---------------------------------------------------------------------------
# M8: BETWEEN filter validation
# ---------------------------------------------------------------------------


class TestBetweenFilter:
    """Tests for BETWEEN filter validation."""

    def test_valid_between(self):
        """Valid BETWEEN filter is parsed correctly."""
        params = {"filter[date][between]": "2024-01-01,2024-12-31"}
        filters = parse_filters(params)
        assert len(filters) == 1
        assert filters[0].op == FilterOp.BETWEEN
        assert filters[0].value == "2024-01-01,2024-12-31"

    def test_between_single_value_ignored(self):
        """BETWEEN with a single value (no comma) is silently skipped."""
        f = FilterCondition(field="date", op=FilterOp.BETWEEN, value="2024-01-01")
        col = MagicMock()
        # Wrap in a mock query
        query = MagicMock()
        result = apply_filters(query, [f], {"date": col})
        # query.where should NOT be called (no valid BETWEEN condition)
        query.where.assert_not_called()

    def test_between_empty_parts_skipped(self):
        """BETWEEN with empty low or high is skipped."""
        f = FilterCondition(field="date", op=FilterOp.BETWEEN, value=",2024-12-31")
        col = MagicMock()
        query = MagicMock()
        result = apply_filters(query, [f], {"date": col})
        query.where.assert_not_called()

    def test_between_reversed_range_swapped(self):
        """BETWEEN with reversed range auto-swaps low and high.

        We test the swap logic by patching and_() to avoid SQLAlchemy's
        type checking on mock objects.
        """
        f = FilterCondition(field="date", op=FilterOp.BETWEEN, value="2024-12-31,2024-01-01")
        col = MagicMock()

        query = MagicMock()
        with patch("datapulse.api.filters.and_", side_effect=lambda *args: args):
            apply_filters(query, [f], {"date": col})
        # col.between should be called with swapped values (low < high)
        col.between.assert_called_once_with("2024-01-01", "2024-12-31")


# ---------------------------------------------------------------------------
# M7: Custom SQL quality check timeout
# ---------------------------------------------------------------------------


class TestCustomSqlTimeout:
    """Tests for statement timeout in custom SQL quality checks."""

    def test_timeout_set_before_query(self):
        """Custom SQL check sets statement_timeout before executing."""
        from datapulse.pipeline.quality_engine import _check_custom_sql

        session = MagicMock()
        session.execute.return_value.scalar_one.return_value = "0"

        result = _check_custom_sql(
            session,
            "bronze",
            {"query": "SELECT COUNT(*) FROM bronze.sales", "expected": "0"},
        )

        # First call should be SET LOCAL statement_timeout
        first_call = session.execute.call_args_list[0]
        sql_text = str(first_call[0][0])
        assert "statement_timeout" in sql_text
        assert result.passed

    def test_timeout_error_handled(self):
        """Timeout errors produce a clear message."""
        from datapulse.pipeline.quality_engine import _check_custom_sql

        session = MagicMock()
        # First call (SET timeout) succeeds, second call (query) times out
        session.execute.side_effect = [
            None,
            Exception("canceling statement due to statement timeout"),
        ]

        result = _check_custom_sql(
            session,
            "bronze",
            {"query": "SELECT 1", "expected": "1"},
        )

        assert not result.passed
        assert "timed out" in result.message

    def test_rejects_non_select(self):
        """Non-SELECT statements are rejected."""
        from datapulse.pipeline.quality_engine import _check_custom_sql

        session = MagicMock()
        result = _check_custom_sql(
            session,
            "bronze",
            {"query": "DROP TABLE bronze.sales", "expected": "0"},
        )

        assert not result.passed
        assert "SELECT" in result.message
        session.execute.assert_not_called()


# ---------------------------------------------------------------------------
# M6: Forecasting min series length
# ---------------------------------------------------------------------------


class TestForecastingMinSeriesLength:
    """Tests for minimum series length guard in forecasting."""

    @patch("datapulse.forecasting.service._run_method")
    @patch("datapulse.forecasting.service.select_best_method")
    def test_skips_daily_with_insufficient_data(self, mock_select, mock_run):
        """Daily forecast is skipped if fewer than 14 data points."""
        from datapulse.forecasting.service import ForecastingService

        repo = MagicMock()
        service = ForecastingService(repo)

        # Only 10 daily data points (need 14 for weekly seasonality)
        repo.get_daily_revenue_series.return_value = [
            ("2024-01-01", 100.0 + i) for i in range(10)
        ]
        repo.get_monthly_revenue_series.return_value = []
        repo.get_top_products_by_revenue.return_value = []
        repo.save_forecasts.return_value = 0

        stats = service.run_all_forecasts()

        # select_best_method should NOT be called for daily
        mock_select.assert_not_called()
        assert "daily_revenue" not in stats

    @patch("datapulse.forecasting.service._run_method")
    @patch("datapulse.forecasting.service.select_best_method")
    def test_runs_daily_with_sufficient_data(self, mock_select, mock_run):
        """Daily forecast runs with 14+ data points."""
        from datetime import date

        from datapulse.forecasting.models import ForecastAccuracy

        from datapulse.forecasting.service import ForecastingService

        repo = MagicMock()
        service = ForecastingService(repo)

        # 30 daily data points (above min 14)
        repo.get_daily_revenue_series.return_value = [
            (date(2024, 1, 1), 100.0 + i) for i in range(30)
        ]
        repo.get_monthly_revenue_series.return_value = []
        repo.get_top_products_by_revenue.return_value = []
        repo.save_forecasts.return_value = 0

        mock_select.return_value = (
            "sma",
            ForecastAccuracy(mape=5.0, mae=10.0, rmse=12.0, coverage=80.0),
        )
        mock_run.return_value = []

        stats = service.run_all_forecasts()

        mock_select.assert_called_once()
        assert "daily_revenue" in stats


# ---------------------------------------------------------------------------
# extract_quarter
# ---------------------------------------------------------------------------


class TestExtractQuarter:
    """Tests for extract_quarter() filename parsing."""

    def test_standard_format(self):
        from datapulse.bronze.loader import extract_quarter

        assert extract_quarter("Q1.2023.xlsx") == "Q1.2023"
        assert extract_quarter("Q4.2025.xlsx") == "Q4.2025"

    def test_nonstandard_format(self):
        from datapulse.bronze.loader import extract_quarter

        assert extract_quarter("sales_data.xlsx") == "sales_data"

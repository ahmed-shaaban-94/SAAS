"""Targeted tests to cover branches missed by the primary test files.

Covers:
- datapulse.bronze.loader: read_and_concat, save_parquet, main() CLI
- datapulse.import_pipeline.reader: latin-1 retry, read_excel, row/column limits
- datapulse.logging: setup_logging (console and JSON renderers)
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from datapulse.bronze.loader import (
    extract_quarter,
    read_and_concat,
    save_parquet,
)
from datapulse.import_pipeline.reader import read_csv, read_excel, read_file
from datapulse.import_pipeline.models import ImportConfig, FileFormat
from datapulse.import_pipeline.validator import ValidationError
from datapulse.logging import setup_logging, get_logger


FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# bronze.loader — read_and_concat
# ---------------------------------------------------------------------------

class TestReadAndConcat:
    """Test read_and_concat() using the real fixture Excel approach — but since
    we only have CSV fixtures, we mock pl.read_excel to avoid needing real .xlsx files.
    """

    def test_concat_single_file(self, tmp_path):
        xlsx_file = tmp_path / "Q1.2023.xlsx"
        xlsx_file.write_bytes(b"fake")

        fake_df = pl.DataFrame({"material": ["ABC"], "quantity": [10]})

        with patch("datapulse.bronze.loader.pl.read_excel", return_value=fake_df):
            result = read_and_concat([xlsx_file])

        assert result.shape[0] == 1
        assert "source_file" in result.columns
        assert "source_quarter" in result.columns

    def test_concat_multiple_files(self, tmp_path):
        files = []
        for q in ("Q1.2023", "Q2.2023"):
            f = tmp_path / f"{q}.xlsx"
            f.write_bytes(b"fake")
            files.append(f)

        fake_df = pl.DataFrame({"material": ["ABC"], "quantity": [10]})

        with patch("datapulse.bronze.loader.pl.read_excel", return_value=fake_df):
            result = read_and_concat(files)

        # 2 files x 1 row each = 2 rows total
        assert result.shape[0] == 2

    def test_source_file_column_contains_filename(self, tmp_path):
        xlsx_file = tmp_path / "Q1.2023.xlsx"
        xlsx_file.write_bytes(b"fake")

        fake_df = pl.DataFrame({"quantity": [5]})

        with patch("datapulse.bronze.loader.pl.read_excel", return_value=fake_df):
            result = read_and_concat([xlsx_file])

        assert result["source_file"][0] == "Q1.2023.xlsx"

    def test_source_quarter_extracted_from_filename(self, tmp_path):
        xlsx_file = tmp_path / "Q3.2024.xlsx"
        xlsx_file.write_bytes(b"fake")

        fake_df = pl.DataFrame({"quantity": [1]})

        with patch("datapulse.bronze.loader.pl.read_excel", return_value=fake_df):
            result = read_and_concat([xlsx_file])

        assert result["source_quarter"][0] == "Q3.2024"


# ---------------------------------------------------------------------------
# bronze.loader — save_parquet
# ---------------------------------------------------------------------------

class TestSaveParquet:
    def test_creates_parquet_file(self, tmp_path):
        df = pl.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
        output = tmp_path / "sub" / "output.parquet"

        result = save_parquet(df, output)

        assert output.exists()
        assert result == output

    def test_creates_parent_directory(self, tmp_path):
        df = pl.DataFrame({"x": [1]})
        deep_path = tmp_path / "a" / "b" / "c" / "out.parquet"

        save_parquet(df, deep_path)

        assert deep_path.exists()

    def test_saved_file_is_readable_as_parquet(self, tmp_path):
        df = pl.DataFrame({"col1": [10, 20], "col2": ["x", "y"]})
        output = tmp_path / "test.parquet"

        save_parquet(df, output)

        loaded = pl.read_parquet(output)
        assert loaded.shape == df.shape
        assert loaded.columns == df.columns


# ---------------------------------------------------------------------------
# bronze.loader — main() CLI entry point
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_calls_run_with_correct_args(self):
        from datapulse.bronze.loader import main

        test_args = [
            "prog",
            "--source", "/tmp/data",
            "--skip-db",
        ]

        with (
            patch("sys.argv", test_args),
            patch("datapulse.bronze.loader.run") as mock_run,
        ):
            mock_run.return_value = pl.DataFrame()
            main()

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["skip_db"] is True

    def test_main_passes_parquet_path_when_given(self):
        from datapulse.bronze.loader import main

        test_args = [
            "prog",
            "--source", "/tmp/data",
            "--parquet", "/tmp/output.parquet",
            "--skip-db",
        ]

        with (
            patch("sys.argv", test_args),
            patch("datapulse.bronze.loader.run") as mock_run,
        ):
            mock_run.return_value = pl.DataFrame()
            main()

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["parquet_path"] == Path("/tmp/output.parquet")

    def test_main_passes_batch_size_when_given(self):
        from datapulse.bronze.loader import main

        test_args = [
            "prog",
            "--source", "/tmp/data",
            "--batch-size", "5000",
            "--skip-db",
        ]

        with (
            patch("sys.argv", test_args),
            patch("datapulse.bronze.loader.run") as mock_run,
        ):
            mock_run.return_value = pl.DataFrame()
            main()

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["batch_size"] == 5000


# ---------------------------------------------------------------------------
# import_pipeline.reader — latin-1 retry path in read_csv
# ---------------------------------------------------------------------------

class TestReadCsvLatin1Retry:
    def test_retries_with_latin1_on_utf8_decode_error(self, tmp_path):
        """If utf-8 decoding fails, read_csv should retry with latin-1."""
        latin1_csv = tmp_path / "latin.csv"
        # Write a CSV with a latin-1 encoded byte (é = 0xe9) that is invalid UTF-8
        latin1_csv.write_bytes(b"name,value\n\xe9l\xe8ve,100\n")

        df = read_csv(latin1_csv, encoding="utf-8")

        assert df.shape[0] == 1
        assert "name" in df.columns

    def test_reraises_on_non_utf8_encoding_failure(self, tmp_path):
        """When encoding is not utf-8, errors are re-raised without retry."""
        latin1_csv = tmp_path / "latin.csv"
        latin1_csv.write_bytes(b"name\ntest")

        # Simulate a ComputeError from polars for non-utf-8 encoding
        with patch(
            "datapulse.import_pipeline.reader.pl.read_csv",
            side_effect=pl.exceptions.ComputeError("encoding error"),
        ):
            with pytest.raises(pl.exceptions.ComputeError):
                read_csv(latin1_csv, encoding="latin-1")


# ---------------------------------------------------------------------------
# import_pipeline.reader — read_excel
# ---------------------------------------------------------------------------

class TestReadExcel:
    def test_raises_validation_error_for_xls_format(self, tmp_path):
        xls_file = tmp_path / "old.xls"
        xls_file.write_bytes(b"fake xls content")

        with pytest.raises(ValidationError, match=".xls format is not supported"):
            read_excel(xls_file)

    def test_calls_polars_read_excel_for_xlsx(self, tmp_path):
        xlsx_file = tmp_path / "data.xlsx"
        xlsx_file.write_bytes(b"fake")
        expected_df = pl.DataFrame({"col": [1, 2]})

        with patch("datapulse.import_pipeline.reader.pl.read_excel", return_value=expected_df) as mock_read:
            result = read_excel(xlsx_file)

        mock_read.assert_called_once()
        assert result.shape == expected_df.shape

    def test_passes_sheet_name_when_provided(self, tmp_path):
        xlsx_file = tmp_path / "data.xlsx"
        xlsx_file.write_bytes(b"fake")
        expected_df = pl.DataFrame({"col": [1]})

        with patch("datapulse.import_pipeline.reader.pl.read_excel", return_value=expected_df) as mock_read:
            read_excel(xlsx_file, sheet_name="Sheet2")

        call_kwargs = mock_read.call_args[1]
        assert call_kwargs.get("sheet_name") == "Sheet2"

    def test_does_not_pass_sheet_name_when_none(self, tmp_path):
        xlsx_file = tmp_path / "data.xlsx"
        xlsx_file.write_bytes(b"fake")
        expected_df = pl.DataFrame({"col": [1]})

        with patch("datapulse.import_pipeline.reader.pl.read_excel", return_value=expected_df) as mock_read:
            read_excel(xlsx_file, sheet_name=None)

        call_kwargs = mock_read.call_args[1]
        assert "sheet_name" not in call_kwargs


# ---------------------------------------------------------------------------
# import_pipeline.reader — row/column limit enforcement in read_file
# ---------------------------------------------------------------------------

class TestReadFileLimits:
    def test_raises_when_row_count_exceeds_max_rows(self):
        """read_file should raise ValidationError when df has too many rows."""
        big_df = pl.DataFrame({"col": list(range(1000))})
        tight_settings = MagicMock()
        tight_settings.max_rows = 5
        tight_settings.max_columns = 200

        with (
            patch("datapulse.import_pipeline.reader.validate_file", return_value=FileFormat.CSV),
            patch("datapulse.import_pipeline.reader.read_csv", return_value=big_df),
            patch("datapulse.import_pipeline.reader.get_settings", return_value=tight_settings),
        ):
            with pytest.raises(ValidationError, match="Too many rows"):
                read_file(FIXTURES / "sample.csv")

    def test_raises_when_column_count_exceeds_max_columns(self):
        """read_file should raise ValidationError when df has too many columns."""
        wide_df = pl.DataFrame({f"col_{i}": [1] for i in range(50)})
        tight_settings = MagicMock()
        tight_settings.max_rows = 10_000_000
        tight_settings.max_columns = 10

        with (
            patch("datapulse.import_pipeline.reader.validate_file", return_value=FileFormat.CSV),
            patch("datapulse.import_pipeline.reader.read_csv", return_value=wide_df),
            patch("datapulse.import_pipeline.reader.get_settings", return_value=tight_settings),
        ):
            with pytest.raises(ValidationError, match="Too many columns"):
                read_file(FIXTURES / "sample.csv")


# ---------------------------------------------------------------------------
# utils.logging — setup_logging
# ---------------------------------------------------------------------------

class TestSetupLogging:
    """setup_logging() calls structlog.get_level_from_name which is only
    available in newer structlog versions. We inject the attribute with
    create=True so the tests work on any installed version.
    """

    def _patch_get_level(self):
        """Patch structlog.get_level_from_name (may not exist in older versions)."""
        import logging
        return patch(
            "structlog.get_level_from_name",
            return_value=logging.INFO,
            create=True,
        )

    def test_setup_logging_console_renderer(self):
        """setup_logging with console format should not raise."""
        with self._patch_get_level():
            with patch.dict(os.environ, {"LOG_FORMAT": "console"}):
                setup_logging("INFO")  # must not raise

    def test_setup_logging_json_renderer(self):
        """setup_logging with json format should call structlog.configure."""
        with self._patch_get_level():
            with patch("structlog.configure") as mock_configure:
                with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
                    setup_logging("DEBUG")
        mock_configure.assert_called_once()

    def test_setup_logging_default_level(self):
        """setup_logging called without arguments should not raise."""
        with self._patch_get_level():
            setup_logging()

    def test_get_logger_returns_logger(self):
        logger = get_logger("test.module")
        assert logger is not None

    def test_get_logger_different_names_work(self):
        l1 = get_logger("module.a")
        l2 = get_logger("module.b")
        assert l1 is not None
        assert l2 is not None

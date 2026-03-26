"""Tests for the import pipeline reader."""

from pathlib import Path

import polars as pl
import pytest

from datapulse.import_pipeline.reader import read_csv, read_file
from datapulse.import_pipeline.validator import ValidationError
from datapulse.import_pipeline.models import ImportConfig, FileFormat

FIXTURES = Path(__file__).parent / "fixtures"


class TestReadCsv:
    def test_reads_csv_successfully(self):
        df = read_csv(FIXTURES / "sample.csv")
        assert df.shape == (5, 5)
        assert df.columns == ["id", "name", "amount", "date", "is_active"]

    def test_reads_correct_values(self):
        df = read_csv(FIXTURES / "sample.csv")
        assert df["name"][0] == "Alice"
        assert df["id"][0] == 1


class TestReadFile:
    def test_read_file_with_path(self):
        df, result = read_file(FIXTURES / "sample.csv")
        assert df.shape[0] == 5
        assert result.file_format == FileFormat.CSV
        assert result.row_count == 5
        assert result.column_count == 5

    def test_read_file_with_config(self):
        config = ImportConfig(file_path=FIXTURES / "sample.csv")
        df, result = read_file(config)
        assert df.shape[0] == 5

    def test_read_file_detects_nulls(self):
        _, result = read_file(FIXTURES / "sample.csv")
        null_cols = [c.name for c in result.columns if c.null_count > 0]
        assert "amount" in null_cols or "date" in null_cols

    def test_read_file_reports_warnings_for_nulls(self):
        _, result = read_file(FIXTURES / "sample.csv")
        assert any("null" in w.lower() for w in result.warnings)

    def test_read_file_nonexistent_raises(self):
        with pytest.raises(ValidationError, match="File not found"):
            read_file(FIXTURES / "nonexistent.csv")

    def test_read_file_unsupported_format_raises(self):
        # Create a temp .txt file
        txt_file = FIXTURES / "temp.txt"
        txt_file.write_text("hello")
        try:
            with pytest.raises(ValidationError, match="Unsupported file type"):
                read_file(txt_file)
        finally:
            txt_file.unlink()

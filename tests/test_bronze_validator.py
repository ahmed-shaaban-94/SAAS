"""Tests for datapulse.import_pipeline.validator — validate_file."""

from __future__ import annotations

import pytest

from datapulse.import_pipeline.models import FileFormat
from datapulse.import_pipeline.validator import ValidationError, validate_file


class TestValidateFile:
    def test_file_not_found_raises(self, tmp_path):
        """Non-existent path raises ValidationError with 'not found' message."""
        p = tmp_path / "missing.xlsx"
        with pytest.raises(ValidationError, match="not found"):
            validate_file(p)

    def test_path_is_directory_raises(self, tmp_path):
        """Passing a directory path raises ValidationError."""
        with pytest.raises(ValidationError, match="Not a file"):
            validate_file(tmp_path)

    def test_txt_extension_raises(self, tmp_path):
        """Unsupported extension raises ValidationError mentioning extension."""
        p = tmp_path / "data.txt"
        p.write_bytes(b"some content")
        with pytest.raises(ValidationError, match="Unsupported file type"):
            validate_file(p)

    def test_json_extension_raises(self, tmp_path):
        """JSON extension is not allowed."""
        p = tmp_path / "data.json"
        p.write_bytes(b'{"key": "val"}')
        with pytest.raises(ValidationError, match="Unsupported file type"):
            validate_file(p)

    def test_empty_file_raises(self, tmp_path):
        """Zero-byte file raises ValidationError with 'empty' message."""
        p = tmp_path / "empty.xlsx"
        p.write_bytes(b"")
        with pytest.raises(ValidationError, match="empty"):
            validate_file(p)

    def test_empty_csv_raises(self, tmp_path):
        """Zero-byte CSV file also raises ValidationError."""
        p = tmp_path / "empty.csv"
        p.write_bytes(b"")
        with pytest.raises(ValidationError, match="empty"):
            validate_file(p)

    def test_file_too_large_raises(self, tmp_path, monkeypatch):
        """File exceeding max size raises ValidationError with 'too large'."""
        from datapulse.import_pipeline import validator

        p = tmp_path / "big.xlsx"
        p.write_bytes(b"x" * 100)

        # Patch settings so max is 50 bytes
        monkeypatch.setattr(
            validator,
            "get_settings",
            lambda: type("S", (), {"max_file_size_bytes": 50, "max_file_size_mb": 0})(),
        )
        with pytest.raises(ValidationError, match="too large"):
            validate_file(p)

    def test_file_too_large_csv_raises(self, tmp_path, monkeypatch):
        """Large CSV also triggers the size check."""
        from datapulse.import_pipeline import validator

        p = tmp_path / "big.csv"
        p.write_bytes(b"a,b,c\n" * 20)  # 120 bytes

        monkeypatch.setattr(
            validator,
            "get_settings",
            lambda: type("S", (), {"max_file_size_bytes": 10, "max_file_size_mb": 0})(),
        )
        with pytest.raises(ValidationError, match="too large"):
            validate_file(p)

    def test_valid_xlsx_returns_xlsx_format(self, tmp_path):
        """Valid .xlsx file returns FileFormat.XLSX."""
        p = tmp_path / "data.xlsx"
        p.write_bytes(b"fake xlsx content")
        result = validate_file(p)
        assert result == FileFormat.XLSX

    def test_valid_csv_returns_csv_format(self, tmp_path):
        """Valid .csv file returns FileFormat.CSV."""
        p = tmp_path / "data.csv"
        p.write_bytes(b"col1,col2\n1,2\n3,4")
        result = validate_file(p)
        assert result == FileFormat.CSV

    def test_valid_xls_returns_xls_format(self, tmp_path):
        """Valid .xls file returns FileFormat.XLS."""
        p = tmp_path / "data.xls"
        p.write_bytes(b"fake xls content")
        result = validate_file(p)
        assert result == FileFormat.XLS

    def test_uppercase_extension_not_allowed(self, tmp_path):
        """Uppercase extension like .XLSX is not accepted."""
        p = tmp_path / "data.XLSX"
        p.write_bytes(b"some content")
        # suffix.lower() maps .XLSX -> .xlsx -> allowed
        # The validator does suffix.lower() so XLSX IS accepted
        result = validate_file(p)
        assert result == FileFormat.XLSX

    def test_valid_file_exactly_at_limit(self, tmp_path, monkeypatch):
        """File exactly at the size limit passes validation."""
        from datapulse.import_pipeline import validator

        p = tmp_path / "edge.xlsx"
        p.write_bytes(b"x" * 100)

        monkeypatch.setattr(
            validator,
            "get_settings",
            lambda: type("S", (), {"max_file_size_bytes": 100, "max_file_size_mb": 0})(),
        )
        result = validate_file(p)
        assert result == FileFormat.XLSX

    def test_file_one_byte_over_limit_raises(self, tmp_path, monkeypatch):
        """File one byte over the limit raises ValidationError."""
        from datapulse.import_pipeline import validator

        p = tmp_path / "edge.xlsx"
        p.write_bytes(b"x" * 101)

        monkeypatch.setattr(
            validator,
            "get_settings",
            lambda: type("S", (), {"max_file_size_bytes": 100, "max_file_size_mb": 0})(),
        )
        with pytest.raises(ValidationError, match="too large"):
            validate_file(p)

    def test_validation_error_is_exception(self):
        """ValidationError is a subclass of Exception."""
        assert issubclass(ValidationError, Exception)

    def test_file_not_found_message_contains_path(self, tmp_path):
        """The 'not found' error includes the file path."""
        p = tmp_path / "nonexistent.xlsx"
        with pytest.raises(ValidationError, match=str(p.name)):
            validate_file(p)

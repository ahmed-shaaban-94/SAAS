"""Tests for datapulse.import_pipeline.validator — validate_file()."""

from pathlib import Path
from unittest.mock import patch

import pytest

from datapulse.config import Settings
from datapulse.import_pipeline.models import FileFormat
from datapulse.import_pipeline.validator import ALLOWED_EXTENSIONS, ValidationError, validate_file

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: bytes = b"data") -> Path:
    """Write bytes to a path and return it."""
    path.write_bytes(content)
    return path


def _settings_with_max_mb(max_mb: int) -> Settings:
    """Return a Settings instance with a custom max file size, bypassing .env."""
    return Settings(_env_file=None, max_file_size_mb=max_mb, database_url="")


def _patch_settings(max_mb: int):
    """Context manager that patches get_settings in the validator module."""
    s = _settings_with_max_mb(max_mb)
    return patch(
        "datapulse.import_pipeline.validator.get_settings",
        return_value=s,
    )


# ---------------------------------------------------------------------------
# Test: file does not exist
# ---------------------------------------------------------------------------


class TestValidateFileMissing:
    def test_raises_when_file_not_found(self, tmp_path):
        missing = tmp_path / "ghost.csv"
        with pytest.raises(ValidationError, match="File not found"):
            validate_file(missing)

    def test_raises_when_path_is_directory(self, tmp_path):
        subdir = tmp_path / "adir"
        subdir.mkdir()
        with pytest.raises(ValidationError, match="Not a file"):
            validate_file(subdir)


# ---------------------------------------------------------------------------
# Test: unsupported extensions
# ---------------------------------------------------------------------------


class TestValidateFileExtension:
    @pytest.mark.parametrize("ext", [".txt", ".json", ".parquet", ".pdf", ".xml", ""])
    def test_raises_on_unsupported_extension(self, tmp_path, ext):
        # A file named "file" (empty ext) needs special handling
        name = f"file{ext}" if ext else "file"
        bad_file = _write(tmp_path / name)
        with pytest.raises(ValidationError, match="Unsupported file type"):
            validate_file(bad_file)

    def test_error_message_lists_allowed_types(self, tmp_path):
        bad_file = _write(tmp_path / "file.txt")
        with pytest.raises(ValidationError) as exc_info:
            validate_file(bad_file)
        message = str(exc_info.value)
        for allowed in ALLOWED_EXTENSIONS:
            assert allowed in message

    @pytest.mark.parametrize(
        "ext,expected_format",
        [
            (".csv", FileFormat.CSV),
            (".xlsx", FileFormat.XLSX),
            (".xls", FileFormat.XLS),
        ],
    )
    def test_accepts_all_allowed_extensions(self, tmp_path, ext, expected_format):
        valid_file = _write(tmp_path / f"file{ext}")
        with _patch_settings(500):
            result = validate_file(valid_file)
        assert result == expected_format

    def test_extension_comparison_is_case_insensitive(self, tmp_path):
        # .CSV uppercase must be accepted (suffix is lowercased in validator)
        upper_file = _write(tmp_path / "file.CSV")
        with _patch_settings(500):
            result = validate_file(upper_file)
        assert result == FileFormat.CSV


# ---------------------------------------------------------------------------
# Test: empty files
# ---------------------------------------------------------------------------


class TestValidateFileEmpty:
    def test_raises_on_empty_csv(self, tmp_path):
        empty = tmp_path / "empty.csv"
        empty.write_bytes(b"")
        with pytest.raises(ValidationError, match="File is empty"):
            validate_file(empty)

    def test_raises_on_empty_xlsx(self, tmp_path):
        empty = tmp_path / "empty.xlsx"
        empty.write_bytes(b"")
        with pytest.raises(ValidationError, match="File is empty"):
            validate_file(empty)

    def test_raises_on_empty_xls(self, tmp_path):
        empty = tmp_path / "empty.xls"
        empty.write_bytes(b"")
        with pytest.raises(ValidationError, match="File is empty"):
            validate_file(empty)


# ---------------------------------------------------------------------------
# Test: oversized files
# ---------------------------------------------------------------------------


class TestValidateFileSize:
    def test_raises_when_file_exceeds_limit(self, tmp_path):
        # 2 MB file against a 1 MB limit
        large_file = _write(tmp_path / "large.csv", b"x" * (2 * 1024 * 1024))
        with _patch_settings(max_mb=1), pytest.raises(ValidationError, match="File too large"):
            validate_file(large_file)

    def test_error_message_contains_size_in_mb(self, tmp_path):
        large_file = _write(tmp_path / "large.csv", b"x" * (2 * 1024 * 1024))
        with _patch_settings(max_mb=1), pytest.raises(ValidationError) as exc_info:
            validate_file(large_file)
        assert "MB" in str(exc_info.value)

    def test_error_message_contains_max_mb_limit(self, tmp_path):
        large_file = _write(tmp_path / "large.csv", b"x" * (2 * 1024 * 1024))
        with _patch_settings(max_mb=1), pytest.raises(ValidationError) as exc_info:
            validate_file(large_file)
        # The message should mention the configured limit (1 MB)
        assert "1" in str(exc_info.value)

    def test_file_below_limit_is_accepted(self, tmp_path):
        # 512 KB file against a 1 MB limit — must pass
        small_file = _write(tmp_path / "small.csv", b"x" * (512 * 1024))
        with _patch_settings(max_mb=1):
            result = validate_file(small_file)
        assert result == FileFormat.CSV

    def test_file_exactly_at_limit_is_accepted(self, tmp_path):
        # exactly max_file_size_bytes - 1 byte (strictly less than limit → accepted)
        at_limit = _write(tmp_path / "atlimit.csv", b"x" * (1 * 1024 * 1024 - 1))
        with _patch_settings(max_mb=1):
            result = validate_file(at_limit)
        assert result == FileFormat.CSV

    def test_file_one_byte_over_limit_is_rejected(self, tmp_path):
        over_limit = _write(tmp_path / "over.csv", b"x" * (1 * 1024 * 1024 + 1))
        with _patch_settings(max_mb=1), pytest.raises(ValidationError, match="File too large"):
            validate_file(over_limit)


# ---------------------------------------------------------------------------
# Test: return values (happy path)
# ---------------------------------------------------------------------------


class TestValidateFileReturnValues:
    def test_csv_returns_csv_format(self, tmp_path):
        f = _write(tmp_path / "data.csv")
        with _patch_settings(500):
            assert validate_file(f) == FileFormat.CSV

    def test_xlsx_returns_xlsx_format(self, tmp_path):
        f = _write(tmp_path / "data.xlsx")
        with _patch_settings(500):
            assert validate_file(f) == FileFormat.XLSX

    def test_xls_returns_xls_format(self, tmp_path):
        f = _write(tmp_path / "data.xls")
        with _patch_settings(500):
            assert validate_file(f) == FileFormat.XLS

    def test_validation_error_is_exception_subclass(self):
        assert issubclass(ValidationError, Exception)

    def test_allowed_extensions_set_content(self):
        assert {".csv", ".xlsx", ".xls"} == ALLOWED_EXTENSIONS

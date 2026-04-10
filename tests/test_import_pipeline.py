"""Tests for import pipeline — validator, reader, type_detector."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from datapulse.import_pipeline.models import DetectedType, FileFormat
from datapulse.import_pipeline.type_detector import detect_column_types
from datapulse.import_pipeline.validator import ValidationError, validate_file

# ============================================================
# Helpers
# ============================================================

def _write_csv(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _write_bytes(tmp_path: Path, name: str, content: bytes) -> Path:
    p = tmp_path / name
    p.write_bytes(content)
    return p


# ============================================================
# validator.py
# ============================================================


@pytest.mark.unit
def test_validate_file_not_found(tmp_path):
    with pytest.raises(ValidationError, match="not found"):
        validate_file(tmp_path / "nonexistent.csv")


@pytest.mark.unit
def test_validate_file_not_a_file(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    with pytest.raises(ValidationError, match="Not a file"):
        validate_file(d)


@pytest.mark.unit
def test_validate_file_unsupported_extension(tmp_path):
    p = _write_bytes(tmp_path, "data.txt", b"hello")
    with pytest.raises(ValidationError, match="Unsupported file type"):
        validate_file(p)


@pytest.mark.unit
def test_validate_file_empty(tmp_path):
    p = _write_bytes(tmp_path, "empty.csv", b"")
    with pytest.raises(ValidationError, match="empty"):
        validate_file(p)


@pytest.mark.unit
def test_validate_file_too_large(tmp_path):
    p = _write_bytes(tmp_path, "big.csv", b"a,b\n1,2\n")
    with patch("datapulse.import_pipeline.validator.get_settings") as mock_settings:
        mock_settings.return_value.max_file_size_bytes = 5  # tiny limit
        mock_settings.return_value.max_file_size_mb = 0
        with pytest.raises(ValidationError, match="too large"):
            validate_file(p)


@pytest.mark.unit
def test_validate_file_csv(tmp_path):
    p = _write_csv(tmp_path, "data.csv", "a,b\n1,2\n")
    result = validate_file(p)
    assert result == FileFormat.CSV


@pytest.mark.unit
def test_validate_file_xlsx(tmp_path):
    # XLSX magic bytes (PK\x03\x04) with minimal content
    xlsx_bytes = b"PK\x03\x04" + b"\x00" * 20
    p = _write_bytes(tmp_path, "data.xlsx", xlsx_bytes)
    result = validate_file(p)
    assert result == FileFormat.XLSX


# ============================================================
# reader.py
# ============================================================


@pytest.mark.unit
def test_read_csv_happy_path(tmp_path):
    from datapulse.import_pipeline.reader import read_csv

    p = _write_csv(tmp_path, "sales.csv", "product,qty\nAlpha,10\nBeta,20\n")
    df = read_csv(p)
    assert df.shape == (2, 2)
    assert "product" in df.columns
    assert "qty" in df.columns


@pytest.mark.unit
def test_read_csv_latin1_fallback(tmp_path):
    from datapulse.import_pipeline.reader import read_csv

    # Write latin-1 encoded content that is NOT valid UTF-8
    content = "name,value\néàü,1\n".encode("latin-1")
    p = _write_bytes(tmp_path, "latin.csv", content)
    df = read_csv(p)  # should retry with latin-1
    assert df.shape[0] == 1


@pytest.mark.unit
def test_read_excel_happy_path(tmp_path):
    """Test XLSX reading — uses a real (minimal) XLSX file via openpyxl."""
    pytest.importorskip("openpyxl")
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["product", "qty"])
    ws.append(["Alpha", 10])
    ws.append(["Beta", 20])
    p = tmp_path / "test.xlsx"
    wb.save(str(p))

    from datapulse.import_pipeline.reader import read_excel

    df = read_excel(p)
    assert df.shape == (2, 2)


@pytest.mark.unit
def test_read_excel_xls_rejected(tmp_path):
    from datapulse.import_pipeline.reader import read_excel

    p = _write_bytes(tmp_path, "old.xls", b"\xd0\xcf\x11\xe0" + b"\x00" * 20)
    with pytest.raises(ValidationError, match=".xls format is not supported"):
        read_excel(p)


@pytest.mark.unit
def test_read_file_too_many_rows(tmp_path):
    from datapulse.import_pipeline.reader import read_file

    rows = "\n".join(f"row{i},{i}" for i in range(10))
    p = _write_csv(tmp_path, "big.csv", "a,b\n" + rows)
    with patch("datapulse.import_pipeline.reader.get_settings") as mock_settings:
        mock_settings.return_value.max_rows = 3
        mock_settings.return_value.max_columns = 100
        with pytest.raises(ValidationError, match="Too many rows"):
            read_file(p)


@pytest.mark.unit
def test_read_file_too_many_columns(tmp_path):
    from datapulse.import_pipeline.reader import read_file

    headers = ",".join(f"col{i}" for i in range(10))
    values = ",".join(str(i) for i in range(10))
    p = _write_csv(tmp_path, "wide.csv", f"{headers}\n{values}\n")
    with patch("datapulse.import_pipeline.reader.get_settings") as mock_settings:
        mock_settings.return_value.max_rows = 10_000_000
        mock_settings.return_value.max_columns = 5
        with pytest.raises(ValidationError, match="Too many columns"):
            read_file(p)


# ============================================================
# type_detector.py
# ============================================================


@pytest.mark.unit
def test_detect_integer_column():
    df = pl.DataFrame({"count": [1, 2, 3, 4]})
    cols = detect_column_types(df)
    assert cols[0].detected_type == DetectedType.INTEGER


@pytest.mark.unit
def test_detect_float_column():
    df = pl.DataFrame({"price": [1.5, 2.5, 3.0]})
    cols = detect_column_types(df)
    assert cols[0].detected_type == DetectedType.FLOAT


@pytest.mark.unit
def test_detect_string_column():
    df = pl.DataFrame({"name": ["Alice", "Bob", "Carol"]})
    cols = detect_column_types(df)
    assert cols[0].detected_type == DetectedType.STRING


@pytest.mark.unit
def test_detect_date_column():
    import datetime

    df = pl.DataFrame({"date": [datetime.date(2024, 1, 1), datetime.date(2024, 1, 2)]})
    cols = detect_column_types(df)
    assert cols[0].detected_type == DetectedType.DATE


@pytest.mark.unit
def test_detect_boolean_column():
    df = pl.DataFrame({"flag": [True, False, True]})
    cols = detect_column_types(df)
    assert cols[0].detected_type == DetectedType.BOOLEAN


@pytest.mark.unit
def test_detect_null_counts():
    df = pl.DataFrame({"a": [1, None, 3, None, 5]})
    cols = detect_column_types(df)
    assert cols[0].null_count == 2


@pytest.mark.unit
def test_detect_with_no_samples():
    df = pl.DataFrame({"x": [10, 20, 30]})
    cols = detect_column_types(df, include_samples=False)
    assert cols[0].sample_values == []

"""Tests for ExcelReceiptsLoader — discover, read, validate methods."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from datapulse.bronze.receipts_column_map import COLUMN_MAP
from datapulse.bronze.receipts_loader import ALLOWED_COLUMNS, ExcelReceiptsLoader


@pytest.fixture()
def loader(tmp_path: Path) -> ExcelReceiptsLoader:
    return ExcelReceiptsLoader(tmp_path)


# ------------------------------------------------------------------
# Metadata
# ------------------------------------------------------------------


def test_get_target_table(loader):
    assert loader.get_target_table() == "bronze.stock_receipts"


def test_get_column_map(loader):
    cm = loader.get_column_map()
    assert cm is COLUMN_MAP
    assert "Drug Code" in cm
    assert cm["Drug Code"] == "drug_code"


def test_get_allowed_columns(loader):
    ac = loader.get_allowed_columns()
    assert ac is ALLOWED_COLUMNS
    assert "drug_code" in ac
    assert "receipt_date" in ac
    assert "source_file" in ac
    assert "tenant_id" in ac


# ------------------------------------------------------------------
# discover()
# ------------------------------------------------------------------


def test_discover_finds_xlsx_files(tmp_path: Path):
    f1 = tmp_path / "receipts_jan.xlsx"
    f2 = tmp_path / "receipts_feb.xlsx"
    f1.touch()
    f2.touch()

    loader = ExcelReceiptsLoader(tmp_path)
    found = loader.discover()
    assert len(found) == 2
    assert all(f.suffix == ".xlsx" for f in found)


def test_discover_raises_when_no_files(tmp_path: Path):
    loader = ExcelReceiptsLoader(tmp_path)
    with pytest.raises(FileNotFoundError, match="No .xlsx files found"):
        loader.discover()


def test_discover_ignores_non_xlsx(tmp_path: Path):
    (tmp_path / "data.csv").touch()
    (tmp_path / "notes.txt").touch()
    loader = ExcelReceiptsLoader(tmp_path)
    with pytest.raises(FileNotFoundError):
        loader.discover()


def test_discover_recursive(tmp_path: Path):
    subdir = tmp_path / "2025" / "q1"
    subdir.mkdir(parents=True)
    (subdir / "receipts.xlsx").touch()

    loader = ExcelReceiptsLoader(tmp_path)
    found = loader.discover()
    assert len(found) == 1


def test_discover_path_traversal_safe(tmp_path: Path):
    """Files resolved outside source_dir should be excluded."""
    (tmp_path / "safe.xlsx").touch()
    loader = ExcelReceiptsLoader(tmp_path)
    found = loader.discover()
    # All resolved paths must be inside tmp_path
    resolved_root = tmp_path.resolve()
    for f in found:
        assert f.resolve().is_relative_to(resolved_root)


# ------------------------------------------------------------------
# read()
# ------------------------------------------------------------------


def test_read_adds_source_file_column(tmp_path: Path):
    fake_file = tmp_path / "receipts_2025.xlsx"
    fake_file.touch()

    raw_df = pl.DataFrame({"Drug Code": ["D001"], "Quantity": [50]})

    loader = ExcelReceiptsLoader(tmp_path)
    with patch("datapulse.bronze.receipts_loader.pl.read_excel", return_value=raw_df):
        result = loader.read(fake_file)

    assert "source_file" in result.columns
    assert result["source_file"][0] == "receipts_2025.xlsx"


def test_read_calls_calamine_engine(tmp_path: Path):
    fake_file = tmp_path / "data.xlsx"
    fake_file.touch()

    raw_df = pl.DataFrame({"Drug Code": ["D001"]})
    loader = ExcelReceiptsLoader(tmp_path)

    with patch("datapulse.bronze.receipts_loader.pl.read_excel", return_value=raw_df) as mock_read:
        loader.read(fake_file)

    mock_read.assert_called_once_with(fake_file, engine="calamine")


# ------------------------------------------------------------------
# validate()
# ------------------------------------------------------------------


def _excel_df(**extra) -> pl.DataFrame:
    """Build a DataFrame with Excel-style column headers."""
    data: dict = {
        "Drug Code": ["D001"],
        "Receipt Date": ["2025-01-15"],
        "Quantity": [100],
        **extra,
    }
    return pl.DataFrame(data)


def test_validate_renames_columns(loader):
    df = _excel_df()
    result = loader.validate(df)
    assert "drug_code" in result.columns
    assert "receipt_date" in result.columns
    assert "Drug Code" not in result.columns


def test_validate_passes_already_renamed_columns(loader):
    """If columns are already in DB names (e.g. from a prior rename), still valid."""
    df = pl.DataFrame({"drug_code": ["D001"], "receipt_date": ["2025-01-01"]})
    result = loader.validate(df)
    assert "drug_code" in result.columns


def test_validate_raises_on_missing_drug_code(loader):
    df = pl.DataFrame({"Receipt Date": ["2025-01-01"], "Quantity": [10]})
    with pytest.raises(ValueError, match="drug_code"):
        loader.validate(df)


def test_validate_raises_on_missing_receipt_date(loader):
    df = pl.DataFrame({"Drug Code": ["D001"], "Quantity": [10]})
    with pytest.raises(ValueError, match="receipt_date"):
        loader.validate(df)


def test_validate_raises_on_null_drug_code(loader):
    df = pl.DataFrame({"Drug Code": [None], "Receipt Date": ["2025-01-01"]})
    with pytest.raises(ValueError, match="drug_code has 1 null"):
        loader.validate(df)


def test_validate_passes_with_optional_columns(loader):
    df = _excel_df(**{"Batch Number": ["B001"], "Unit Cost": ["5.00"]})
    result = loader.validate(df)
    assert "batch_number" in result.columns
    assert "unit_cost" in result.columns


def test_validate_skips_unknown_columns(loader):
    """Columns not in COLUMN_MAP stay as-is (whitelisting happens in run())."""
    df = _excel_df(**{"Unknown Column": ["value"]})
    result = loader.validate(df)
    assert "Unknown Column" in result.columns


# ------------------------------------------------------------------
# LOADER_REGISTRY registration
# ------------------------------------------------------------------


def test_loader_registered():
    from datapulse.bronze.registry import LOADER_REGISTRY

    assert "stock_receipts" in LOADER_REGISTRY
    assert LOADER_REGISTRY["stock_receipts"] is ExcelReceiptsLoader

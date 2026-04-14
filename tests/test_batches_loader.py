"""Tests for ExcelBatchesLoader — column map, validation, and discover logic."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from datapulse.bronze.batches_column_map import COLUMN_MAP
from datapulse.bronze.batches_loader import ALLOWED_COLUMNS, ExcelBatchesLoader


@pytest.fixture()
def loader(tmp_path: Path) -> ExcelBatchesLoader:
    return ExcelBatchesLoader(source_dir=tmp_path)


# ------------------------------------------------------------------
# COLUMN_MAP
# ------------------------------------------------------------------


def test_column_map_has_required_keys():
    assert "Drug Code" in COLUMN_MAP
    assert "Batch Number" in COLUMN_MAP
    assert "Expiry Date" in COLUMN_MAP


def test_column_map_values():
    assert COLUMN_MAP["Drug Code"] == "drug_code"
    assert COLUMN_MAP["Batch Number"] == "batch_number"
    assert COLUMN_MAP["Expiry Date"] == "expiry_date"
    assert COLUMN_MAP["Site Code"] == "site_code"
    assert COLUMN_MAP["Initial Quantity"] == "initial_quantity"
    assert COLUMN_MAP["Current Quantity"] == "current_quantity"
    assert COLUMN_MAP["Unit Cost"] == "unit_cost"
    assert COLUMN_MAP["Status"] == "status"


def test_column_map_notes_included():
    assert "Notes" in COLUMN_MAP
    assert COLUMN_MAP["Notes"] == "notes"


# ------------------------------------------------------------------
# ALLOWED_COLUMNS
# ------------------------------------------------------------------


def test_allowed_columns_includes_db_names():
    assert "drug_code" in ALLOWED_COLUMNS
    assert "batch_number" in ALLOWED_COLUMNS
    assert "expiry_date" in ALLOWED_COLUMNS


def test_allowed_columns_includes_metadata():
    assert "source_file" in ALLOWED_COLUMNS
    assert "loaded_at" in ALLOWED_COLUMNS
    assert "tenant_id" in ALLOWED_COLUMNS


# ------------------------------------------------------------------
# get_target_table / get_column_map
# ------------------------------------------------------------------


def test_get_target_table(loader: ExcelBatchesLoader):
    assert loader.get_target_table() == "bronze.batches"


def test_get_column_map(loader: ExcelBatchesLoader):
    assert loader.get_column_map() is COLUMN_MAP


def test_get_allowed_columns(loader: ExcelBatchesLoader):
    assert loader.get_allowed_columns() is ALLOWED_COLUMNS


# ------------------------------------------------------------------
# discover
# ------------------------------------------------------------------


def test_discover_finds_xlsx_files(tmp_path: Path):
    (tmp_path / "batches_2025.xlsx").touch()
    (tmp_path / "batches_2026.xlsx").touch()
    loader = ExcelBatchesLoader(tmp_path)
    found = loader.discover()
    assert len(found) == 2
    assert all(f.suffix == ".xlsx" for f in found)


def test_discover_ignores_non_xlsx(tmp_path: Path):
    (tmp_path / "batches.csv").touch()
    (tmp_path / "batches.xlsx").touch()
    loader = ExcelBatchesLoader(tmp_path)
    found = loader.discover()
    assert len(found) == 1
    assert found[0].name == "batches.xlsx"


def test_discover_raises_if_no_files(tmp_path: Path):
    loader = ExcelBatchesLoader(tmp_path)
    with pytest.raises(FileNotFoundError, match="No .xlsx files found"):
        loader.discover()


def test_discover_prevents_path_traversal(tmp_path: Path):
    """Files outside the source root must not be discovered."""
    other_dir = tmp_path.parent / "other"
    other_dir.mkdir(exist_ok=True)
    (other_dir / "evil.xlsx").touch()
    loader = ExcelBatchesLoader(tmp_path)
    with pytest.raises(FileNotFoundError):
        loader.discover()


# ------------------------------------------------------------------
# read
# ------------------------------------------------------------------


def test_read_adds_source_file_column(tmp_path: Path):
    source = tmp_path / "batches_Q1.xlsx"
    df_in = pl.DataFrame({
        "Drug Code": ["D001"],
        "Batch Number": ["B001"],
        "Expiry Date": ["2025-06-01"],
    })

    loader = ExcelBatchesLoader(tmp_path)
    with patch("datapulse.bronze.batches_loader.pl.read_excel", return_value=df_in):
        df_out = loader.read(source)

    assert "source_file" in df_out.columns
    assert df_out["source_file"][0] == "batches_Q1.xlsx"


# ------------------------------------------------------------------
# validate
# ------------------------------------------------------------------


def _make_valid_df() -> pl.DataFrame:
    return pl.DataFrame({
        "Drug Code": ["D001", "D002"],
        "Batch Number": ["B001", "B002"],
        "Expiry Date": ["2025-06-01", "2025-12-01"],
        "Site Code": ["S01", "S01"],
        "Current Quantity": [100.0, 50.0],
    })


def test_validate_renames_columns(loader: ExcelBatchesLoader):
    df = _make_valid_df()
    result = loader.validate(df)
    assert "drug_code" in result.columns
    assert "batch_number" in result.columns
    assert "expiry_date" in result.columns


def test_validate_missing_drug_code_raises(loader: ExcelBatchesLoader):
    df = pl.DataFrame({
        "Batch Number": ["B001"],
        "Expiry Date": ["2025-06-01"],
    })
    with pytest.raises(ValueError, match="drug_code"):
        loader.validate(df)


def test_validate_missing_batch_number_raises(loader: ExcelBatchesLoader):
    df = pl.DataFrame({
        "Drug Code": ["D001"],
        "Expiry Date": ["2025-06-01"],
    })
    with pytest.raises(ValueError, match="batch_number"):
        loader.validate(df)


def test_validate_missing_expiry_date_raises(loader: ExcelBatchesLoader):
    df = pl.DataFrame({
        "Drug Code": ["D001"],
        "Batch Number": ["B001"],
    })
    with pytest.raises(ValueError, match="expiry_date"):
        loader.validate(df)


def test_validate_null_drug_code_raises(loader: ExcelBatchesLoader):
    df = pl.DataFrame({
        "Drug Code": [None],
        "Batch Number": ["B001"],
        "Expiry Date": ["2025-06-01"],
    })
    with pytest.raises(ValueError, match="drug_code, batch_number, and expiry_date"):
        loader.validate(df)


def test_validate_null_batch_number_raises(loader: ExcelBatchesLoader):
    df = pl.DataFrame({
        "Drug Code": ["D001"],
        "Batch Number": [None],
        "Expiry Date": ["2025-06-01"],
    })
    with pytest.raises(ValueError, match="drug_code, batch_number, and expiry_date"):
        loader.validate(df)


def test_validate_null_expiry_date_raises(loader: ExcelBatchesLoader):
    df = pl.DataFrame({
        "Drug Code": ["D001"],
        "Batch Number": ["B001"],
        "Expiry Date": [None],
    })
    with pytest.raises(ValueError, match="drug_code, batch_number, and expiry_date"):
        loader.validate(df)


def test_validate_partial_null_raises(loader: ExcelBatchesLoader):
    """If any row has a null required field, validation must fail."""
    df = pl.DataFrame({
        "Drug Code": ["D001", None],
        "Batch Number": ["B001", "B002"],
        "Expiry Date": ["2025-06-01", "2025-12-01"],
    })
    with pytest.raises(ValueError):
        loader.validate(df)


def test_validate_valid_dataframe_passes(loader: ExcelBatchesLoader):
    df = _make_valid_df()
    result = loader.validate(df)
    assert result is not None
    assert len(result) == 2

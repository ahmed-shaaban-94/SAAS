"""Tests for ExcelAdjustmentsLoader — discover, read, validate methods."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from datapulse.bronze.adjustments_column_map import COLUMN_MAP
from datapulse.bronze.adjustments_loader import ALLOWED_COLUMNS, ExcelAdjustmentsLoader


@pytest.fixture()
def loader(tmp_path: Path) -> ExcelAdjustmentsLoader:
    return ExcelAdjustmentsLoader(tmp_path)


# ------------------------------------------------------------------
# Metadata
# ------------------------------------------------------------------


def test_get_target_table(loader):
    assert loader.get_target_table() == "bronze.stock_adjustments"


def test_get_column_map(loader):
    cm = loader.get_column_map()
    assert cm is COLUMN_MAP
    assert "Drug Code" in cm
    assert cm["Drug Code"] == "drug_code"


def test_get_allowed_columns(loader):
    ac = loader.get_allowed_columns()
    assert ac is ALLOWED_COLUMNS
    assert "drug_code" in ac
    assert "adjustment_date" in ac
    assert "adjustment_type" in ac
    assert "source_file" in ac
    assert "tenant_id" in ac


# ------------------------------------------------------------------
# discover()
# ------------------------------------------------------------------


def test_discover_finds_xlsx_files(tmp_path: Path):
    (tmp_path / "adjustments_jan.xlsx").touch()
    (tmp_path / "adjustments_feb.xlsx").touch()
    loader = ExcelAdjustmentsLoader(tmp_path)
    found = loader.discover()
    assert len(found) == 2


def test_discover_raises_when_no_files(tmp_path: Path):
    loader = ExcelAdjustmentsLoader(tmp_path)
    with pytest.raises(FileNotFoundError, match="No .xlsx files found"):
        loader.discover()


def test_discover_ignores_non_xlsx(tmp_path: Path):
    (tmp_path / "adjustments.csv").touch()
    loader = ExcelAdjustmentsLoader(tmp_path)
    with pytest.raises(FileNotFoundError):
        loader.discover()


def test_discover_recursive(tmp_path: Path):
    subdir = tmp_path / "archive" / "2025"
    subdir.mkdir(parents=True)
    (subdir / "adj.xlsx").touch()
    loader = ExcelAdjustmentsLoader(tmp_path)
    assert len(loader.discover()) == 1


def test_discover_returns_sorted_paths(tmp_path: Path):
    (tmp_path / "b.xlsx").touch()
    (tmp_path / "a.xlsx").touch()
    loader = ExcelAdjustmentsLoader(tmp_path)
    found = loader.discover()
    names = [f.name for f in found]
    assert names == sorted(names)


# ------------------------------------------------------------------
# read()
# ------------------------------------------------------------------


def test_read_adds_source_file_column(tmp_path: Path):
    fake_file = tmp_path / "adjustments_2025.xlsx"
    fake_file.touch()

    raw_df = pl.DataFrame({"Drug Code": ["D001"], "Adjustment Type": ["damage"]})
    loader = ExcelAdjustmentsLoader(tmp_path)

    with patch("datapulse.bronze.adjustments_loader.pl.read_excel", return_value=raw_df):
        result = loader.read(fake_file)

    assert "source_file" in result.columns
    assert result["source_file"][0] == "adjustments_2025.xlsx"


def test_read_calls_calamine_engine(tmp_path: Path):
    fake_file = tmp_path / "data.xlsx"
    fake_file.touch()

    raw_df = pl.DataFrame({"Drug Code": ["D001"]})
    loader = ExcelAdjustmentsLoader(tmp_path)

    with patch(
        "datapulse.bronze.adjustments_loader.pl.read_excel", return_value=raw_df
    ) as mock_read:
        loader.read(fake_file)

    mock_read.assert_called_once_with(fake_file, engine="calamine")


# ------------------------------------------------------------------
# validate()
# ------------------------------------------------------------------


def _excel_df(**extra) -> pl.DataFrame:
    data: dict = {
        "Drug Code": ["D001"],
        "Adjustment Date": ["2025-03-10"],
        "Adjustment Type": ["damage"],
        "Quantity": [-5],
        **extra,
    }
    return pl.DataFrame(data)


def test_validate_renames_columns(loader):
    df = _excel_df()
    result = loader.validate(df)
    assert "drug_code" in result.columns
    assert "adjustment_date" in result.columns
    assert "adjustment_type" in result.columns
    assert "Drug Code" not in result.columns


def test_validate_raises_on_missing_drug_code(loader):
    df = pl.DataFrame({"Adjustment Date": ["2025-01-01"], "Adjustment Type": ["damage"]})
    with pytest.raises(ValueError, match="drug_code"):
        loader.validate(df)


def test_validate_raises_on_missing_adjustment_date(loader):
    df = pl.DataFrame({"Drug Code": ["D001"], "Adjustment Type": ["correction"]})
    with pytest.raises(ValueError, match="adjustment_date"):
        loader.validate(df)


def test_validate_raises_on_null_drug_code(loader):
    df = pl.DataFrame({"Drug Code": [None], "Adjustment Date": ["2025-01-01"]})
    with pytest.raises(ValueError, match="drug_code has 1 null"):
        loader.validate(df)


def test_validate_passes_with_optional_columns(loader):
    df = _excel_df(**{"Reason": ["Broken"], "Batch Number": ["B001"]})
    result = loader.validate(df)
    assert "reason" in result.columns
    assert "batch_number" in result.columns


def test_validate_multiple_nulls_reported(loader):
    df = pl.DataFrame(
        {
            "Drug Code": [None, None, "D001"],
            "Adjustment Date": ["2025-01-01", "2025-01-02", "2025-01-03"],
        }
    )
    with pytest.raises(ValueError, match="drug_code has 2 null"):
        loader.validate(df)


# ------------------------------------------------------------------
# LOADER_REGISTRY registration
# ------------------------------------------------------------------


def test_loader_registered():
    from datapulse.bronze.registry import LOADER_REGISTRY

    assert "stock_adjustments" in LOADER_REGISTRY
    assert LOADER_REGISTRY["stock_adjustments"] is ExcelAdjustmentsLoader

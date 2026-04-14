"""Unit tests for ExcelPOLoader."""

from __future__ import annotations

import polars as pl
import pytest

from datapulse.bronze.po_column_map import PO_HEADER_MAP, PO_LINE_MAP
from datapulse.bronze.po_loader import ExcelPOLoader


@pytest.fixture()
def loader(tmp_path):
    return ExcelPOLoader(tmp_path)


class TestExcelPOLoaderMeta:
    def test_target_table(self, loader):
        assert loader.get_target_table() == "bronze.purchase_orders"

    def test_column_maps(self, loader):
        assert "PO Number" in PO_HEADER_MAP
        assert PO_HEADER_MAP["PO Number"] == "po_number"
        assert "Drug Code" in PO_LINE_MAP
        assert PO_LINE_MAP["Drug Code"] == "drug_code"

    def test_registered_in_registry(self):
        from datapulse.bronze.registry import LOADER_REGISTRY

        assert "purchase_orders" in LOADER_REGISTRY
        assert LOADER_REGISTRY["purchase_orders"] is ExcelPOLoader


class TestValidateHeaders:
    def _make_raw_headers(self):
        return pl.DataFrame({
            "PO Number": ["PO-001", "PO-002"],
            "PO Date": ["2025-01-15", "2025-01-16"],
            "Supplier Code": ["SUP001", "SUP002"],
            "Site Code": ["SITE01", "SITE01"],
            "Status": ["draft", "INVALID_STATUS"],
            "source_file": ["test.xlsx", "test.xlsx"],
        })

    def test_renames_header_columns(self, loader):
        raw = self._make_raw_headers()
        result = loader.validate(raw)
        assert "po_number" in result.columns
        assert "supplier_code" in result.columns

    def test_invalid_status_defaults_to_draft(self, loader):
        raw = self._make_raw_headers()
        result = loader.validate(raw)
        statuses = result["status"].to_list()
        assert all(s == "draft" for s in statuses)

    def test_no_columns_raises(self, loader):
        raw = pl.DataFrame({"UNKNOWN": ["value"]})
        with pytest.raises(ValueError, match="No whitelisted columns"):
            loader.validate(raw)


class TestValidateLines:
    def _make_raw_lines(self):
        return pl.DataFrame({
            "PO Number": ["PO-001", "PO-001"],
            "Line Number": [1, 2],
            "Drug Code": ["DRUG001", "DRUG002"],
            "Ordered Quantity": [10.0, -5.0],  # negative should be clipped to 0
            "Unit Price": [5.50, 3.25],
            "Received Quantity": [0.0, 0.0],
        })

    def test_renames_line_columns(self, loader):
        raw = self._make_raw_lines()
        result = loader.validate_lines(raw)
        assert "drug_code" in result.columns
        assert "ordered_quantity" in result.columns

    def test_negative_quantity_clipped_to_zero(self, loader):
        raw = self._make_raw_lines()
        result = loader.validate_lines(raw)
        quantities = result["ordered_quantity"].to_list()
        assert all(q >= 0 for q in quantities)

    def test_no_columns_raises(self, loader):
        raw = pl.DataFrame({"UNKNOWN": ["value"]})
        with pytest.raises(ValueError, match="No whitelisted columns"):
            loader.validate_lines(raw)


class TestDiscover:
    def test_discovers_xlsx_files(self, loader, tmp_path):
        (tmp_path / "po_2025.xlsx").touch()
        (tmp_path / "notes.txt").touch()
        files = loader.discover()
        assert len(files) == 1

    def test_empty_dir_returns_empty_list(self, loader):
        assert loader.discover() == []

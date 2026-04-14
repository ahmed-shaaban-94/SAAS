"""Unit tests for ExcelSuppliersLoader."""

from __future__ import annotations

import polars as pl
import pytest

from datapulse.bronze.suppliers_loader import ExcelSuppliersLoader


@pytest.fixture()
def loader(tmp_path):
    return ExcelSuppliersLoader(tmp_path)


class TestExcelSuppliersLoaderMeta:
    def test_target_table(self, loader):
        assert loader.get_target_table() == "bronze.suppliers"

    def test_column_map(self, loader):
        cm = loader.get_column_map()
        assert "Supplier Code" in cm
        assert cm["Supplier Code"] == "supplier_code"
        assert cm["Active"] == "is_active"

    def test_allowed_columns_include_tenant(self, loader):
        allowed = loader.get_allowed_columns()
        assert "tenant_id" in allowed
        assert "supplier_code" in allowed
        assert "supplier_name" in allowed

    def test_registered_in_registry(self):
        from datapulse.bronze.registry import LOADER_REGISTRY

        assert "suppliers" in LOADER_REGISTRY
        assert LOADER_REGISTRY["suppliers"] is ExcelSuppliersLoader


class TestValidate:
    def _make_raw_df(self):
        return pl.DataFrame({
            "Supplier Code": ["SUP001", "SUP002"],
            "Supplier Name": ["Pharma Co", "MedSupply"],
            "Contact Name": ["John", None],
            "Active": ["true", "false"],
            "Payment Terms (Days)": [30, 45],
            "Lead Time (Days)": [7, 14],
        })

    def test_renames_columns(self, loader):
        raw = self._make_raw_df()
        result = loader.validate(raw)
        assert "supplier_code" in result.columns
        assert "is_active" in result.columns
        assert "Supplier Code" not in result.columns

    def test_is_active_coercion_true(self, loader):
        raw = pl.DataFrame({
            "Supplier Code": ["S1"],
            "Supplier Name": ["Test"],
            "Active": ["yes"],
        })
        result = loader.validate(raw)
        assert result["is_active"][0] is True

    def test_is_active_coercion_false(self, loader):
        raw = pl.DataFrame({
            "Supplier Code": ["S1"],
            "Supplier Name": ["Test"],
            "Active": ["no"],
        })
        result = loader.validate(raw)
        assert result["is_active"][0] is False

    def test_only_allowed_columns_returned(self, loader):
        raw = pl.DataFrame({
            "Supplier Code": ["S1"],
            "Supplier Name": ["Test"],
            "SECRET_COLUMN": ["hack"],
        })
        result = loader.validate(raw)
        assert "SECRET_COLUMN" not in result.columns

    def test_no_columns_raises(self, loader):
        raw = pl.DataFrame({"UNKNOWN": ["value"]})
        with pytest.raises(ValueError, match="No whitelisted columns"):
            loader.validate(raw)


class TestDiscover:
    def test_discovers_xlsx_files(self, loader, tmp_path):
        (tmp_path / "suppliers.xlsx").touch()
        (tmp_path / "other.csv").touch()
        files = loader.discover()
        assert len(files) == 1
        assert files[0].name == "suppliers.xlsx"

    def test_empty_dir_returns_empty_list(self, loader):
        files = loader.discover()
        assert files == []

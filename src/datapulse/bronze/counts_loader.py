"""Excel counts loader — loads inventory count records into bronze.inventory_counts."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from datapulse.bronze.base_loader import BronzeLoader
from datapulse.bronze.counts_column_map import COLUMN_MAP
from datapulse.bronze.registry import LOADER_REGISTRY
from datapulse.logging import get_logger

log = get_logger(__name__)

ALLOWED_COLUMNS: frozenset[str] = frozenset(COLUMN_MAP.values()) | {
    "source_file",
    "loaded_at",
    "tenant_id",
}


class ExcelCountsLoader(BronzeLoader):
    """Loads physical inventory count records from Excel into bronze.inventory_counts.

    Follows the template method pattern from BronzeLoader:
    discover() -> read() -> validate() -> (run() inserts to DB)
    """

    def __init__(self, source_dir: Path) -> None:
        self._source_dir = source_dir

    def get_target_table(self) -> str:
        return "bronze.inventory_counts"

    def get_column_map(self) -> dict[str, str]:
        return COLUMN_MAP

    def get_allowed_columns(self) -> frozenset[str]:
        return ALLOWED_COLUMNS

    def discover(self) -> list[Path]:
        """Find all .xlsx files in source directory, path-traversal safe."""
        resolved_root = self._source_dir.resolve()
        files: list[Path] = []
        for f in sorted(self._source_dir.rglob("*.xlsx")):
            resolved = f.resolve()
            if resolved.is_relative_to(resolved_root):
                files.append(f)
        if not files:
            raise FileNotFoundError(f"No .xlsx files found in {self._source_dir}")
        return files

    def read(self, source: Path) -> pl.DataFrame:
        """Read a single Excel file using calamine engine; add source_file lineage."""
        log.info("reading_counts_file", file=source.name)
        df = pl.read_excel(source, engine="calamine")
        return df.with_columns(pl.lit(source.name).alias("source_file"))

    def validate(self, df: pl.DataFrame) -> pl.DataFrame:
        """Rename columns from Excel headers to DB names; enforce required fields."""
        col_map = self.get_column_map()
        rename_map = {k: v for k, v in col_map.items() if k in df.columns}
        df = df.rename(rename_map)

        missing = {"drug_code", "count_date"} - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns after rename: {sorted(missing)}")

        null_count = df.filter(pl.col("drug_code").is_null()).shape[0]
        if null_count > 0:
            raise ValueError(f"drug_code has {null_count} null value(s) — cannot load")

        return df


LOADER_REGISTRY["inventory_counts"] = ExcelCountsLoader

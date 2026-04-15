"""Excel batches loader — loads batch/lot records into bronze.batches."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from datapulse.bronze.base_loader import BronzeLoader
from datapulse.bronze.batches_column_map import COLUMN_MAP
from datapulse.bronze.registry import LOADER_REGISTRY
from datapulse.logging import get_logger

log = get_logger(__name__)

ALLOWED_COLUMNS: frozenset[str] = frozenset(COLUMN_MAP.values()) | {
    "source_file",
    "loaded_at",
    "tenant_id",
}


class ExcelBatchesLoader(BronzeLoader):
    """Loads batch/lot records from Excel files into bronze.batches."""

    def __init__(self, source_dir: Path) -> None:
        self._source_dir = source_dir

    def get_target_table(self) -> str:
        return "bronze.batches"

    def get_column_map(self) -> dict[str, str]:
        return COLUMN_MAP

    def get_allowed_columns(self) -> frozenset[str]:
        return ALLOWED_COLUMNS

    def discover(self) -> list[Path]:
        """Find all .xlsx files in source directory, path-traversal safe."""
        resolved_root = self._source_dir.resolve()
        files: list[Path] = []
        for file_path in sorted(self._source_dir.rglob("*.xlsx")):
            resolved = file_path.resolve()
            if resolved.is_relative_to(resolved_root):
                files.append(file_path)
        if not files:
            raise FileNotFoundError(f"No .xlsx files found in {self._source_dir}")
        return files

    def read(self, source: Path) -> pl.DataFrame:
        """Read a single Excel file using calamine engine; add source_file lineage."""
        log.info("reading_batches_file", file=source.name)
        df = pl.read_excel(source, engine="calamine")
        return df.with_columns(pl.lit(source.name).alias("source_file"))

    def validate(self, df: pl.DataFrame) -> pl.DataFrame:
        """Rename columns from Excel headers to DB names; enforce required fields."""
        rename_map = {k: v for k, v in self.get_column_map().items() if k in df.columns}
        df = df.rename(rename_map)

        missing = {"drug_code", "batch_number", "expiry_date"} - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns after rename: {sorted(missing)}")

        required_nulls = df.filter(
            pl.any_horizontal(
                pl.col("drug_code").is_null(),
                pl.col("batch_number").is_null(),
                pl.col("expiry_date").is_null(),
            )
        ).shape[0]
        if required_nulls > 0:
            raise ValueError(
                "drug_code, batch_number, and expiry_date must be present for every row"
            )

        return df


LOADER_REGISTRY["batches"] = ExcelBatchesLoader

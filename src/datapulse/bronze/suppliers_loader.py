"""Bronze loader: Excel supplier directory -> bronze.suppliers.

Reads an Excel file with a single sheet of supplier records and
loads them into the bronze.suppliers table.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
import structlog

from datapulse.bronze.base_loader import BronzeLoader
from datapulse.bronze.registry import LOADER_REGISTRY
from datapulse.bronze.suppliers_column_map import COLUMN_MAP

logger = structlog.get_logger(__name__)

_ALLOWED_COLUMNS: frozenset[str] = frozenset(COLUMN_MAP.values()) | {"source_file", "tenant_id"}

_VALID_BOOL_TRUE = frozenset({"true", "yes", "1", "active", "y"})
_VALID_BOOL_FALSE = frozenset({"false", "no", "0", "inactive", "n"})


class ExcelSuppliersLoader(BronzeLoader):
    """Load supplier data from Excel files into bronze.suppliers.

    Expects a single-sheet Excel file with the columns defined in
    ``suppliers_column_map.COLUMN_MAP``.  Multiple files in the
    directory are concatenated before loading.

    Usage::

        result = ExcelSuppliersLoader(Path("/app/data/raw/suppliers")).run(engine, tenant_id=1)
    """

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = Path(data_dir)

    # ── BronzeLoader hooks ────────────────────────────────────

    def discover(self) -> list[Path]:
        """Discover all .xlsx files in data_dir (non-recursive)."""
        resolved_root = self._data_dir.resolve()
        files: list[Path] = []
        for f in sorted(self._data_dir.glob("*.xlsx")):
            resolved = f.resolve()
            if not resolved.is_relative_to(resolved_root):
                logger.warning("path_traversal_blocked", file=str(f))
                continue
            files.append(f)
        logger.info("suppliers_discover", count=len(files), dir=str(self._data_dir))
        return files

    def read(self, source: Any) -> pl.DataFrame:
        """Read a single Excel file into a Polars DataFrame."""
        path = Path(source)
        logger.info("suppliers_read", file=path.name)
        df = pl.read_excel(path, engine="calamine")
        return df.with_columns(pl.lit(path.name).alias("source_file"))

    def validate(self, df: pl.DataFrame) -> pl.DataFrame:
        """Rename columns, coerce types, and filter to allowed columns."""
        # Rename using column map (only renames columns that exist)
        rename_map = {k: v for k, v in self.get_column_map().items() if k in df.columns}
        df = df.rename(rename_map)

        # Coerce is_active to boolean
        if "is_active" in df.columns:
            df = df.with_columns(
                pl.col("is_active")
                .cast(pl.Utf8, strict=False)
                .str.to_lowercase()
                .map_elements(
                    lambda v: True if v in _VALID_BOOL_TRUE else v not in _VALID_BOOL_FALSE,
                    return_dtype=pl.Boolean,
                )
                .alias("is_active")
            )

        # Coerce numeric columns
        for col in ("payment_terms_days", "lead_time_days"):
            if col in df.columns:
                df = df.with_columns(pl.col(col).cast(pl.Int64, strict=False))

        # Filter to allowed columns only
        allowed = self.get_allowed_columns()
        cols = [c for c in df.columns if c in allowed]
        if not cols:
            raise ValueError("No whitelisted columns found in supplier source file")

        return df.select(cols)

    def get_column_map(self) -> dict[str, str]:
        return COLUMN_MAP

    def get_allowed_columns(self) -> frozenset[str]:
        return _ALLOWED_COLUMNS

    def get_target_table(self) -> str:
        return "bronze.suppliers"


# Register in global loader registry
LOADER_REGISTRY["suppliers"] = ExcelSuppliersLoader

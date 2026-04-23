"""Bronze loader: Excel PO files -> bronze.purchase_orders + bronze.po_lines.

Reads an Excel workbook with two named sheets:
  - "PO Headers" (or first sheet): purchase order headers
  - "PO Lines" (or second sheet): line items

Both sheets are validated and loaded separately into their respective tables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
import structlog
from sqlalchemy import Engine, text

from datapulse.bronze.base_loader import BronzeLoader, LoadResult
from datapulse.bronze.po_column_map import PO_HEADER_MAP, PO_LINE_MAP
from datapulse.bronze.registry import LOADER_REGISTRY

logger = structlog.get_logger(__name__)

_ALLOWED_HEADER_COLUMNS: frozenset[str] = frozenset(PO_HEADER_MAP.values()) | {
    "source_file",
    "tenant_id",
}

_ALLOWED_LINE_COLUMNS: frozenset[str] = frozenset(PO_LINE_MAP.values()) | {
    "tenant_id",
}

_VALID_STATUSES = frozenset({"draft", "submitted", "partial", "received", "cancelled"})


class ExcelPOLoader(BronzeLoader):
    """Load purchase order data from Excel files.

    Handles two sheets in a single workbook:
    - Sheet 0 / "PO Headers": loaded to bronze.purchase_orders
    - Sheet 1 / "PO Lines": loaded to bronze.po_lines

    The ``run()`` method is overridden to handle both tables in one pass.

    Usage::

        result = ExcelPOLoader(Path("/app/data/raw/purchase_orders")).run(engine, tenant_id=1)
    """

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = Path(data_dir)

    # ── BronzeLoader hooks ────────────────────────────────────

    def discover(self) -> list[Path]:
        """Discover all .xlsx files in data_dir."""
        resolved_root = self._data_dir.resolve()
        files: list[Path] = []
        for f in sorted(self._data_dir.glob("*.xlsx")):
            resolved = f.resolve()
            if not resolved.is_relative_to(resolved_root):
                logger.warning("path_traversal_blocked", file=str(f))
                continue
            files.append(f)
        logger.info("po_discover", count=len(files), dir=str(self._data_dir))
        return files

    def read(self, source: Any) -> pl.DataFrame:
        """Read the PO header sheet (sheet index 0).

        For line items, use ``read_lines()`` instead.
        """
        path = Path(source)
        df = pl.read_excel(path, engine="calamine", sheet_id=1)
        return df.with_columns(pl.lit(path.name).alias("source_file"))

    def read_lines(self, source: Any) -> pl.DataFrame:
        """Read the PO lines sheet (sheet index 1)."""
        path = Path(source)
        df = pl.read_excel(path, engine="calamine", sheet_id=2)
        return df

    def validate(self, df: pl.DataFrame) -> pl.DataFrame:
        """Validate and clean PO header DataFrame."""
        rename_map = {k: v for k, v in PO_HEADER_MAP.items() if k in df.columns}
        df = df.rename(rename_map)

        # Normalize status
        if "status" in df.columns:
            df = df.with_columns(
                pl.col("status")
                .cast(pl.Utf8, strict=False)
                .str.to_lowercase()
                .map_elements(
                    lambda v: v if v in _VALID_STATUSES else "draft",
                    return_dtype=pl.Utf8,
                )
                .alias("status")
            )

        cols = [c for c in df.columns if c in _ALLOWED_HEADER_COLUMNS]
        if not cols:
            raise ValueError("No whitelisted columns found in PO header sheet")
        return df.select(cols)

    def validate_lines(self, df: pl.DataFrame) -> pl.DataFrame:
        """Validate and clean PO line items DataFrame."""
        rename_map = {k: v for k, v in PO_LINE_MAP.items() if k in df.columns}
        df = df.rename(rename_map)

        # Ensure non-negative quantities
        for col in ("ordered_quantity", "received_quantity"):
            if col in df.columns:
                df = df.with_columns(
                    pl.col(col)
                    .cast(pl.Float64, strict=False)
                    .fill_null(0)
                    .clip(lower_bound=0)
                    .alias(col)
                )

        if "unit_price" in df.columns:
            df = df.with_columns(
                pl.col("unit_price").cast(pl.Float64, strict=False).fill_null(0).alias("unit_price")
            )

        if "line_number" in df.columns:
            df = df.with_columns(pl.col("line_number").cast(pl.Int64, strict=False))

        cols = [c for c in df.columns if c in _ALLOWED_LINE_COLUMNS]
        if not cols:
            raise ValueError("No whitelisted columns found in PO lines sheet")
        return df.select(cols)

    def get_column_map(self) -> dict[str, str]:
        return PO_HEADER_MAP

    def get_allowed_columns(self) -> frozenset[str]:
        return _ALLOWED_HEADER_COLUMNS

    def get_target_table(self) -> str:
        return "bronze.purchase_orders"

    # ── Override run() to handle two tables ──────────────────

    def run(
        self,
        engine: Engine,
        batch_size: int = 50_000,
        tenant_id: int = 1,
    ) -> LoadResult:
        """Load both PO headers and PO lines from each discovered file."""
        sources = self.discover()
        total_loaded = 0
        total_skipped = 0
        errors: list[str] = []

        for source in sources:
            path = Path(source)
            # --- Load PO headers ---
            try:
                raw_headers = self.read(source)
                headers_df = self.validate(raw_headers)
            except Exception as exc:
                errors.append(f"{path.name} (headers): {exc}")
                logger.warning("po_loader_header_error", file=path.name, error=str(exc))
                continue

            headers_df = headers_df.with_columns(pl.lit(tenant_id).alias("tenant_id"))
            header_cols = [c for c in headers_df.columns if c in _ALLOWED_HEADER_COLUMNS]
            headers_df = headers_df.select(header_cols)

            col_list = ", ".join(headers_df.columns)
            placeholders = ", ".join(f":{c}" for c in headers_df.columns)
            insert_headers = (
                f"INSERT INTO bronze.purchase_orders ({col_list}) VALUES ({placeholders})"  # noqa: S608
                " ON CONFLICT (tenant_id, po_number) DO NOTHING"
            )

            with engine.begin() as conn:
                conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
                rows = headers_df.to_dicts()
                for i in range(0, len(rows), batch_size):
                    conn.execute(text(insert_headers), rows[i : i + batch_size])
            total_loaded += len(rows)

            # --- Load PO lines ---
            try:
                raw_lines = self.read_lines(source)
                lines_df = self.validate_lines(raw_lines)
            except Exception as exc:
                errors.append(f"{path.name} (lines): {exc}")
                logger.warning("po_loader_lines_error", file=path.name, error=str(exc))
                continue

            lines_df = lines_df.with_columns(pl.lit(tenant_id).alias("tenant_id"))
            line_cols = [c for c in lines_df.columns if c in _ALLOWED_LINE_COLUMNS]
            lines_df = lines_df.select(line_cols)

            col_list = ", ".join(lines_df.columns)
            placeholders = ", ".join(f":{c}" for c in lines_df.columns)
            insert_lines = (
                f"INSERT INTO bronze.po_lines ({col_list}) VALUES ({placeholders})"  # noqa: S608
                " ON CONFLICT (tenant_id, po_number, line_number) DO NOTHING"
            )

            with engine.begin() as conn:
                conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
                line_rows = lines_df.to_dicts()
                for i in range(0, len(line_rows), batch_size):
                    conn.execute(text(insert_lines), line_rows[i : i + batch_size])
            total_loaded += len(line_rows)

        return LoadResult(
            source_type="excel",
            table_name="bronze.purchase_orders+bronze.po_lines",
            rows_loaded=total_loaded,
            rows_skipped=total_skipped,
            errors=tuple(errors),
        )


# Register in global loader registry
LOADER_REGISTRY["purchase_orders"] = ExcelPOLoader

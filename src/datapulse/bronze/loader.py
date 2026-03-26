"""Bronze loader — Excel files -> Polars concat -> Parquet -> PostgreSQL.

Usage:
    python -m datapulse.bronze.loader --source "E:/Data Analysis/sales/RAW FULL"
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import create_engine, text

from datapulse.bronze.column_map import COLUMN_MAP
from datapulse.config import settings
from datapulse.utils.logging import get_logger

log = get_logger(__name__)


def discover_files(source_dir: Path) -> list[Path]:
    """Find all .xlsx files in the source directory, sorted by name."""
    files = sorted(source_dir.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError(f"No .xlsx files found in {source_dir}")
    log.info("discovered_files", count=len(files), dir=str(source_dir))
    return files


def extract_quarter(filename: str) -> str:
    """Extract quarter identifier from filename like 'Q1.2023.xlsx' -> 'Q1.2023'."""
    match = re.match(r"(Q\d\.\d{4})", filename)
    if match:
        return match.group(1)
    return Path(filename).stem


def read_and_concat(files: list[Path]) -> pl.DataFrame:
    """Read all Excel files and concatenate into a single DataFrame.

    Adds source_file and source_quarter columns for lineage tracking.
    """
    frames: list[pl.DataFrame] = []

    for file_path in files:
        log.info("reading_file", file=file_path.name)
        t0 = time.perf_counter()

        df = pl.read_excel(file_path, engine="calamine")

        # Add source tracking columns
        df = df.with_columns(
            pl.lit(file_path.name).alias("source_file"),
            pl.lit(extract_quarter(file_path.name)).alias("source_quarter"),
        )

        elapsed = time.perf_counter() - t0
        log.info("file_read", file=file_path.name, rows=df.shape[0], seconds=round(elapsed, 2))
        frames.append(df)

    combined = pl.concat(frames, how="diagonal_relaxed")
    log.info("concat_complete", total_rows=combined.shape[0], total_cols=combined.shape[1])
    return combined


def rename_columns(df: pl.DataFrame) -> pl.DataFrame:
    """Rename Excel headers to snake_case DB column names."""
    rename_map = {excel: db for excel, db in COLUMN_MAP.items() if excel in df.columns}
    return df.rename(rename_map)


def save_parquet(df: pl.DataFrame, output_path: Path) -> Path:
    """Save DataFrame as Parquet using PyArrow for optimal compression."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    arrow_table = df.to_arrow()
    pq.write_table(
        arrow_table,
        output_path,
        compression="snappy",
        row_group_size=100_000,
    )

    size_mb = output_path.stat().st_size / (1024 * 1024)
    log.info("parquet_saved", path=str(output_path), size_mb=round(size_mb, 1))
    return output_path


def load_to_postgres(df: pl.DataFrame, database_url: str, batch_size: int) -> int:
    """Load DataFrame into bronze.sales table using batched inserts via PyArrow."""
    engine = create_engine(database_url)

    # Get the DB column names (excluding id, loaded_at which are auto-generated)
    db_columns = [col for col in df.columns if col not in ("id", "loaded_at")]
    df_to_load = df.select(db_columns)

    total_rows = df_to_load.shape[0]
    loaded = 0

    log.info("loading_to_postgres", total_rows=total_rows, batch_size=batch_size)

    with engine.begin() as conn:
        for offset in range(0, total_rows, batch_size):
            batch = df_to_load.slice(offset, batch_size)

            # Convert to list of dicts for executemany
            cols = batch.columns
            placeholders = ", ".join(f":{c}" for c in cols)
            col_names = ", ".join(cols)
            insert_sql = text(f"INSERT INTO bronze.sales ({col_names}) VALUES ({placeholders})")

            rows_dicts = batch.to_dicts()
            conn.execute(insert_sql, rows_dicts)

            loaded += len(rows_dicts)
            log.info(
                "batch_loaded",
                loaded=loaded,
                total=total_rows,
                pct=round(loaded / total_rows * 100, 1),
            )

    log.info("load_complete", total_loaded=loaded)
    return loaded


def run_migration(database_url: str) -> None:
    """Run the bronze schema migration."""
    migration_path = Path(__file__).parent.parent.parent.parent / "migrations" / "001_create_bronze_schema.sql"
    if not migration_path.exists():
        log.warning("migration_not_found", path=str(migration_path))
        return

    engine = create_engine(database_url)
    sql = migration_path.read_text(encoding="utf-8")

    with engine.begin() as conn:
        conn.execute(text(sql))

    log.info("migration_applied", file=migration_path.name)


def run(
    source_dir: Path,
    database_url: str | None = None,
    parquet_path: Path | None = None,
    batch_size: int | None = None,
    skip_db: bool = False,
) -> pl.DataFrame:
    """Full bronze pipeline: Excel -> concat -> Parquet -> PostgreSQL.

    Args:
        source_dir: Directory containing .xlsx files.
        database_url: PostgreSQL connection string (defaults to settings).
        parquet_path: Where to save the Parquet file (defaults to settings).
        batch_size: Rows per insert batch (defaults to settings).
        skip_db: If True, only create Parquet without loading to DB.

    Returns:
        The concatenated DataFrame.
    """
    db_url = database_url or settings.database_url
    pq_path = parquet_path or settings.parquet_dir / "bronze_sales.parquet"
    bs = batch_size or settings.bronze_batch_size

    t0 = time.perf_counter()

    # 1. Read & concat
    files = discover_files(source_dir)
    df = read_and_concat(files)

    # 2. Rename columns
    df = rename_columns(df)

    # 3. Save Parquet
    save_parquet(df, pq_path)

    # 4. Load to PostgreSQL
    if not skip_db:
        run_migration(db_url)
        load_to_postgres(df, db_url, bs)

    elapsed = time.perf_counter() - t0
    log.info("pipeline_complete", rows=df.shape[0], elapsed_seconds=round(elapsed, 1))

    return df


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Load Excel sales data into bronze layer")
    parser.add_argument("--source", required=True, help="Directory with .xlsx files")
    parser.add_argument("--db-url", default=None, help="PostgreSQL URL (default: from .env)")
    parser.add_argument("--parquet", default=None, help="Output Parquet path")
    parser.add_argument("--batch-size", type=int, default=None, help="Insert batch size")
    parser.add_argument("--skip-db", action="store_true", help="Only create Parquet, skip DB load")
    args = parser.parse_args()

    run(
        source_dir=Path(args.source),
        database_url=args.db_url,
        parquet_path=Path(args.parquet) if args.parquet else None,
        batch_size=args.batch_size,
        skip_db=args.skip_db,
    )


if __name__ == "__main__":
    main()

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
import pyarrow.parquet as pq
from sqlalchemy import Engine, create_engine, text

from datapulse.bronze.column_map import COLUMN_MAP
from datapulse.config import get_settings
from datapulse.logging import get_logger

log = get_logger(__name__)

# Whitelist of columns allowed in INSERT statements — derived from COLUMN_MAP
# plus the two lineage columns added at read time.
ALLOWED_COLUMNS: frozenset[str] = frozenset(COLUMN_MAP.values()) | {
    "source_file",
    "source_quarter",
}


def _validate_columns(columns: list[str]) -> None:
    """Raise ValueError if any column name is not in ALLOWED_COLUMNS.

    Prevents SQL injection through f-string column name interpolation.
    """
    unknown = [c for c in columns if c not in ALLOWED_COLUMNS]
    if unknown:
        raise ValueError(f"Column name(s) not in whitelist and cannot be used in SQL: {unknown}")


def discover_files(source_dir: Path) -> list[Path]:
    """Find all .xlsx files in the source directory, sorted by name.

    Validates that every discovered file resolves within the source directory
    to prevent path traversal via symlinks.
    """
    resolved_root = source_dir.resolve()
    files: list[Path] = []
    for f in sorted(source_dir.rglob("*.xlsx")):
        resolved = f.resolve()
        if not resolved.is_relative_to(resolved_root):
            log.warning("path_traversal_blocked", file=str(f), resolved=str(resolved))
            continue
        files.append(f)
    if not files:
        raise FileNotFoundError(f"No .xlsx files found in {source_dir} (searched recursively)")
    log.info("discovered_files", count=len(files), dir=str(source_dir))
    return files


def extract_quarter(filename: str) -> str:
    """Extract quarter identifier from filename like 'Q1.2023.xlsx' -> 'Q1.2023'."""
    match = re.match(r"(Q\d\.\d{4})", filename)
    if match:
        return match.group(1)
    return Path(filename).stem


def read_single_file(file_path: Path) -> pl.DataFrame:
    """Read a single Excel file and add lineage tracking columns.

    Raises on read failure so callers can decide per-file error policy.
    """
    log.info("reading_file", file=file_path.name)
    t0 = time.perf_counter()

    df = pl.read_excel(file_path, engine="calamine")

    # Add source tracking columns
    df = df.with_columns(
        pl.lit(file_path.name).alias("source_file"),
        pl.lit(extract_quarter(file_path.name)).alias("source_quarter"),
    )

    elapsed = time.perf_counter() - t0
    log.info(
        "file_read",
        file=file_path.name,
        rows=df.shape[0],
        seconds=round(elapsed, 2),
    )
    return df


def read_and_concat(files: list[Path]) -> pl.DataFrame:
    """Read all Excel files and concatenate into a single DataFrame.

    Adds source_file and source_quarter columns for lineage tracking.
    Skips malformed files with a warning (fails if ALL files fail).
    """
    frames: list[pl.DataFrame] = []
    errors: list[tuple[str, str]] = []

    for file_path in files:
        try:
            df = read_single_file(file_path)
            frames.append(df)
        except Exception as exc:
            log.error("file_read_failed", file=file_path.name, error=str(exc))
            errors.append((file_path.name, str(exc)))

    if not frames:
        error_summary = "; ".join(f"{name}: {err}" for name, err in errors)
        raise ValueError(f"All {len(errors)} file(s) failed to read: {error_summary}")

    if errors:
        log.warning(
            "partial_read",
            failed_count=len(errors),
            success_count=len(frames),
            failed_files=[name for name, _ in errors],
        )

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


def load_to_postgres(df: pl.DataFrame, engine: Engine, batch_size: int) -> int:
    """Load DataFrame into bronze.sales table using batched inserts via PyArrow.

    Args:
        df: DataFrame with columns already renamed to DB names.
        engine: Shared SQLAlchemy engine (created and disposed by caller).
        batch_size: Number of rows per insert batch.

    Returns:
        Total number of rows inserted.
    """
    # Exclude auto-generated columns
    db_columns = [col for col in df.columns if col not in ("id", "loaded_at")]
    df_to_load = df.select(db_columns)

    # Reject any column not in the whitelist before touching SQL
    _validate_columns(db_columns)

    total_rows = df_to_load.shape[0]
    loaded = 0

    log.info("loading_to_postgres", total_rows=total_rows, batch_size=batch_size)

    with engine.begin() as conn:
        # Pre-compute INSERT template from validated columns (not per-batch)
        placeholders = ", ".join(f":{c}" for c in db_columns)
        col_names = ", ".join(db_columns)
        insert_sql = text(
            f"INSERT INTO bronze.sales ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        )

        for offset in range(0, total_rows, batch_size):
            batch = df_to_load.slice(offset, batch_size)
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


def run_migrations(engine: Engine) -> None:
    """Run all pending SQL migrations in sorted order.

    Ensures the schema_migrations tracking table exists first (via 000 bootstrap),
    then executes each .sql file in the migrations/ directory that has not yet
    been recorded in public.schema_migrations.

    Args:
        engine: Shared SQLAlchemy engine (created and disposed by caller).
    """
    migrations_dir = Path(__file__).parent.parent.parent.parent / "migrations"
    if not migrations_dir.is_dir():
        log.warning("migrations_dir_not_found", path=str(migrations_dir))
        return

    # --- Step 1: Bootstrap the tracking table (000) ---
    bootstrap = migrations_dir / "000_create_schema_migrations.sql"
    if bootstrap.exists():
        try:
            with engine.begin() as conn:
                conn.execute(text(bootstrap.read_text(encoding="utf-8")))
        except Exception:
            log.exception("migration_failed", file=bootstrap.name)
            raise

    # --- Step 2: Discover and run pending migrations ---
    migration_files = sorted(migrations_dir.glob("*.sql"))

    for mig in migration_files:
        try:
            with engine.begin() as conn:
                # Check if already applied
                result = conn.execute(
                    text("SELECT 1 FROM public.schema_migrations WHERE filename = :fn"),
                    {"fn": mig.name},
                )
                if result.fetchone() is not None:
                    log.info("migration_skipped", file=mig.name, reason="already applied")
                    continue

                # Execute the migration
                sql = mig.read_text(encoding="utf-8")
                conn.execute(text(sql))

                # Record it
                conn.execute(
                    text("INSERT INTO public.schema_migrations (filename) VALUES (:fn)"),
                    {"fn": mig.name},
                )
        except Exception:
            log.exception("migration_failed", file=mig.name)
            raise

        log.info("migration_applied", file=mig.name)


def _create_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine with safe pool and timeout settings."""
    return create_engine(
        database_url,
        pool_size=2,
        max_overflow=0,
        pool_timeout=30,
        connect_args={"options": "-c statement_timeout=300000"},
    )


def run(
    source_dir: Path,
    database_url: str | None = None,
    parquet_path: Path | None = None,
    batch_size: int | None = None,
    skip_db: bool = False,
    files_per_chunk: int = 4,
) -> pl.DataFrame:
    """Full bronze pipeline: Excel -> concat -> Parquet -> PostgreSQL.

    Files are processed in chunks of ``files_per_chunk`` to limit peak memory
    usage. Each chunk is read, renamed, and loaded to PostgreSQL before the
    next chunk starts. The full DataFrame is still returned for downstream use,
    but memory pressure during the load phase is bounded.

    Args:
        source_dir: Directory containing .xlsx files.
        database_url: PostgreSQL connection string (defaults to settings).
        parquet_path: Where to save the Parquet file (defaults to settings).
        batch_size: Rows per insert batch (defaults to settings).
        skip_db: If True, only create Parquet without loading to DB.
        files_per_chunk: Number of Excel files to process together (default 4).
            Lower values reduce peak memory; higher values reduce DB round-trips.

    Returns:
        The concatenated DataFrame.
    """
    db_url = database_url or get_settings().database_url
    pq_path = parquet_path or get_settings().parquet_dir / "bronze_sales.parquet"
    bs = batch_size or get_settings().bronze_batch_size

    t0 = time.perf_counter()

    # 1. Discover files
    files = discover_files(source_dir)

    engine = None
    if not skip_db:
        engine = _create_engine(db_url)
        try:
            run_migrations(engine)
        except Exception:
            engine.dispose()
            raise

    # 2. Process in chunks to limit peak memory
    all_frames: list[pl.DataFrame] = []
    total_loaded = 0

    try:
        for chunk_start in range(0, len(files), files_per_chunk):
            chunk_files = files[chunk_start : chunk_start + files_per_chunk]
            log.info(
                "processing_chunk",
                chunk=chunk_start // files_per_chunk + 1,
                files=[f.name for f in chunk_files],
            )

            chunk_df = read_and_concat(chunk_files)
            chunk_df = rename_columns(chunk_df)
            all_frames.append(chunk_df)

            if engine is not None:
                total_loaded += load_to_postgres(chunk_df, engine, bs)

        # 3. Combine all chunks for Parquet and return value
        df = pl.concat(all_frames, how="diagonal_relaxed") if len(all_frames) > 1 else all_frames[0]

        # 4. Save Parquet (full dataset)
        save_parquet(df, pq_path)

    finally:
        if engine is not None:
            engine.dispose()

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

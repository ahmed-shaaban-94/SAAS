"""Core file reader — CSV/Excel to Polars DataFrame."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from datapulse.config import get_settings
from datapulse.import_pipeline.models import FileFormat, ImportConfig, ImportResult
from datapulse.import_pipeline.type_detector import detect_column_types
from datapulse.import_pipeline.validator import ValidationError, validate_file
from datapulse.logging import get_logger

log = get_logger(__name__)


def read_csv(
    path: Path,
    encoding: str = "utf-8",
    delimiter: str = ",",
    has_header: bool = True,
) -> pl.DataFrame:
    """Read a CSV file into a Polars DataFrame."""
    try:
        df = pl.read_csv(
            path,
            encoding=encoding,
            separator=delimiter,
            has_header=has_header,
            infer_schema_length=1000,
            try_parse_dates=True,
        )
    except Exception as e:
        # Retry with latin-1 if utf-8 fails
        if encoding == "utf-8":
            log.warning("utf8_failed_retrying_latin1", path=str(path), error=str(e))
            df = pl.read_csv(
                path,
                encoding="latin-1",
                separator=delimiter,
                has_header=has_header,
                infer_schema_length=1000,
                try_parse_dates=True,
            )
        else:
            raise

    return df


def read_excel(
    path: Path,
    sheet_name: str | None = None,
) -> pl.DataFrame:
    """Read an Excel file into a Polars DataFrame.

    Uses openpyxl for .xlsx and xlrd for .xls files.
    """
    suffix = path.suffix.lower()
    if suffix == ".xls":
        raise ValidationError(".xls format is not supported. Please convert to .xlsx or .csv.")
    engine = "calamine"

    kwargs: dict[str, object] = {"source": path, "engine": engine}
    if sheet_name is not None:
        kwargs["sheet_name"] = sheet_name

    return pl.read_excel(**kwargs)  # type: ignore[call-overload]


def read_file(
    config: ImportConfig | Path | str,
) -> tuple[pl.DataFrame, ImportResult]:
    """Read a file and return the DataFrame with metadata.

    Args:
        config: An ImportConfig, Path, or string path to the file.

    Returns:
        Tuple of (DataFrame, ImportResult).

    Raises:
        ValidationError: If the file fails validation.
    """
    if isinstance(config, (str, Path)):
        config = ImportConfig(file_path=Path(config))

    path = config.file_path
    file_format = validate_file(path)

    log.info("reading_file", path=str(path), format=file_format.value)

    if file_format == FileFormat.CSV:
        df = read_csv(
            path,
            encoding=config.encoding,
            delimiter=config.delimiter,
            has_header=config.has_header,
        )
    else:
        df = read_excel(path, sheet_name=config.sheet_name)

    # Enforce limits
    if df.shape[0] > get_settings().max_rows:
        raise ValidationError(f"Too many rows: {df.shape[0]:,} (max {get_settings().max_rows:,})")
    if df.shape[1] > get_settings().max_columns:
        raise ValidationError(f"Too many columns: {df.shape[1]} (max {get_settings().max_columns})")

    columns = detect_column_types(df, sample_size=config.sample_rows)
    file_size = path.stat().st_size

    warnings: list[str] = []
    null_cols = [c.name for c in columns if c.null_count > 0]
    if null_cols:
        warnings.append(f"Columns with nulls: {', '.join(null_cols)}")

    result = ImportResult(
        file_path=path,
        file_format=file_format,
        file_size_bytes=file_size,
        row_count=df.shape[0],
        column_count=df.shape[1],
        columns=columns,
        warnings=warnings,
    )

    log.info(
        "file_read_complete",
        rows=result.row_count,
        columns=result.column_count,
        warnings=len(warnings),
    )

    return df, result

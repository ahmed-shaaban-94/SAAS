"""Auto-detect column types from a Polars DataFrame."""

from __future__ import annotations

import polars as pl

from datapulse.import_pipeline.models import ColumnInfo, DetectedType


_POLARS_TYPE_MAP: dict[type, DetectedType] = {
    pl.Utf8: DetectedType.STRING,
    pl.String: DetectedType.STRING,
    pl.Int8: DetectedType.INTEGER,
    pl.Int16: DetectedType.INTEGER,
    pl.Int32: DetectedType.INTEGER,
    pl.Int64: DetectedType.INTEGER,
    pl.UInt8: DetectedType.INTEGER,
    pl.UInt16: DetectedType.INTEGER,
    pl.UInt32: DetectedType.INTEGER,
    pl.UInt64: DetectedType.INTEGER,
    pl.Float32: DetectedType.FLOAT,
    pl.Float64: DetectedType.FLOAT,
    pl.Boolean: DetectedType.BOOLEAN,
    pl.Date: DetectedType.DATE,
    pl.Datetime: DetectedType.DATE,
}


def _map_polars_type(dtype: pl.DataType) -> DetectedType:
    """Map a Polars dtype to our DetectedType enum."""
    for polars_type, detected in _POLARS_TYPE_MAP.items():
        if isinstance(dtype, polars_type):
            return detected
    return DetectedType.UNKNOWN


def detect_column_types(
    df: pl.DataFrame,
    sample_size: int = 100,
    sample_values_count: int = 5,
) -> list[ColumnInfo]:
    """Analyze a DataFrame and return column metadata.

    Args:
        df: The DataFrame to analyze.
        sample_size: Number of rows to sample for analysis.
        sample_values_count: Number of sample values to include per column.

    Returns:
        List of ColumnInfo with detected types and statistics.
    """
    sampled = df.head(sample_size)
    result: list[ColumnInfo] = []

    for col_name in df.columns:
        col = df[col_name]
        sampled_col = sampled[col_name]

        detected_type = _map_polars_type(col.dtype)

        # Get sample values as strings
        non_null = sampled_col.drop_nulls()
        samples = [str(v) for v in non_null.head(sample_values_count).to_list()]

        result.append(
            ColumnInfo(
                name=col_name,
                detected_type=detected_type,
                null_count=col.null_count(),
                unique_count=col.n_unique(),
                sample_values=samples,
            )
        )

    return result

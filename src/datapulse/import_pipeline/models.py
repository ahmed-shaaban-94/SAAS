"""Pydantic models for import pipeline configuration and results."""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class FileFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"
    XLS = "xls"


class DetectedType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DATE = "date"
    BOOLEAN = "boolean"
    UNKNOWN = "unknown"


class ColumnInfo(BaseModel):
    """Metadata for a single column."""

    name: str
    detected_type: DetectedType
    null_count: int = 0
    unique_count: int = 0
    sample_values: list[str] = Field(default_factory=list)


class ImportConfig(BaseModel):
    """Configuration for importing a file."""

    file_path: Path
    file_format: FileFormat | None = None
    sheet_name: str | None = None
    encoding: str = "utf-8"
    delimiter: str = ","
    has_header: bool = True
    sample_rows: int = 100


class ImportResult(BaseModel):
    """Result metadata from a file import."""

    file_path: Path
    file_format: FileFormat
    file_size_bytes: int
    row_count: int
    column_count: int
    columns: list[ColumnInfo]
    warnings: list[str] = Field(default_factory=list)

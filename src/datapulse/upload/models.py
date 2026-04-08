"""Pydantic models for file upload and preview."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ColumnInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    dtype: str
    null_count: int
    sample_values: list[str]


class PreviewResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_id: str
    filename: str
    row_count: int
    columns: list[ColumnInfo]
    sample_rows: list[list[str]]
    warnings: list[str]


class UploadedFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_id: str
    filename: str
    size_bytes: int
    status: str  # "uploaded", "previewed", "confirmed"

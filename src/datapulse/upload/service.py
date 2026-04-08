"""Upload service for file preview and confirmation."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from datapulse.logging import get_logger
from datapulse.upload.models import ColumnInfo, PreviewResult, UploadedFile

log = get_logger(__name__)

TEMP_DIR = Path("/tmp/datapulse-uploads")  # noqa: S108
ALLOWED_EXTENSIONS = {".xlsx", ".csv", ".xls"}
MAX_PREVIEW_ROWS = 100


class UploadService:
    def __init__(self, raw_data_dir: str = "/app/data/raw/sales") -> None:
        self._raw_dir = Path(raw_data_dir)
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

    def save_temp_file(self, filename: str, content: bytes) -> UploadedFile:
        """Save uploaded file to temp directory, return file metadata."""
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}")

        file_id = str(uuid.uuid4())
        dest = TEMP_DIR / f"{file_id}{ext}"
        dest.write_bytes(content)

        log.info("file_uploaded", file_id=file_id, filename=filename, size=len(content))
        return UploadedFile(
            file_id=file_id,
            filename=filename,
            size_bytes=len(content),
            status="uploaded",
        )

    def preview_file(self, file_id: str) -> PreviewResult:
        """Read first N rows from an uploaded file and return preview."""
        import polars as pl

        matching = list(TEMP_DIR.glob(f"{file_id}.*"))
        if not matching:
            raise FileNotFoundError(f"File {file_id} not found")

        file_path = matching[0]
        ext = file_path.suffix.lower()

        if ext == ".csv":
            df = pl.read_csv(file_path, n_rows=MAX_PREVIEW_ROWS, infer_schema_length=200)
        else:
            df = pl.read_excel(file_path, engine="calamine")
            if df.height > MAX_PREVIEW_ROWS:
                df = df.head(MAX_PREVIEW_ROWS)

        warnings: list[str] = []
        columns = []
        for col in df.columns:
            series = df[col]
            null_count = series.null_count()
            if null_count > df.height * 0.5:
                warnings.append(f"Column '{col}' has >50% nulls ({null_count}/{df.height})")
            sample = [str(v) for v in series.head(3).to_list() if v is not None]
            columns.append(
                ColumnInfo(
                    name=col,
                    dtype=str(series.dtype),
                    null_count=null_count,
                    sample_values=sample,
                )
            )

        sample_rows = [[str(v) if v is not None else "" for v in row] for row in df.head(10).rows()]

        return PreviewResult(
            file_id=file_id,
            filename=file_path.name,
            row_count=df.height,
            columns=columns,
            sample_rows=sample_rows,
            warnings=warnings,
        )

    def confirm_upload(self, file_ids: list[str]) -> list[str]:
        """Move confirmed files to the raw data directory."""
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        moved = []
        for fid in file_ids:
            matching = list(TEMP_DIR.glob(f"{fid}.*"))
            if not matching:
                continue
            src = matching[0]
            dest = self._raw_dir / src.name
            shutil.move(str(src), str(dest))
            moved.append(str(dest))
            log.info("file_confirmed", file_id=fid, destination=str(dest))
        return moved

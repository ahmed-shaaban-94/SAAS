"""Upload service for file preview and confirmation."""

from __future__ import annotations

import shutil
import uuid
from collections.abc import AsyncIterable
from contextlib import suppress
from pathlib import Path

from fastapi import HTTPException

from datapulse.logging import get_logger
from datapulse.upload.models import (
    ColumnInfo,
    InventoryPreviewResult,
    PreviewResult,
    UploadedFile,
)

log = get_logger(__name__)

TEMP_DIR = Path("/tmp/datapulse-uploads")  # noqa: S108
ALLOWED_EXTENSIONS = {".xlsx", ".csv", ".xls"}
MAX_PREVIEW_ROWS = 100

# Magic bytes for file type validation
_MAGIC_XLSX = b"PK\x03\x04"  # OOXML (xlsx, docx, zip)
_MAGIC_XLS = b"\xd0\xcf\x11\xe0"  # OLE2 Compound Document (xls, doc)

# ── Inventory file type detection ──────────────────────────────────
# Maps known Excel header sets to loader registry keys.
# Detection works by checking which header set has the most matches.

INVENTORY_HEADER_SIGNATURES: dict[str, frozenset[str]] = {
    "stock_receipts": frozenset(
        {
            "Receipt Date",
            "Receipt Reference",
            "Drug Code",
            "Quantity",
            "Unit Cost",
            "Batch Number",
        }
    ),
    "stock_adjustments": frozenset(
        {
            "Adjustment Date",
            "Adjustment Type",
            "Drug Code",
            "Quantity",
            "Reason",
        }
    ),
    "inventory_counts": frozenset(
        {
            "Count Date",
            "Drug Code",
            "Counted Quantity",
            "Counted By",
        }
    ),
    "batches": frozenset(
        {
            "Drug Code",
            "Batch Number",
            "Expiry Date",
            "Initial Quantity",
            "Current Quantity",
        }
    ),
    "suppliers": frozenset(
        {
            "Supplier Code",
            "Supplier Name",
            "Contact Name",
            "Payment Terms (Days)",
        }
    ),
    "purchase_orders": frozenset(
        {
            "PO Number",
            "PO Date",
            "Supplier Code",
            "Status",
        }
    ),
}

# Minimum fraction of signature headers that must match to accept detection
_MIN_MATCH_RATIO = 0.6


def _validate_magic_bytes(ext: str, content: bytes) -> None:
    """Raise ValueError if content magic bytes don't match the declared extension."""
    if not content:
        raise ValueError("Uploaded file is empty")

    if ext in (".xlsx", ".xls"):
        # Accept both OOXML (.xlsx) and OLE2 (.xls) magic bytes for both extensions
        # since users sometimes rename files
        if not (content[:4] == _MAGIC_XLSX or content[:4] == _MAGIC_XLS):
            raise ValueError(
                f"File declared as {ext} but content does not match Excel format. "
                "Expected XLSX (PK\\x03\\x04) or XLS (OLE2) magic bytes."
            )
    elif ext == ".csv":
        # CSV: first 1 KB must be valid UTF-8 with no null bytes
        sample = content[:1024]
        if b"\x00" in sample:
            raise ValueError("CSV file contains null bytes — likely a binary file")
        try:
            sample.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("CSV file is not valid UTF-8. Upload a UTF-8 encoded CSV.") from exc


def _validate_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}")
    return ext


class UploadService:
    def __init__(self, raw_data_dir: str = "/app/data/raw/sales", tenant_id: str = "0") -> None:
        self._raw_dir = Path(raw_data_dir)
        self._tenant_dir = TEMP_DIR / str(tenant_id)
        self._tenant_dir.mkdir(parents=True, exist_ok=True)

    def _build_upload_target(self, filename: str) -> tuple[str, Path, str]:
        ext = _validate_extension(filename)
        file_id = str(uuid.uuid4())
        dest = self._tenant_dir / f"{file_id}{ext}"
        return file_id, dest, ext

    @staticmethod
    def _build_uploaded_file(file_id: str, filename: str, size_bytes: int) -> UploadedFile:
        return UploadedFile(
            file_id=file_id,
            filename=filename,
            size_bytes=size_bytes,
            status="uploaded",
        )

    def save_temp_file(self, filename: str, content: bytes) -> UploadedFile:
        """Save uploaded file to per-tenant temp directory, return file metadata."""
        file_id, dest, ext = self._build_upload_target(filename)
        _validate_magic_bytes(ext, content)

        dest.write_bytes(content)

        log.info("file_uploaded", file_id=file_id, filename=filename, size=len(content))
        return self._build_uploaded_file(file_id, filename, len(content))

    async def save_temp_file_stream(
        self,
        filename: str,
        chunks: AsyncIterable[bytes],
    ) -> UploadedFile:
        """Stream an upload to disk without buffering the entire file in memory."""
        file_id, dest, ext = self._build_upload_target(filename)
        sample = bytearray()
        total = 0

        try:
            with dest.open("wb") as handle:
                async for chunk in chunks:
                    if not chunk:
                        continue
                    total += len(chunk)
                    if len(sample) < 1024:
                        sample.extend(chunk[: 1024 - len(sample)])
                    handle.write(chunk)

            _validate_magic_bytes(ext, bytes(sample))
        except Exception:
            with suppress(FileNotFoundError):
                dest.unlink()
            raise

        log.info("file_uploaded", file_id=file_id, filename=filename, size=total)
        return self._build_uploaded_file(file_id, filename, total)

    def preview_file(self, file_id: str) -> PreviewResult:
        """Read first N rows from an uploaded file and return preview."""
        import polars as pl

        try:
            normalized_id = str(uuid.UUID(file_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid file ID format") from exc

        matching = list(self._tenant_dir.glob(f"{normalized_id}.*"))
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

    @staticmethod
    def detect_inventory_type(headers: list[str]) -> str | None:
        """Detect inventory file type from Excel/CSV column headers.

        Compares the file's header row against known column-map signatures.
        Returns the loader registry key (e.g. 'stock_receipts') or None.
        """
        header_set = frozenset(headers)
        best_match: str | None = None
        best_score = 0.0

        for file_type, signature in INVENTORY_HEADER_SIGNATURES.items():
            matched = header_set & signature
            if not signature:
                continue
            score = len(matched) / len(signature)
            if score > best_score and score >= _MIN_MATCH_RATIO:
                best_score = score
                best_match = file_type

        return best_match

    def preview_inventory_file(self, file_id: str) -> InventoryPreviewResult:
        """Preview an uploaded file with inventory type detection.

        Reads the file, detects the inventory type from headers, and returns
        preview data with the detected type for user confirmation.
        """
        import polars as pl

        try:
            normalized_id = str(uuid.UUID(file_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid file ID format") from exc

        matching = list(self._tenant_dir.glob(f"{normalized_id}.*"))
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

        detected_type = self.detect_inventory_type(df.columns)
        if detected_type is None:
            raise ValueError(
                "Cannot detect inventory file type from headers. "
                f"Found columns: {df.columns[:10]}. "
                "Expected headers matching stock_receipts, stock_adjustments, "
                "inventory_counts, batches, suppliers, or purchase_orders."
            )

        signature = INVENTORY_HEADER_SIGNATURES[detected_type]
        matched_headers = [h for h in df.columns if h in signature]

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

        log.info(
            "inventory_file_detected",
            file_id=file_id,
            detected_type=detected_type,
            matched_headers=matched_headers,
            row_count=df.height,
        )

        return InventoryPreviewResult(
            file_id=file_id,
            filename=file_path.name,
            detected_type=detected_type,
            row_count=df.height,
            columns=columns,
            sample_rows=sample_rows,
            warnings=warnings,
            matched_headers=matched_headers,
        )

    def confirm_inventory_upload(
        self, file_ids: list[str], target_dir: str | None = None
    ) -> list[str]:
        """Move confirmed inventory files to the appropriate raw data directory.

        Uses a separate directory from sales files to keep data organized.
        """
        raw_dir = Path(target_dir) if target_dir else self._raw_dir.parent / "inventory"
        moved = []
        for fid in file_ids:
            try:
                normalized_fid = str(uuid.UUID(fid))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid file ID format") from exc

            matching = list(self._tenant_dir.glob(f"{normalized_fid}.*"))
            if not matching:
                continue
            raw_dir.mkdir(parents=True, exist_ok=True)
            src = matching[0]
            dest = raw_dir / src.name
            shutil.move(str(src), str(dest))
            moved.append(str(dest))
            log.info("inventory_file_confirmed", file_id=fid, destination=str(dest))
        return moved

    def confirm_upload(self, file_ids: list[str]) -> list[str]:
        """Move confirmed files to the raw data directory."""
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        moved = []
        for fid in file_ids:
            try:
                normalized_fid = str(uuid.UUID(fid))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid file ID format") from exc

            matching = list(self._tenant_dir.glob(f"{normalized_fid}.*"))
            if not matching:
                continue
            src = matching[0]
            dest = self._raw_dir / src.name
            shutil.move(str(src), str(dest))
            moved.append(str(dest))
            log.info("file_confirmed", file_id=fid, destination=str(dest))
        return moved

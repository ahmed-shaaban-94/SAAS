"""FileUploadConnector — implements SourceConnector for file_upload sources.

This connector handles sources backed by a file previously uploaded via the
/upload/files endpoint.  The uploaded file lives in TEMP_DIR/{tenant_id}/.

config_json shape for file_upload connections:
    {
        "file_id":   "uuid-string",          # UUID from UploadService
        "filename":  "sales_q4_2025.csv",    # original name (used for extension)
        "encoding":  "utf-8",                # optional, default utf-8
        "delimiter": ","                     # optional, default comma
    }

IMPORTANT: This connector delegates all file *reading* to
``control_center.preview``, which is the sole module allowed to invoke
``import_pipeline.reader``.  The bronze loader is never imported here.
"""

from __future__ import annotations

import time
from pathlib import Path

from datapulse.control_center.models import ConnectionPreviewResult, ConnectionTestResult
from datapulse.logging import get_logger

log = get_logger(__name__)

# Mirror of upload/service.py TEMP_DIR — kept as a constant to avoid
# importing UploadService (which introduces an unwanted coupling path).
_UPLOAD_TEMP_DIR = Path("/tmp/datapulse-uploads")  # noqa: S108


class FileUploadConnector:
    """Connector for file_upload source type (CSV / Excel files)."""

    def test(self, *, tenant_id: int, config: dict) -> ConnectionTestResult:
        """Check that the uploaded file still exists and is readable."""
        path = _resolve_path(tenant_id, config)
        if path is None:
            return ConnectionTestResult(ok=False, error="config_missing_file_id")
        if not path.exists():
            return ConnectionTestResult(
                ok=False,
                error="file_not_found — re-upload the source file to restore this connection",
            )
        try:
            t0 = time.perf_counter()
            size = path.stat().st_size
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        except OSError as exc:
            return ConnectionTestResult(ok=False, error=f"file_unreadable: {exc}")

        warnings: list[str] = []
        if size == 0:
            warnings.append("file_is_empty")

        log.info("file_upload_connector_test_ok", tenant_id=tenant_id, path=str(path))
        return ConnectionTestResult(ok=True, latency_ms=latency_ms, warnings=warnings)

    def preview(
        self,
        *,
        tenant_id: int,
        config: dict,
        max_rows: int = 1000,
        sample_rows: int = 50,
    ) -> ConnectionPreviewResult:
        """Delegate to the isolated preview engine — never touches bronze."""
        # Lazy import keeps preview.py architecturally isolated from connectors.
        from datapulse.control_center import preview as preview_engine  # noqa: PLC0415

        return preview_engine.preview_file_upload(
            tenant_id,
            config,
            max_rows=max_rows,
            sample_rows=sample_rows,
        )


def _resolve_path(tenant_id: int, config: dict) -> Path | None:
    """Build the temp-file path from tenant_id + config.file_id + extension."""
    file_id = config.get("file_id", "").strip()
    if not file_id:
        return None
    filename = config.get("filename", "")
    ext = Path(filename).suffix.lower() if filename else ".csv"
    return _UPLOAD_TEMP_DIR / str(tenant_id) / f"{file_id}{ext}"

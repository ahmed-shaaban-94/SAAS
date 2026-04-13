"""Preview engine for the Control Center — READ-ONLY file sampling.

Architectural constraint (enforced by code review and graph rules):
  - This module may import from: import_pipeline.reader, import_pipeline.models,
    control_center.models, stdlib, Polars.
  - This module must NEVER import from: bronze.*, bronze.loader,
    or any module that writes to the database.

The preview runs on the *uploaded* temp file and returns column metadata
plus a row sample.  It does not touch the bronze, silver, or gold layers.

Downstream callers:
  service.preview_connection  →  preview.preview_file_upload
  connectors.file_upload.FileUploadConnector.preview  →  preview.preview_file_upload
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from datapulse.control_center.models import ConnectionPreviewResult, PreviewColumn
from datapulse.import_pipeline.models import ImportConfig
from datapulse.import_pipeline.reader import read_file
from datapulse.logging import get_logger

log = get_logger(__name__)

# Mirror of upload/service.py TEMP_DIR — inlined to prevent importing
# the upload module (which is a sibling business module, not a dependency
# of control_center).
_UPLOAD_TEMP_DIR = Path("/tmp/datapulse-uploads")  # noqa: S108


def preview_file_upload(
    tenant_id: int,
    config: dict,
    *,
    max_rows: int = 1000,
    sample_rows: int = 50,
) -> ConnectionPreviewResult:
    """Read a sample of a file_upload source connection.

    Args:
        tenant_id:   Tenant that owns the connection (used to locate temp file).
        config:      The ``config_json`` dict from the SourceConnection.
                     Must contain ``file_id`` and optionally ``filename``,
                     ``encoding``, ``delimiter``.
        max_rows:    Maximum rows to read from the file (caps memory usage).
        sample_rows: Number of rows to include in ``sample_rows`` output.

    Returns:
        ConnectionPreviewResult with columns, sample data, null ratios, warnings.

    Raises:
        FileNotFoundError: When the uploaded file no longer exists.
        ValueError:        When config is missing ``file_id``.
    """
    path = _resolve_path(tenant_id, config)
    log.info("preview_file_upload_start", tenant_id=tenant_id, path=str(path))

    if not path.exists():
        raise FileNotFoundError(
            f"Uploaded file not found at {path}. Re-upload the source file to restore preview."
        )

    cfg = ImportConfig(
        file_path=path,
        encoding=config.get("encoding", "utf-8"),
        delimiter=config.get("delimiter", ","),
        sample_rows=max_rows,
    )

    df, result = read_file(cfg)

    row_count = result.row_count
    sample_df = df.head(min(sample_rows, row_count))

    columns = [
        PreviewColumn(
            source_name=c.name,
            detected_type=c.detected_type.value,
            null_count=c.null_count,
            unique_count=c.unique_count,
            sample_values=c.sample_values,
        )
        for c in result.columns
    ]

    null_ratios = {c.name: round(c.null_count / max(row_count, 1), 4) for c in result.columns}

    raw_rows = sample_df.to_dicts()
    serialized_rows: list[dict[str, Any]] = [
        {k: _safe_json(v) for k, v in row.items()} for row in raw_rows
    ]

    log.info(
        "preview_file_upload_done",
        tenant_id=tenant_id,
        rows=row_count,
        columns=len(columns),
        warnings=len(result.warnings),
    )

    return ConnectionPreviewResult(
        columns=columns,
        sample_rows=serialized_rows,
        row_count_estimate=row_count,
        null_ratios=null_ratios,
        warnings=result.warnings,
    )


# ── Helpers ──────────────────────────────────────────────────


def _resolve_path(tenant_id: int, config: dict) -> Path:
    """Build the upload temp-file path from tenant_id and config."""
    file_id = config.get("file_id", "").strip()
    if not file_id:
        raise ValueError("config.file_id is required for file_upload preview")
    filename = config.get("filename", "")
    ext = Path(filename).suffix.lower() if filename else ".csv"
    return _UPLOAD_TEMP_DIR / str(tenant_id) / f"{file_id}{ext}"


def _safe_json(value: object) -> object:
    """Coerce non-JSON-serializable values (e.g. date, Decimal) to strings."""
    if value is None:
        return None
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)

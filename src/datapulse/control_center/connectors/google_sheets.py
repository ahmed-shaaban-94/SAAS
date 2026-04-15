"""GoogleSheetsConnector — implements SourceConnector for google_sheets sources.

Reads data from a Google Sheet via the Google Sheets API v4, using a
service account key embedded in config_json.

config_json shape:
    {
        "spreadsheet_id":    "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
        "sheet_name":        "Sheet1",          # tab name (default: Sheet1)
        "header_row":        1,                 # 1-based row containing column headers
        "service_account_key": {
            "<google service-account json>": "include the credential fields from the "
            "downloaded key file, such as project identifier, client email, and "
            "private key material"
        }
    }

Security:
  - service_account_key is validated but never logged.
  - preview() returns a copy of data with no credentials attached.
"""

from __future__ import annotations

import time
from typing import Any

from datapulse.control_center.models import (
    ConnectionPreviewResult,
    ConnectionTestResult,
    PreviewColumn,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

_REQUIRED_KEY_FIELDS = {"type", "project_id", "private_key", "client_email"}


def _build_service(service_account_key: dict) -> Any:
    """Construct an authenticated Google Sheets API service object.

    Raises ImportError when google-api-python-client is not installed.
    Raises ValueError for invalid credentials.
    """
    try:
        import google.oauth2.service_account as sa  # noqa: PLC0415
        from googleapiclient.discovery import build  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "google-api-python-client and google-auth are required for the "
            "Google Sheets connector. Install them with: "
            "pip install google-api-python-client google-auth"
        ) from exc

    creds = sa.Credentials.from_service_account_info(
        service_account_key,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _validate_config(config: dict) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    errors: list[str] = []
    if not config.get("spreadsheet_id", "").strip():
        errors.append("config_missing_spreadsheet_id")

    sak = config.get("service_account_key")
    if not isinstance(sak, dict):
        errors.append("config_missing_service_account_key")
    else:
        missing = _REQUIRED_KEY_FIELDS - sak.keys()
        if missing:
            errors.append(f"service_account_key_missing_fields:{','.join(sorted(missing))}")
        if sak.get("type") != "service_account":
            errors.append("service_account_key_wrong_type")

    return errors


class GoogleSheetsConnector:
    """Connector for google_sheets source type."""

    def test(self, *, tenant_id: int, config: dict) -> ConnectionTestResult:
        """Validate credentials and verify the spreadsheet is accessible."""
        errors = _validate_config(config)
        if errors:
            return ConnectionTestResult(ok=False, error=errors[0])

        spreadsheet_id: str = config["spreadsheet_id"].strip()
        sheet_name: str = config.get("sheet_name", "Sheet1")
        sak: dict = config["service_account_key"]

        try:
            t0 = time.perf_counter()
            service = _build_service(sak)

            # Fetch spreadsheet metadata — lightweight, does not download data
            meta = (
                service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id, fields="spreadsheetId,sheets.properties.title")
                .execute()
            )
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        except ImportError as exc:
            return ConnectionTestResult(ok=False, error=str(exc))
        except Exception as exc:  # noqa: BLE001
            # Google API errors (404, 403, invalid creds) surface here
            err_msg = _sanitize_error(str(exc))
            log.warning(
                "google_sheets_connector_test_failed",
                tenant_id=tenant_id,
                spreadsheet_id=spreadsheet_id,
                error=err_msg,
            )
            return ConnectionTestResult(ok=False, error=err_msg)

        # Check that the requested sheet tab exists
        sheet_titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
        warnings: list[str] = []
        if sheet_name not in sheet_titles:
            warnings.append(
                f"sheet_not_found:'{sheet_name}' — available: {', '.join(sheet_titles)}"
            )

        log.info(
            "google_sheets_connector_test_ok",
            tenant_id=tenant_id,
            spreadsheet_id=spreadsheet_id,
            latency_ms=latency_ms,
        )
        return ConnectionTestResult(ok=True, latency_ms=latency_ms, warnings=warnings)

    def preview(
        self,
        *,
        tenant_id: int,
        config: dict,
        max_rows: int = 1000,
        sample_rows: int = 50,
    ) -> ConnectionPreviewResult:
        """Read up to ``max_rows`` from the sheet and return column metadata + sample."""
        errors = _validate_config(config)
        if errors:
            raise ValueError(errors[0])

        spreadsheet_id: str = config["spreadsheet_id"].strip()
        sheet_name: str = config.get("sheet_name", "Sheet1")
        header_row: int = max(1, int(config.get("header_row", 1)))
        sak: dict = config["service_account_key"]

        try:
            service = _build_service(sak)
        except (ImportError, Exception) as exc:  # noqa: BLE001
            raise ValueError(_sanitize_error(str(exc))) from exc

        # Build an A1 range that covers header + data rows
        # We request header_row to header_row + max_rows (inclusive)
        end_row = header_row + max_rows
        a1_range = f"{sheet_name}!A{header_row}:{_col_letter(512)}{end_row}"

        try:
            result = (
                service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=a1_range,
                    valueRenderOption="FORMATTED_VALUE",
                    dateTimeRenderOption="FORMATTED_STRING",
                )
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            raise ValueError(_sanitize_error(str(exc))) from exc

        raw_rows: list[list[str]] = result.get("values", [])
        if not raw_rows:
            return ConnectionPreviewResult(
                columns=[],
                sample_rows=[],
                row_count_estimate=0,
                warnings=["sheet_appears_empty"],
            )

        # First row = headers
        headers: list[str] = [str(cell).strip() for cell in raw_rows[0]]
        data_rows = raw_rows[1:]

        columns = _build_column_meta(headers, data_rows)
        row_count = len(data_rows)

        # Build sample_rows output (cap at sample_rows)
        sample: list[dict[str, Any]] = []
        for raw_row in data_rows[:sample_rows]:
            record: dict[str, Any] = {}
            for idx, col_name in enumerate(headers):
                record[col_name] = raw_row[idx] if idx < len(raw_row) else None
            sample.append(record)

        null_ratios: dict[str, float] = {}
        if row_count > 0:
            for col in columns:
                null_ratios[col.source_name] = round(col.null_count / row_count, 4)

        log.info(
            "google_sheets_preview_ok",
            tenant_id=tenant_id,
            spreadsheet_id=spreadsheet_id,
            row_count=row_count,
            col_count=len(columns),
        )
        return ConnectionPreviewResult(
            columns=columns,
            sample_rows=sample,
            row_count_estimate=row_count,
            null_ratios=null_ratios,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_column_meta(headers: list[str], data_rows: list[list[str]]) -> list[PreviewColumn]:
    """Derive column metadata from header names + sample data."""
    columns: list[PreviewColumn] = []

    for col_idx, col_name in enumerate(headers):
        values: list[str] = []
        null_count = 0
        for row in data_rows:
            val = row[col_idx] if col_idx < len(row) else ""
            if val == "" or val is None:
                null_count += 1
            else:
                values.append(str(val))

        unique_count = len(set(values))
        detected_type = _detect_type(values[:100])

        sample_values = values[:5]
        columns.append(
            PreviewColumn(
                source_name=col_name or f"col_{col_idx}",
                detected_type=detected_type,
                null_count=null_count,
                unique_count=unique_count,
                sample_values=sample_values,
            )
        )

    return columns


def _detect_type(values: list[str]) -> str:
    """Heuristically detect the column type from a sample of string values."""
    if not values:
        return "string"

    numeric_hits = 0
    date_hits = 0
    for val in values:
        stripped = val.replace(",", "").replace(" ", "")
        # Numeric check
        try:
            float(stripped)
            numeric_hits += 1
            continue
        except ValueError:
            pass
        # Lightweight date pattern check (YYYY-MM-DD or DD/MM/YYYY)
        if len(stripped) >= 8 and (
            (stripped[4] == "-" and stripped[7] == "-")
            or (stripped[2] in "/.-" and stripped[5] in "/.-")
        ):
            date_hits += 1

    ratio = len(values)
    if numeric_hits / ratio >= 0.8:
        return "numeric"
    if date_hits / ratio >= 0.8:
        return "date"
    return "string"


def _col_letter(n: int) -> str:
    """Convert a 1-based column index to an A1 letter (e.g. 1 → A, 27 → AA)."""
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _sanitize_error(msg: str) -> str:
    """Strip any potential credential fragments from error messages."""
    # Truncate and remove common key-like patterns
    truncated = msg[:300]
    # Remove any lines that look like private keys
    lines = [ln for ln in truncated.splitlines() if "PRIVATE KEY" not in ln]
    return " ".join(lines)[:200]

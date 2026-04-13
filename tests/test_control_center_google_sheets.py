"""Tests for GoogleSheetsConnector (Phase 2 — Google Sheets source type).

All Google API calls are mocked — no real HTTP is made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from datapulse.control_center.connectors.google_sheets import (
    GoogleSheetsConnector,
    _col_letter,
    _detect_type,
    _sanitize_error,
    _validate_config,
)
from datapulse.control_center.models import ConnectionPreviewResult, ConnectionTestResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def valid_config() -> dict:
    return {
        "spreadsheet_id": "abc123",
        "sheet_name": "Sheet1",
        "service_account_key": {
            "type": "service_account",
            "project_id": "my-project",
            "private_key_id": "kid123",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "sa@project.iam.gserviceaccount.com",
            "token_uri": "https://oauth2.googleapis.com/token",
        },
    }


@pytest.fixture()
def connector() -> GoogleSheetsConnector:
    return GoogleSheetsConnector()


# ---------------------------------------------------------------------------
# _validate_config
# ---------------------------------------------------------------------------


def test_validate_config_valid(valid_config):
    assert _validate_config(valid_config) == []


def test_validate_config_missing_spreadsheet_id(valid_config):
    valid_config["spreadsheet_id"] = ""
    errors = _validate_config(valid_config)
    assert any("spreadsheet_id" in e for e in errors)


def test_validate_config_missing_sak(valid_config):
    del valid_config["service_account_key"]
    errors = _validate_config(valid_config)
    assert any("service_account_key" in e for e in errors)


def test_validate_config_sak_wrong_type(valid_config):
    valid_config["service_account_key"]["type"] = "authorized_user"
    errors = _validate_config(valid_config)
    assert any("wrong_type" in e for e in errors)


def test_validate_config_sak_missing_fields(valid_config):
    del valid_config["service_account_key"]["private_key"]
    errors = _validate_config(valid_config)
    assert any("private_key" in e for e in errors)


# ---------------------------------------------------------------------------
# GoogleSheetsConnector.test()
# ---------------------------------------------------------------------------


def _mock_sheets_service(sheet_titles: list[str]) -> MagicMock:
    """Build a mock Google Sheets service with the given sheet tab titles."""
    service = MagicMock()
    meta_response = {
        "spreadsheetId": "abc123",
        "sheets": [{"properties": {"title": t}} for t in sheet_titles],
    }
    (service.spreadsheets.return_value.get.return_value.execute.return_value) = meta_response
    return service


def test_test_connection_ok(connector, valid_config):
    mock_service = _mock_sheets_service(["Sheet1", "Sheet2"])
    with patch(
        "datapulse.control_center.connectors.google_sheets._build_service",
        return_value=mock_service,
    ):
        result = connector.test(tenant_id=1, config=valid_config)

    assert isinstance(result, ConnectionTestResult)
    assert result.ok is True
    assert result.latency_ms is not None
    assert result.warnings == []


def test_test_connection_sheet_not_found_warns(connector, valid_config):
    valid_config["sheet_name"] = "MissingTab"
    mock_service = _mock_sheets_service(["Sheet1"])
    with patch(
        "datapulse.control_center.connectors.google_sheets._build_service",
        return_value=mock_service,
    ):
        result = connector.test(tenant_id=1, config=valid_config)

    assert result.ok is True
    assert any("sheet_not_found" in w for w in result.warnings)


def test_test_connection_invalid_config(connector):
    result = connector.test(tenant_id=1, config={"spreadsheet_id": ""})
    assert result.ok is False
    assert "spreadsheet_id" in result.error


def test_test_connection_api_error(connector, valid_config):
    with patch(
        "datapulse.control_center.connectors.google_sheets._build_service",
        side_effect=Exception("403 Forbidden"),
    ):
        result = connector.test(tenant_id=1, config=valid_config)

    assert result.ok is False
    assert result.error is not None


def test_test_connection_import_error(connector, valid_config):
    with patch(
        "datapulse.control_center.connectors.google_sheets._build_service",
        side_effect=ImportError("google-api-python-client not installed"),
    ):
        result = connector.test(tenant_id=1, config=valid_config)

    assert result.ok is False
    assert "google-api-python-client" in result.error or result.error is not None


# ---------------------------------------------------------------------------
# GoogleSheetsConnector.preview()
# ---------------------------------------------------------------------------


def _mock_sheets_values(values: list[list[str]]) -> MagicMock:
    """Build a mock Sheets service that returns the given values array."""
    service = MagicMock()
    (
        service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value
    ) = {"values": values}
    return service


def test_preview_ok(connector, valid_config):
    raw = [
        ["name", "amount", "date"],
        ["Alice", "100.50", "2024-01-01"],
        ["Bob", "200.00", "2024-01-02"],
        ["", "300.00", "2024-01-03"],
    ]
    mock_service = _mock_sheets_values(raw)
    with patch(
        "datapulse.control_center.connectors.google_sheets._build_service",
        return_value=mock_service,
    ):
        result = connector.preview(tenant_id=1, config=valid_config, max_rows=100, sample_rows=10)

    assert isinstance(result, ConnectionPreviewResult)
    assert len(result.columns) == 3  # noqa: PLR2004
    assert result.row_count_estimate == 3  # noqa: PLR2004
    assert len(result.sample_rows) == 3  # noqa: PLR2004

    name_col = next(c for c in result.columns if c.source_name == "name")
    assert name_col.null_count == 1  # empty string row


def test_preview_empty_sheet(connector, valid_config):
    mock_service = _mock_sheets_values([])
    with patch(
        "datapulse.control_center.connectors.google_sheets._build_service",
        return_value=mock_service,
    ):
        result = connector.preview(tenant_id=1, config=valid_config)

    assert result.row_count_estimate == 0
    assert "sheet_appears_empty" in result.warnings


def test_preview_caps_sample_rows(connector, valid_config):
    raw = [["col"]] + [[str(i)] for i in range(200)]
    mock_service = _mock_sheets_values(raw)
    with patch(
        "datapulse.control_center.connectors.google_sheets._build_service",
        return_value=mock_service,
    ):
        result = connector.preview(tenant_id=1, config=valid_config, sample_rows=5)

    assert len(result.sample_rows) == 5  # noqa: PLR2004


def test_preview_invalid_config_raises(connector):
    with pytest.raises(ValueError, match="spreadsheet_id"):
        connector.preview(tenant_id=1, config={"spreadsheet_id": ""})


def test_preview_api_error_raises(connector, valid_config):
    with (
        patch(
            "datapulse.control_center.connectors.google_sheets._build_service",
            side_effect=Exception("404 Not Found"),
        ),
        pytest.raises(ValueError),
    ):
        connector.preview(tenant_id=1, config=valid_config)


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


def test_detect_type_numeric():
    assert _detect_type(["1.0", "2.5", "3", "100"]) == "numeric"


def test_detect_type_date():
    assert _detect_type(["2024-01-01", "2024-02-15", "2023-12-31"]) == "date"


def test_detect_type_string():
    assert _detect_type(["Alice", "Bob", "Charlie"]) == "string"


def test_detect_type_empty():
    assert _detect_type([]) == "string"


def test_col_letter_single():
    assert _col_letter(1) == "A"
    assert _col_letter(26) == "Z"


def test_col_letter_double():
    assert _col_letter(27) == "AA"
    assert _col_letter(28) == "AB"


def test_sanitize_error_strips_private_key():
    msg = "Error\nBEGIN PRIVATE KEY\nABC123\nEND PRIVATE KEY\nDetails"
    result = _sanitize_error(msg)
    assert "PRIVATE KEY" not in result

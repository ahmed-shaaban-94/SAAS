"""Tests for Phase 1b — ControlCenterService WRITE operations.

Covers:
  - SourceConnectionRepository.create / update / archive (via service)
  - service.test_connection  — delegates to FileUploadConnector
  - service.preview_connection — delegates to preview module
  - preview._resolve_path / _safe_json pure helpers
  - preview.preview_file_upload integration (monkeypatched read_file)
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, create_autospec, patch

import pytest

from datapulse.control_center import preview as preview_module
from datapulse.control_center.models import (
    ConnectionPreviewResult,
    ConnectionTestResult,
    PreviewColumn,
    SourceConnection,
)
from datapulse.control_center.repository import (
    MappingTemplateRepository,
    PipelineDraftRepository,
    PipelineProfileRepository,
    PipelineReleaseRepository,
    SourceConnectionRepository,
    SyncJobRepository,
)
from datapulse.control_center.service import ControlCenterService

# ── Fixtures ─────────────────────────────────────────────────


NOW = datetime.now(UTC)


def _connection_row(id_: int = 1, status: str = "draft") -> dict:
    return {
        "id": id_,
        "tenant_id": 1,
        "name": "Acme Sales Q4",
        "source_type": "file_upload",
        "status": status,
        "config_json": {"file_id": "abc-123", "filename": "sales.csv"},
        "credentials_ref": None,
        "last_sync_at": None,
        "created_by": "auth0|user",
        "created_at": NOW,
        "updated_at": NOW,
    }


@pytest.fixture()
def mock_repos():
    return {
        "connections": create_autospec(SourceConnectionRepository, instance=True),
        "profiles": create_autospec(PipelineProfileRepository, instance=True),
        "mappings": create_autospec(MappingTemplateRepository, instance=True),
        "releases": create_autospec(PipelineReleaseRepository, instance=True),
        "sync_jobs": create_autospec(SyncJobRepository, instance=True),
        "drafts": create_autospec(PipelineDraftRepository, instance=True),
    }


@pytest.fixture()
def service(mock_repos) -> ControlCenterService:
    return ControlCenterService(
        MagicMock(),
        connections=mock_repos["connections"],
        profiles=mock_repos["profiles"],
        mappings=mock_repos["mappings"],
        releases=mock_repos["releases"],
        sync_jobs=mock_repos["sync_jobs"],
        drafts=mock_repos["drafts"],
    )


# ── create_connection ────────────────────────────────────────


class TestCreateConnection:
    def test_returns_source_connection(self, service, mock_repos):
        mock_repos["connections"].create.return_value = _connection_row(42)
        result = service.create_connection(
            tenant_id=1,
            name="Acme Sales Q4",
            source_type="file_upload",
            config={"file_id": "abc-123", "filename": "sales.csv"},
            created_by="auth0|user",
        )
        assert isinstance(result, SourceConnection)
        assert result.id == 42
        mock_repos["connections"].create.assert_called_once_with(
            tenant_id=1,
            name="Acme Sales Q4",
            source_type="file_upload",
            config_json={"file_id": "abc-123", "filename": "sales.csv"},
            created_by="auth0|user",
        )

    def test_created_by_defaults_to_none(self, service, mock_repos):
        mock_repos["connections"].create.return_value = _connection_row(1)
        service.create_connection(
            tenant_id=1,
            name="Test",
            source_type="file_upload",
            config={},
        )
        call_kwargs = mock_repos["connections"].create.call_args.kwargs
        assert call_kwargs["created_by"] is None


# ── update_connection ────────────────────────────────────────


class TestUpdateConnection:
    def test_returns_updated_connection(self, service, mock_repos):
        updated = _connection_row(7, status="active")
        mock_repos["connections"].update.return_value = updated
        result = service.update_connection(7, name="New Name", status="active")
        assert isinstance(result, SourceConnection)
        assert result.status == "active"
        mock_repos["connections"].update.assert_called_once_with(
            7, name="New Name", status="active", config_json=None
        )

    def test_returns_none_when_not_found(self, service, mock_repos):
        mock_repos["connections"].update.return_value = None
        result = service.update_connection(999, name="Ghost")
        assert result is None

    def test_partial_update_only_name(self, service, mock_repos):
        mock_repos["connections"].update.return_value = _connection_row(3)
        service.update_connection(3, name="Renamed")
        call_kwargs = mock_repos["connections"].update.call_args.kwargs
        assert call_kwargs["name"] == "Renamed"
        assert call_kwargs["status"] is None
        assert call_kwargs["config_json"] is None

    def test_config_update_passes_dict(self, service, mock_repos):
        new_config = {"file_id": "xyz", "filename": "new.csv"}
        mock_repos["connections"].update.return_value = _connection_row(5)
        service.update_connection(5, config=new_config)
        call_kwargs = mock_repos["connections"].update.call_args.kwargs
        assert call_kwargs["config_json"] == new_config


# ── archive_connection ───────────────────────────────────────


class TestArchiveConnection:
    def test_returns_true_when_found(self, service, mock_repos):
        mock_repos["connections"].archive.return_value = True
        assert service.archive_connection(5) is True
        mock_repos["connections"].archive.assert_called_once_with(5)

    def test_returns_false_when_not_found(self, service, mock_repos):
        mock_repos["connections"].archive.return_value = False
        assert service.archive_connection(999) is False


# ── test_connection ──────────────────────────────────────────


class TestTestConnection:
    def test_ok_for_file_upload(self, service, mock_repos):
        mock_repos["connections"].get.return_value = _connection_row(1)
        fake_result = ConnectionTestResult(ok=True, latency_ms=1.2)
        with patch(
            "datapulse.control_center.connectors.file_upload.FileUploadConnector.test",
            return_value=fake_result,
        ):
            result = service.test_connection(1, tenant_id=1)
        assert result.ok is True
        assert result.latency_ms == 1.2

    def test_not_found_returns_error(self, service, mock_repos):
        mock_repos["connections"].get.return_value = None
        result = service.test_connection(999, tenant_id=1)
        assert result.ok is False
        assert result.error == "connection_not_found"

    def test_unsupported_source_type_returns_error(self, service, mock_repos):
        row = _connection_row(1)
        row["source_type"] = "google_sheets"  # no connector yet
        mock_repos["connections"].get.return_value = row
        result = service.test_connection(1, tenant_id=1)
        assert result.ok is False
        assert "google_sheets" in (result.error or "")


# ── preview_connection ───────────────────────────────────────


class TestPreviewConnection:
    def _fake_preview_result(self) -> ConnectionPreviewResult:
        return ConnectionPreviewResult(
            columns=[
                PreviewColumn(
                    source_name="order_id",
                    detected_type="integer",
                    null_count=0,
                    unique_count=500,
                )
            ],
            sample_rows=[{"order_id": 1}],
            row_count_estimate=500,
            null_ratios={"order_id": 0.0},
        )

    def test_delegates_to_preview_module(self, service, mock_repos):
        mock_repos["connections"].get.return_value = _connection_row(1)
        fake = self._fake_preview_result()
        with patch.object(preview_module, "preview_file_upload", return_value=fake) as mock_fn:
            result = service.preview_connection(
                connection_id=1, tenant_id=1, max_rows=500, sample_rows=50
            )
        assert isinstance(result, ConnectionPreviewResult)
        assert result.row_count_estimate == 500
        mock_fn.assert_called_once_with(
            1,
            {"file_id": "abc-123", "filename": "sales.csv"},
            max_rows=500,
            sample_rows=50,
        )

    def test_raises_when_connection_not_found(self, service, mock_repos):
        mock_repos["connections"].get.return_value = None
        with pytest.raises(ValueError, match="connection_not_found"):
            service.preview_connection(connection_id=999, tenant_id=1)

    def test_raises_for_unsupported_source_type(self, service, mock_repos):
        row = _connection_row(1)
        row["source_type"] = "postgres"
        mock_repos["connections"].get.return_value = row
        with pytest.raises(ValueError, match="preview_not_supported_for"):
            service.preview_connection(connection_id=1, tenant_id=1)


# ── preview module — pure helper functions ───────────────────


class TestPreviewHelpers:
    def test_resolve_path_csv(self):
        from datapulse.control_center.preview import _resolve_path

        path = _resolve_path(7, {"file_id": "abc-def", "filename": "data.csv"})
        assert path == Path("/tmp/datapulse-uploads/7/abc-def.csv")  # noqa: S108

    def test_resolve_path_xlsx(self):
        from datapulse.control_center.preview import _resolve_path

        path = _resolve_path(3, {"file_id": "xyz", "filename": "report.xlsx"})
        assert path == Path("/tmp/datapulse-uploads/3/xyz.xlsx")  # noqa: S108

    def test_resolve_path_defaults_to_csv_when_no_filename(self):
        from datapulse.control_center.preview import _resolve_path

        path = _resolve_path(1, {"file_id": "nofname"})
        assert path.suffix == ".csv"

    def test_resolve_path_raises_on_missing_file_id(self):
        from datapulse.control_center.preview import _resolve_path

        with pytest.raises(ValueError, match="file_id"):
            _resolve_path(1, {})

    def test_safe_json_passthrough_for_primitives(self):
        from datapulse.control_center.preview import _safe_json

        assert _safe_json(42) == 42
        assert _safe_json("hello") == "hello"
        assert _safe_json(None) is None
        assert _safe_json(3.14) == 3.14

    def test_safe_json_converts_non_serializable_to_str(self):
        from datetime import date

        from datapulse.control_center.preview import _safe_json

        result = _safe_json(date(2024, 1, 15))
        assert isinstance(result, str)
        assert "2024" in result


# ── preview module — integration (monkeypatched I/O) ────────


class TestPreviewFileUpload:
    """Tests for preview_file_upload that mock out the file system and reader."""

    def test_raises_file_not_found(self, tmp_path):
        from datapulse.control_center.preview import preview_file_upload

        config = {"file_id": "missing-id", "filename": "data.csv"}
        with pytest.raises(FileNotFoundError):
            preview_file_upload(1, config)

    def test_returns_preview_result(self, tmp_path):
        """Creates a real temp CSV and runs the preview engine end-to-end."""
        from datapulse.control_center.preview import preview_file_upload

        # Write a tiny CSV into the expected upload path
        tenant_dir = tmp_path / "1"
        tenant_dir.mkdir()
        csv_path = tenant_dir / "test-file.csv"
        csv_path.write_text("order_id,amount\n1,100.5\n2,200.0\n3,\n")

        config = {"file_id": "test-file", "filename": "test.csv"}

        # Monkeypatch _UPLOAD_TEMP_DIR so the path resolves into tmp_path
        with patch.object(preview_module, "_UPLOAD_TEMP_DIR", tmp_path):
            result = preview_file_upload(1, config, max_rows=100, sample_rows=10)

        assert isinstance(result, ConnectionPreviewResult)
        assert len(result.columns) == 2
        assert result.row_count_estimate == 3
        col_names = [c.source_name for c in result.columns]
        assert "order_id" in col_names
        assert "amount" in col_names
        # null_ratios: amount has 1 null out of 3
        assert result.null_ratios["amount"] > 0
        assert len(result.sample_rows) <= 3

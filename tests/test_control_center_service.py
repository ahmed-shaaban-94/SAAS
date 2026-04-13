"""Tests for ControlCenterService — Phase 1a READ-only smoke coverage."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, create_autospec

import pytest

from datapulse.control_center import canonical as canonical_helpers
from datapulse.control_center.models import (
    CanonicalDomainList,
    MappingTemplate,
    MappingTemplateList,
    PipelineProfile,
    PipelineProfileList,
    PipelineRelease,
    PipelineReleaseList,
    SourceConnection,
    SourceConnectionList,
    SyncJobList,
)
from datapulse.control_center.repository import (
    MappingTemplateRepository,
    PipelineDraftRepository,
    PipelineProfileRepository,
    PipelineReleaseRepository,
    SourceConnectionRepository,
    SyncJobRepository,
    SyncScheduleRepository,
)
from datapulse.control_center.service import ControlCenterService


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_repos():
    return {
        "connections": create_autospec(SourceConnectionRepository, instance=True),
        "profiles": create_autospec(PipelineProfileRepository, instance=True),
        "mappings": create_autospec(MappingTemplateRepository, instance=True),
        "releases": create_autospec(PipelineReleaseRepository, instance=True),
        "sync_jobs": create_autospec(SyncJobRepository, instance=True),
        "drafts": create_autospec(PipelineDraftRepository, instance=True),
        "schedules": create_autospec(SyncScheduleRepository, instance=True),
    }


@pytest.fixture()
def service(mock_session, mock_repos) -> ControlCenterService:
    return ControlCenterService(
        mock_session,
        connections=mock_repos["connections"],
        profiles=mock_repos["profiles"],
        mappings=mock_repos["mappings"],
        releases=mock_repos["releases"],
        sync_jobs=mock_repos["sync_jobs"],
        drafts=mock_repos["drafts"],
        schedules=mock_repos["schedules"],
    )


NOW = datetime.now(UTC)


def _connection_row(id_: int = 1) -> dict:
    return {
        "id": id_,
        "tenant_id": 1,
        "name": "Acme Sales Q4",
        "source_type": "file_upload",
        "status": "draft",
        "config_json": {"domain": "sales_orders"},
        "credentials_ref": None,
        "last_sync_at": None,
        "created_by": "auth0|user",
        "created_at": NOW,
        "updated_at": NOW,
    }


def _profile_row(id_: int = 1) -> dict:
    return {
        "id": id_,
        "tenant_id": 1,
        "profile_key": "sales_standard",
        "display_name": "Sales Standard",
        "target_domain": "sales_orders",
        "is_default": True,
        "config_json": {"required_fields": ["order_id"]},
        "created_at": NOW,
        "updated_at": NOW,
    }


def _mapping_row(id_: int = 1) -> dict:
    return {
        "id": id_,
        "tenant_id": 1,
        "source_type": "file_upload",
        "template_name": "acme_q4_v1",
        "source_schema_hash": "abc123",
        "mapping_json": {"columns": []},
        "version": 1,
        "created_by": "auth0|user",
        "created_at": NOW,
        "updated_at": NOW,
    }


def _release_row(id_: int = 1, version: int = 1) -> dict:
    return {
        "id": id_,
        "tenant_id": 1,
        "release_version": version,
        "draft_id": None,
        "source_release_id": None,
        "snapshot_json": {"foo": "bar"},
        "release_notes": "",
        "is_rollback": False,
        "published_by": "auth0|user",
        "published_at": NOW,
    }


def _sync_row(id_: int = 1) -> dict:
    return {
        "id": id_,
        "tenant_id": 1,
        "pipeline_run_id": "00000000-0000-0000-0000-000000000001",
        "source_connection_id": 1,
        "release_id": None,
        "profile_id": None,
        "run_mode": "manual",
        "created_by": "auth0|user",
        "created_at": NOW,
        "status": "success",
        "rows_loaded": 1000,
        "error_message": None,
        "started_at": NOW,
        "finished_at": NOW,
        "duration_seconds": 12.5,
    }


class TestConnections:
    def test_list_empty(self, service, mock_repos):
        mock_repos["connections"].list.return_value = ([], 0)
        result = service.list_connections()
        assert isinstance(result, SourceConnectionList)
        assert result.total == 0
        assert result.items == []

    def test_list_with_items(self, service, mock_repos):
        mock_repos["connections"].list.return_value = ([_connection_row(1), _connection_row(2)], 2)
        result = service.list_connections(page=1, page_size=10)
        assert result.total == 2
        assert len(result.items) == 2
        assert all(isinstance(c, SourceConnection) for c in result.items)
        mock_repos["connections"].list.assert_called_once_with(
            source_type=None, status=None, page=1, page_size=10
        )

    def test_list_with_filters(self, service, mock_repos):
        mock_repos["connections"].list.return_value = ([], 0)
        service.list_connections(source_type="file_upload", status="active")
        mock_repos["connections"].list.assert_called_once_with(
            source_type="file_upload", status="active", page=1, page_size=50
        )

    def test_get_found(self, service, mock_repos):
        mock_repos["connections"].get.return_value = _connection_row(7)
        result = service.get_connection(7)
        assert isinstance(result, SourceConnection)
        assert result.id == 7

    def test_get_missing(self, service, mock_repos):
        mock_repos["connections"].get.return_value = None
        assert service.get_connection(999) is None


class TestProfiles:
    def test_list(self, service, mock_repos):
        mock_repos["profiles"].list.return_value = ([_profile_row()], 1)
        result = service.list_profiles(target_domain="sales_orders")
        assert isinstance(result, PipelineProfileList)
        assert result.total == 1
        assert result.items[0].target_domain == "sales_orders"

    def test_get_missing(self, service, mock_repos):
        mock_repos["profiles"].get.return_value = None
        assert service.get_profile(1) is None

    def test_get_found(self, service, mock_repos):
        mock_repos["profiles"].get.return_value = _profile_row(5)
        result = service.get_profile(5)
        assert isinstance(result, PipelineProfile)
        assert result.id == 5


class TestMappings:
    def test_list(self, service, mock_repos):
        mock_repos["mappings"].list.return_value = ([_mapping_row()], 1)
        result = service.list_mappings(source_type="file_upload")
        assert isinstance(result, MappingTemplateList)
        assert result.total == 1

    def test_get_found(self, service, mock_repos):
        mock_repos["mappings"].get.return_value = _mapping_row(3)
        result = service.get_mapping(3)
        assert isinstance(result, MappingTemplate)
        assert result.id == 3


class TestReleases:
    def test_list(self, service, mock_repos):
        mock_repos["releases"].list.return_value = (
            [_release_row(1, 2), _release_row(2, 1)],
            2,
        )
        result = service.list_releases()
        assert isinstance(result, PipelineReleaseList)
        assert result.total == 2
        # Releases returned newest-first by repo.list(ORDER BY release_version DESC)
        assert result.items[0].release_version == 2

    def test_get_missing(self, service, mock_repos):
        mock_repos["releases"].get.return_value = None
        assert service.get_release(1) is None

    def test_get_found(self, service, mock_repos):
        mock_repos["releases"].get.return_value = _release_row(4, 3)
        result = service.get_release(4)
        assert isinstance(result, PipelineRelease)
        assert result.release_version == 3


class TestSyncHistory:
    def test_list(self, service, mock_repos):
        mock_repos["sync_jobs"].list_for_connection.return_value = ([_sync_row()], 1)
        result = service.list_sync_history(connection_id=1)
        assert isinstance(result, SyncJobList)
        assert result.total == 1
        assert result.items[0].status == "success"
        assert result.items[0].rows_loaded == 1000


class TestCanonicalHelpers:
    """Pure functions — no DB needed for required_fields_for / field_types_for."""

    def test_required_fields_extracts_list(self):
        schema = {"required_fields": ["a", "b", "c"]}
        assert canonical_helpers.required_fields_for(schema) == ["a", "b", "c"]

    def test_required_fields_missing(self):
        assert canonical_helpers.required_fields_for({}) == []

    def test_required_fields_malformed(self):
        # non-list input should not crash
        assert canonical_helpers.required_fields_for({"required_fields": "nope"}) == []

    def test_field_types_extracts_dict(self):
        schema = {"types": {"x": "integer", "y": "string"}}
        assert canonical_helpers.field_types_for(schema) == {"x": "integer", "y": "string"}

    def test_field_types_missing(self):
        assert canonical_helpers.field_types_for({}) == {}

    def test_field_types_malformed(self):
        assert canonical_helpers.field_types_for({"types": "nope"}) == {}


class TestCanonicalDomainsService:
    def test_list_canonical_domains_empty(self, service, mock_session, monkeypatch):
        monkeypatch.setattr(canonical_helpers, "list_canonical_domains", lambda s: [])
        result = service.list_canonical_domains()
        assert isinstance(result, CanonicalDomainList)
        assert result.items == []

    def test_list_canonical_domains_with_items(self, service, mock_session, monkeypatch):
        monkeypatch.setattr(
            canonical_helpers,
            "list_canonical_domains",
            lambda s: [
                {
                    "domain_key": "sales_orders",
                    "version": 1,
                    "display_name": "Sales Orders",
                    "description": "",
                    "json_schema": {"required_fields": ["order_id"]},
                    "is_active": True,
                }
            ],
        )
        result = service.list_canonical_domains()
        assert len(result.items) == 1
        assert result.items[0].domain_key == "sales_orders"

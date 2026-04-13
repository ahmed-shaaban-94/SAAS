"""Tests for Phase 1c/1d/1e — profile/mapping CRUD, draft workflow, rollback, sync.

All tests are unit-level (mocked repositories, no database).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, create_autospec, patch

import pytest

from datapulse.control_center.models import (
    MappingTemplate,
    PipelineDraft,
    PipelineProfile,
    PipelineRelease,
    SyncJob,
    ValidationReport,
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

NOW = datetime.now(UTC)


# ── Fixtures ──────────────────────────────────────────────────


def _profile_row(id_: int = 1) -> dict:
    return {
        "id": id_,
        "tenant_id": 1,
        "profile_key": "default-sales",
        "display_name": "Default Sales",
        "target_domain": "sales_orders",
        "is_default": True,
        "config_json": {"keys": ["order_id"], "quality_thresholds": {}},
        "created_at": NOW,
        "updated_at": NOW,
    }


def _mapping_row(id_: int = 1) -> dict:
    return {
        "id": id_,
        "tenant_id": 1,
        "source_type": "file_upload",
        "template_name": "Sales Mapping v1",
        "source_schema_hash": None,
        "mapping_json": {"columns": [{"source": "id", "canonical": "order_id", "cast": "integer"}]},
        "version": 1,
        "created_by": "user@test",
        "created_at": NOW,
        "updated_at": NOW,
    }


def _draft_row(id_: int = 1, status: str = "draft") -> dict:
    return {
        "id": id_,
        "tenant_id": 1,
        "entity_type": "bundle",
        "entity_id": None,
        "draft_json": {
            "mapping_columns": [{"source": "id", "canonical": "order_id", "cast": "integer"}],
            "profile_config": {"keys": ["order_id"], "quality_thresholds": {}},
            "target_domain": "sales_orders",
        },
        "status": status,
        "validation_report_json": None,
        "preview_result_json": None,
        "version": 0,
        "created_by": "user@test",
        "created_at": NOW,
        "updated_at": NOW,
    }


def _release_row(id_: int = 1, version: int = 1) -> dict:
    return {
        "id": id_,
        "tenant_id": 1,
        "release_version": version,
        "draft_id": 1,
        "source_release_id": None,
        "snapshot_json": {"draft_id": 1},
        "release_notes": "initial",
        "is_rollback": False,
        "published_by": "user@test",
        "published_at": NOW,
    }


def _sync_row(id_: int = 1) -> dict:
    return {
        "id": id_,
        "tenant_id": 1,
        "pipeline_run_id": "abc-run-uuid",
        "source_connection_id": 10,
        "release_id": None,
        "profile_id": None,
        "run_mode": "manual",
        "created_by": "user@test",
        "created_at": NOW,
    }


def _connection_row(id_: int = 10) -> dict:
    return {
        "id": id_,
        "tenant_id": 1,
        "name": "Test Upload",
        "source_type": "file_upload",
        "status": "active",
        "config_json": {"file_id": "abc", "filename": "sales.csv"},
        "credentials_ref": None,
        "last_sync_at": None,
        "created_by": "user@test",
        "created_at": NOW,
        "updated_at": NOW,
    }


@pytest.fixture()
def mock_session():
    return MagicMock()


@pytest.fixture()
def repos():
    return {
        "connections": create_autospec(SourceConnectionRepository, instance=True),
        "profiles": create_autospec(PipelineProfileRepository, instance=True),
        "mappings": create_autospec(MappingTemplateRepository, instance=True),
        "releases": create_autospec(PipelineReleaseRepository, instance=True),
        "sync_jobs": create_autospec(SyncJobRepository, instance=True),
        "drafts": create_autospec(PipelineDraftRepository, instance=True),
    }


@pytest.fixture()
def svc(mock_session, repos) -> ControlCenterService:
    return ControlCenterService(mock_session, **repos)


# ── Phase 1c: Profile CRUD ────────────────────────────────────


class TestProfileCrud:
    def test_create_profile(self, svc, repos):
        repos["profiles"].create.return_value = _profile_row()
        result = svc.create_profile(
            tenant_id=1,
            profile_key="default-sales",
            display_name="Default Sales",
            target_domain="sales_orders",
            is_default=True,
            config={"keys": ["order_id"]},
        )
        assert isinstance(result, PipelineProfile)
        assert result.profile_key == "default-sales"
        repos["profiles"].create.assert_called_once()

    def test_update_profile(self, svc, repos):
        updated = {**_profile_row(), "display_name": "Updated"}
        repos["profiles"].update.return_value = updated
        result = svc.update_profile(1, display_name="Updated")
        assert isinstance(result, PipelineProfile)
        assert result.display_name == "Updated"

    def test_update_profile_not_found(self, svc, repos):
        repos["profiles"].update.return_value = None
        result = svc.update_profile(999, display_name="X")
        assert result is None

    def test_update_profile_is_default(self, svc, repos):
        row = {**_profile_row(), "is_default": False}
        repos["profiles"].update.return_value = row
        result = svc.update_profile(1, is_default=False)
        assert result is not None
        assert result.is_default is False


# ── Phase 1c: Mapping CRUD ────────────────────────────────────


class TestMappingCrud:
    def test_create_mapping(self, svc, repos):
        repos["mappings"].create.return_value = _mapping_row()
        result = svc.create_mapping(
            tenant_id=1,
            source_type="file_upload",
            template_name="Sales Mapping v1",
            columns=[{"source": "id", "canonical": "order_id", "cast": "integer"}],
        )
        assert isinstance(result, MappingTemplate)
        assert result.template_name == "Sales Mapping v1"
        # mapping_json should wrap columns
        call_kwargs = repos["mappings"].create.call_args.kwargs
        assert "columns" in call_kwargs["mapping_json"]

    def test_update_mapping(self, svc, repos):
        updated = {**_mapping_row(), "version": 2}
        repos["mappings"].update.return_value = updated
        cols = [{"source": "x", "canonical": "order_id", "cast": "integer"}]
        result = svc.update_mapping(1, columns=cols)
        assert isinstance(result, MappingTemplate)
        assert result.version == 2

    def test_update_mapping_not_found(self, svc, repos):
        repos["mappings"].update.return_value = None
        result = svc.update_mapping(999)
        assert result is None


# ── Phase 1c: Standalone mapping validation ───────────────────


class TestValidateMapping:
    def test_validate_mapping_unknown_domain(self, svc, mock_session):
        with patch("datapulse.control_center.canonical.get_canonical_domain", return_value=None):
            result = svc.validate_mapping_standalone(
                columns=[{"source": "x", "canonical": "order_id", "cast": "integer"}],
                target_domain="nonexistent",
                profile_config={},
                tenant_id=1,
            )
        assert isinstance(result, ValidationReport)
        assert result.ok is False
        assert result.errors[0].code == "UNKNOWN_DOMAIN"

    def test_validate_mapping_ok(self, svc, mock_session):
        fake_domain = {
            "domain_key": "sales_orders",
            "json_schema": {
                "required_fields": ["order_id"],
                "types": {"order_id": "integer"},
            },
        }
        with patch(
            "datapulse.control_center.canonical.get_canonical_domain",
            return_value=fake_domain,
        ):
            result = svc.validate_mapping_standalone(
                columns=[{"source": "id", "canonical": "order_id", "cast": "integer"}],
                target_domain="sales_orders",
                profile_config={"keys": ["order_id"]},
                tenant_id=1,
            )
        assert isinstance(result, ValidationReport)
        assert result.ok is True


# ── Phase 1d: Draft workflow ──────────────────────────────────


class TestDraftWorkflow:
    def test_create_draft(self, svc, repos):
        repos["drafts"].create.return_value = _draft_row()
        result = svc.create_draft(
            tenant_id=1,
            entity_type="bundle",
            draft={"source_connection_id": 10},
        )
        assert isinstance(result, PipelineDraft)
        assert result.status == "draft"

    def test_get_draft_not_found(self, svc, repos):
        repos["drafts"].get.return_value = None
        result = svc.get_draft(999)
        assert result is None

    def test_validate_draft_not_found(self, svc, repos):
        repos["drafts"].get.return_value = None
        with pytest.raises(ValueError, match="draft_not_found"):
            svc.validate_draft_workflow(999, tenant_id=1)

    def test_validate_draft_ok(self, svc, repos):
        repos["drafts"].get.return_value = _draft_row()
        repos["drafts"].update_status.return_value = _draft_row(status="validating")
        repos["releases"].latest.return_value = None

        validated_row = _draft_row(status="validated")
        validated_row["validation_report_json"] = {"ok": True, "errors": [], "warnings": []}
        repos["drafts"].update_validation.return_value = validated_row

        fake_domain = {
            "domain_key": "sales_orders",
            "json_schema": {"required_fields": [], "types": {}},
        }
        with patch(
            "datapulse.control_center.canonical.get_canonical_domain",
            return_value=fake_domain,
        ):
            result = svc.validate_draft_workflow(1, tenant_id=1)

        assert isinstance(result, PipelineDraft)
        assert result.status == "validated"

    def test_validate_draft_invalidated_on_errors(self, svc, repos):
        draft = _draft_row()
        draft["draft_json"]["target_domain"] = "sales_orders"
        repos["drafts"].get.return_value = draft
        repos["drafts"].update_status.return_value = draft
        repos["releases"].latest.return_value = None

        invalidated_row = _draft_row(status="invalidated")
        invalidated_row["validation_report_json"] = {
            "ok": False,
            "errors": [{"code": "MISSING_REQUIRED_FIELD"}],
            "warnings": [],
        }
        repos["drafts"].update_validation.return_value = invalidated_row

        # Force a missing required field by requiring something not in the mapping
        fake_domain = {
            "domain_key": "sales_orders",
            "json_schema": {"required_fields": ["missing_field"], "types": {}},
        }
        with patch(
            "datapulse.control_center.canonical.get_canonical_domain",
            return_value=fake_domain,
        ):
            result = svc.validate_draft_workflow(1, tenant_id=1)

        assert result.status == "invalidated"

    def test_publish_draft_not_found(self, svc, repos):
        repos["drafts"].get.return_value = None
        with pytest.raises(ValueError, match="draft_not_found"):
            svc.publish_draft(999, tenant_id=1)

    def test_publish_draft_wrong_status(self, svc, repos):
        repos["drafts"].get.return_value = _draft_row(status="draft")
        with pytest.raises(ValueError, match="draft_not_publishable"):
            svc.publish_draft(1, tenant_id=1)

    def test_publish_draft_ok(self, svc, repos):
        repos["drafts"].get.return_value = _draft_row(status="validated")
        repos["drafts"].update_status.return_value = _draft_row(status="publishing")
        repos["connections"].get.return_value = None
        repos["profiles"].get.return_value = None
        repos["mappings"].get.return_value = None
        repos["releases"].create.return_value = _release_row()
        repos["drafts"].update_status.return_value = _draft_row(status="published")

        with patch("datapulse.control_center.service.cache_invalidate_tenant", create=True):
            result = svc.publish_draft(1, tenant_id=1, release_notes="initial release")

        assert isinstance(result, PipelineRelease)
        assert result.release_version == 1

    def test_publish_draft_marks_failed_on_exception(self, svc, repos):
        repos["drafts"].get.return_value = _draft_row(status="validated")
        repos["drafts"].update_status.return_value = _draft_row(status="publishing")
        repos["connections"].get.return_value = None
        repos["profiles"].get.return_value = None
        repos["mappings"].get.return_value = None
        repos["releases"].create.side_effect = RuntimeError("DB down")

        with pytest.raises(RuntimeError):
            svc.publish_draft(1, tenant_id=1)

        # Should have called update_status with "publish_failed"
        update_calls = [str(call) for call in repos["drafts"].update_status.call_args_list]
        assert any("publish_failed" in c for c in update_calls)


# ── Phase 1d: Rollback ────────────────────────────────────────


class TestRollback:
    def test_rollback_not_found(self, svc, repos):
        repos["releases"].get.return_value = None
        with pytest.raises(ValueError, match="release_not_found"):
            svc.rollback_release(999, tenant_id=1)

    def test_rollback_creates_new_release(self, svc, repos):
        repos["releases"].get.return_value = _release_row(id_=5, version=5)
        rollback_row = {
            **_release_row(id_=6, version=6),
            "is_rollback": True,
            "source_release_id": 5,
        }
        repos["releases"].create.return_value = rollback_row

        with patch("datapulse.control_center.service.cache_invalidate_tenant", create=True):
            result = svc.rollback_release(5, tenant_id=1)

        assert isinstance(result, PipelineRelease)
        assert result.is_rollback is True
        assert result.source_release_id == 5
        repos["releases"].create.assert_called_once()

    def test_rollback_never_updates_original(self, svc, repos):
        repos["releases"].get.return_value = _release_row()
        repos["releases"].create.return_value = {
            **_release_row(id_=2, version=2),
            "is_rollback": True,
            "source_release_id": 1,
        }

        with patch("datapulse.control_center.service.cache_invalidate_tenant", create=True):
            svc.rollback_release(1, tenant_id=1)

        repos["releases"].update if hasattr(repos["releases"], "update") else None
        # Ensure we never called any update on releases
        assert not repos["releases"].update.called if hasattr(repos["releases"], "update") else True


# ── Phase 1e: Sync trigger ────────────────────────────────────


class TestSyncTrigger:
    def test_trigger_sync_connection_not_found(self, svc, repos):
        repos["connections"].get.return_value = None
        with pytest.raises(ValueError, match="connection_not_found"):
            svc.trigger_sync(999, tenant_id=1)

    def test_trigger_sync_ok(self, svc, repos):
        repos["connections"].get.return_value = _connection_row()
        repos["sync_jobs"].create.return_value = _sync_row()

        result = svc.trigger_sync(10, tenant_id=1, run_mode="manual")

        assert isinstance(result, SyncJob)
        assert result.run_mode == "manual"
        repos["sync_jobs"].create.assert_called_once()
        # Verify a UUID was generated for pipeline_run_id
        call_kwargs = repos["sync_jobs"].create.call_args.kwargs
        assert call_kwargs["pipeline_run_id"] is not None

    def test_trigger_sync_passes_release_and_profile(self, svc, repos):
        repos["connections"].get.return_value = _connection_row()
        repos["sync_jobs"].create.return_value = _sync_row()

        svc.trigger_sync(10, tenant_id=1, release_id=3, profile_id=2)

        call_kwargs = repos["sync_jobs"].create.call_args.kwargs
        assert call_kwargs["release_id"] == 3
        assert call_kwargs["profile_id"] == 2

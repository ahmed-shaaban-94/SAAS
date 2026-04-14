"""Integration tests for the publish_draft → onboarding step wiring.

Phase 4: verifies that the first publish triggers configure_first_profile,
and that subsequent publishes do NOT re-trigger it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, create_autospec, patch

import pytest

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

NOW = datetime.now(UTC)


def _draft_row(status: str = "validated") -> dict:
    return {
        "id": 1,
        "tenant_id": 1,
        "entity_type": "bundle",
        "entity_id": None,
        "draft_json": {},
        "status": status,
        "validation_report_json": None,
        "preview_result_json": None,
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
        "draft_id": 1,
        "source_release_id": None,
        "snapshot_json": {},
        "release_notes": "",
        "is_rollback": False,
        "published_by": "auth0|user",
        "published_at": NOW,
    }


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


class TestPublishDraftOnboardingHook:
    """Verify onboarding.complete_step wiring in publish_draft."""

    def test_first_publish_triggers_onboarding_step(self, service, mock_repos, mock_session):
        """First release (count == 1) must call onboarding complete_step."""
        mock_repos["drafts"].get.return_value = _draft_row("validated")
        mock_repos["drafts"].update_status.return_value = _draft_row("published")
        mock_repos["releases"].create.return_value = _release_row()
        # count_for_tenant returns 1 → first release
        mock_repos["releases"].count_for_tenant.return_value = 1

        fake_onboarding_svc = MagicMock()

        with (
            patch("datapulse.cache.cache_invalidate_pattern"),
            patch(
                "datapulse.onboarding.service.OnboardingService",
                return_value=fake_onboarding_svc,
            ),
            patch("datapulse.onboarding.repository.OnboardingRepository"),
        ):
            service.publish_draft(1, tenant_id=1, release_notes="", published_by="auth0|user")

        fake_onboarding_svc.complete_step.assert_called_once_with(
            tenant_id=1,
            user_id="auth0|user",
            step="configure_first_profile",
        )

    def test_second_publish_does_not_call_onboarding(self, service, mock_repos, mock_session):
        """Subsequent releases (count > 1) must NOT call onboarding."""
        mock_repos["drafts"].get.return_value = _draft_row("validated")
        mock_repos["drafts"].update_status.return_value = _draft_row("published")
        mock_repos["releases"].create.return_value = _release_row(id_=2, version=2)
        # count_for_tenant returns 2 → not the first release
        mock_repos["releases"].count_for_tenant.return_value = 2

        fake_onboarding_svc = MagicMock()

        with (
            patch("datapulse.cache.cache_invalidate_pattern"),
            patch(
                "datapulse.onboarding.service.OnboardingService",
                return_value=fake_onboarding_svc,
            ),
            patch("datapulse.onboarding.repository.OnboardingRepository"),
        ):
            service.publish_draft(1, tenant_id=1, release_notes="", published_by="auth0|user")

        fake_onboarding_svc.complete_step.assert_not_called()

    def test_onboarding_value_error_is_swallowed(self, service, mock_repos, mock_session):
        """ValueError from already-completed step must not propagate."""
        mock_repos["drafts"].get.return_value = _draft_row("validated")
        mock_repos["drafts"].update_status.return_value = _draft_row("published")
        mock_repos["releases"].create.return_value = _release_row()
        mock_repos["releases"].count_for_tenant.return_value = 1

        fake_onboarding_svc = MagicMock()
        fake_onboarding_svc.complete_step.side_effect = ValueError("already done")

        with (
            patch("datapulse.cache.cache_invalidate_pattern"),
            patch(
                "datapulse.onboarding.service.OnboardingService",
                return_value=fake_onboarding_svc,
            ),
            patch("datapulse.onboarding.repository.OnboardingRepository"),
        ):
            # Must not raise
            release = service.publish_draft(
                1, tenant_id=1, release_notes="", published_by="auth0|user"
            )

        assert release.release_version == 1

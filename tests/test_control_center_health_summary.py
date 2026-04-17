"""Tests for the GET /control-center/health-summary endpoint.

Verifies that ControlCenterService.get_health_summary correctly aggregates
data from PipelineReleaseRepository.get_health_summary.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, create_autospec

import pytest

from datapulse.control_center.models import HealthSummary
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


class TestHealthSummary:
    """Verify aggregation logic in get_health_summary."""

    def test_returns_health_summary_model(self, service, mock_repos):
        """get_health_summary returns a HealthSummary Pydantic model."""
        mock_repos["releases"].get_health_summary.return_value = {
            "active_connections": 3,
            "last_sync_at": NOW,
            "active_release_version": 5,
            "pending_drafts": 2,
            "failed_syncs_last_24h": 0,
        }

        result = service.get_health_summary(tenant_id=1)

        assert isinstance(result, HealthSummary)
        assert result.active_connections == 3
        assert result.last_sync_at == NOW
        assert result.active_release_version == 5
        assert result.pending_drafts == 2
        assert result.failed_syncs_last_24h == 0

    def test_passes_tenant_id_to_repo(self, service, mock_repos):
        """Service must pass the tenant_id through to the repository."""
        mock_repos["releases"].get_health_summary.return_value = {
            "active_connections": 0,
            "last_sync_at": None,
            "active_release_version": None,
            "pending_drafts": 0,
            "failed_syncs_last_24h": 0,
        }

        service.get_health_summary(tenant_id=42)

        mock_repos["releases"].get_health_summary.assert_called_once_with(42)

    def test_handles_empty_tenant(self, service, mock_repos):
        """All-zero/None values returned by repo produce a valid HealthSummary."""
        mock_repos["releases"].get_health_summary.return_value = {
            "active_connections": 0,
            "last_sync_at": None,
            "active_release_version": None,
            "pending_drafts": 0,
            "failed_syncs_last_24h": 0,
        }

        result = service.get_health_summary(tenant_id=1)

        assert result.active_connections == 0
        assert result.last_sync_at is None
        assert result.active_release_version is None

    def test_failed_syncs_non_zero(self, service, mock_repos):
        """Verify failed_syncs_last_24h is surfaced correctly."""
        mock_repos["releases"].get_health_summary.return_value = {
            "active_connections": 2,
            "last_sync_at": NOW,
            "active_release_version": 1,
            "pending_drafts": 0,
            "failed_syncs_last_24h": 7,
        }

        result = service.get_health_summary(tenant_id=1)

        assert result.failed_syncs_last_24h == 7

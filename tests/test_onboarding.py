"""Tests for OnboardingService business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from datapulse.onboarding.models import OnboardingStatus
from datapulse.onboarding.repository import OnboardingRepository
from datapulse.onboarding.service import OnboardingService


@pytest.fixture()
def mock_repo():
    return create_autospec(OnboardingRepository, instance=True)


@pytest.fixture()
def service(mock_repo):
    return OnboardingService(mock_repo)


class TestGetStatus:
    def test_get_status_new_user(self, service, mock_repo):
        """When repo returns None, service returns a default OnboardingStatus."""
        mock_repo.get_status.return_value = None

        result = service.get_status(tenant_id=1, user_id="user-1")

        assert isinstance(result, OnboardingStatus)
        assert result.tenant_id == 1
        assert result.user_id == "user-1"
        assert result.steps_completed == []
        assert result.current_step == "connect_data"
        assert result.completed_at is None
        assert result.is_complete is False
        mock_repo.get_status.assert_called_once_with("user-1")

    def test_get_status_existing_user(self, service, mock_repo):
        """When repo returns data, service constructs OnboardingStatus from it."""
        now = datetime.now(UTC)
        mock_repo.get_status.return_value = {
            "id": 42,
            "tenant_id": 1,
            "user_id": "user-1",
            "steps_completed": ["connect_data"],
            "current_step": "first_report",
            "completed_at": None,
            "skipped_at": None,
            "created_at": now,
        }

        result = service.get_status(tenant_id=1, user_id="user-1")

        assert result.id == 42
        assert result.steps_completed == ["connect_data"]
        assert result.current_step == "first_report"
        assert result.is_complete is False


class TestCompleteStep:
    def test_complete_step_first(self, service, mock_repo):
        """Completing 'connect_data' advances current_step to 'first_report'."""
        mock_repo.get_status.return_value = None
        now = datetime.now(UTC)
        mock_repo.upsert_status.return_value = {
            "id": 1,
            "tenant_id": 1,
            "user_id": "user-1",
            "steps_completed": ["connect_data"],
            "current_step": "first_report",
            "completed_at": None,
            "skipped_at": None,
            "created_at": now,
        }

        result = service.complete_step(tenant_id=1, user_id="user-1", step="connect_data")

        assert result.steps_completed == ["connect_data"]
        assert result.current_step == "first_report"
        assert result.is_complete is False
        mock_repo.upsert_status.assert_called_once()
        call_kwargs = mock_repo.upsert_status.call_args
        assert call_kwargs.kwargs["steps_completed"] == ["connect_data"]
        assert call_kwargs.kwargs["current_step"] == "first_report"

    def test_complete_step_all(self, service, mock_repo):
        """When all steps are done, is_complete=True and completed_at is set."""
        mock_repo.get_status.return_value = {
            "id": 1,
            "tenant_id": 1,
            "user_id": "user-1",
            "steps_completed": ["connect_data", "first_report"],
            "current_step": "first_goal",
            "completed_at": None,
            "skipped_at": None,
            "created_at": datetime.now(UTC),
        }
        now = datetime.now(UTC)
        mock_repo.upsert_status.return_value = {
            "id": 1,
            "tenant_id": 1,
            "user_id": "user-1",
            "steps_completed": ["connect_data", "first_report", "first_goal"],
            "current_step": "first_goal",
            "completed_at": now,
            "skipped_at": None,
            "created_at": now,
        }

        result = service.complete_step(tenant_id=1, user_id="user-1", step="first_goal")

        assert result.is_complete is True
        assert result.completed_at is not None
        call_kwargs = mock_repo.upsert_status.call_args.kwargs
        assert call_kwargs["completed_at"] is not None

    def test_complete_step_invalid(self, service, mock_repo):
        """An unknown step raises ValueError."""
        with pytest.raises(ValueError, match="Invalid step"):
            service.complete_step(tenant_id=1, user_id="user-1", step="bad_step")

        mock_repo.upsert_status.assert_not_called()

    def test_complete_step_already_done(self, service, mock_repo):
        """Completing an already-completed step does not duplicate it."""
        mock_repo.get_status.return_value = {
            "id": 1,
            "tenant_id": 1,
            "user_id": "user-1",
            "steps_completed": ["connect_data"],
            "current_step": "first_report",
            "completed_at": None,
            "skipped_at": None,
            "created_at": datetime.now(UTC),
        }
        mock_repo.upsert_status.return_value = {
            "id": 1,
            "tenant_id": 1,
            "user_id": "user-1",
            "steps_completed": ["connect_data"],
            "current_step": "first_report",
            "completed_at": None,
            "skipped_at": None,
            "created_at": datetime.now(UTC),
        }

        service.complete_step(tenant_id=1, user_id="user-1", step="connect_data")

        call_kwargs = mock_repo.upsert_status.call_args.kwargs
        # Step should not appear twice
        assert call_kwargs["steps_completed"].count("connect_data") == 1


class TestSkip:
    def test_skip(self, service, mock_repo):
        """Skip sets skipped_at timestamp."""
        mock_repo.get_status.return_value = None
        now = datetime.now(UTC)
        mock_repo.upsert_status.return_value = {
            "id": 1,
            "tenant_id": 1,
            "user_id": "user-1",
            "steps_completed": [],
            "current_step": "connect_data",
            "completed_at": None,
            "skipped_at": now,
            "created_at": now,
        }

        result = service.skip(tenant_id=1, user_id="user-1")

        assert result.skipped_at is not None
        mock_repo.upsert_status.assert_called_once()
        call_kwargs = mock_repo.upsert_status.call_args.kwargs
        assert call_kwargs["skipped_at"] is not None

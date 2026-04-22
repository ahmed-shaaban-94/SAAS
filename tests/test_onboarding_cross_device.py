"""Tests for onboarding cross-device sync — golden path progress + first-insight dismissal.

Follow-up #6: backend endpoints so the OnboardingStrip and FirstInsightCard
can persist their state server-side, enabling cross-device/cross-browser sync.

Covers:
- OnboardingRepository: upsert_golden_path_progress, dismiss_first_insight
- OnboardingService: update_golden_path_progress, dismiss_first_insight
- API routes: PUT /golden-path-progress, POST /dismiss-first-insight
- GET /status returns the two new fields
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_onboarding_service
from datapulse.onboarding.models import OnboardingStatus
from datapulse.onboarding.repository import OnboardingRepository
from datapulse.onboarding.service import OnboardingService

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_user() -> dict:
    return {
        "sub": "test-user",
        "tenant_id": "1",
        "roles": ["admin"],
        "email": "test@datapulse.local",
        "preferred_username": "test",
        "raw_claims": {},
    }


def _make_status(**overrides) -> OnboardingStatus:
    now = datetime.now(UTC)
    defaults = dict(
        id=1,
        tenant_id=1,
        user_id="test-user",
        steps_completed=[],
        current_step="connect_data",
        completed_at=None,
        skipped_at=None,
        created_at=now,
        golden_path_progress={},
        first_insight_dismissed_at=None,
    )
    defaults.update(overrides)
    return OnboardingStatus(**defaults)


# ---------------------------------------------------------------------------
# Repository unit tests
# ---------------------------------------------------------------------------


class TestUpsertGoldenPathProgress:
    """OnboardingRepository.upsert_golden_path_progress writes only its column."""

    def test_executes_upsert_and_returns_row(self) -> None:
        session = MagicMock()
        progress = {"upload_data": "2026-04-17T10:00:00Z", "validate": None}

        expected_row = {
            "id": 1,
            "tenant_id": 1,
            "user_id": "test-user",
            "steps_completed": [],
            "current_step": "connect_data",
            "completed_at": None,
            "skipped_at": None,
            "created_at": datetime.now(UTC),
            "golden_path_progress": progress,
            "first_insight_dismissed_at": None,
        }
        session.execute.return_value.mappings.return_value.fetchone.return_value = expected_row

        repo = OnboardingRepository(session)
        result = repo.upsert_golden_path_progress(
            tenant_id=1, user_id="test-user", progress=progress
        )

        session.execute.assert_called_once()
        assert result["golden_path_progress"] == progress
        assert result["user_id"] == "test-user"

    def test_raises_on_missing_returning_row(self) -> None:
        session = MagicMock()
        session.execute.return_value.mappings.return_value.fetchone.return_value = None

        repo = OnboardingRepository(session)
        with pytest.raises(RuntimeError, match="UPSERT RETURNING"):
            repo.upsert_golden_path_progress(tenant_id=1, user_id="test-user", progress={})


class TestDismissFirstInsight:
    """OnboardingRepository.dismiss_first_insight sets first_insight_dismissed_at."""

    def test_executes_upsert_and_returns_row(self) -> None:
        session = MagicMock()
        now = datetime.now(UTC)

        expected_row = {
            "id": 1,
            "tenant_id": 1,
            "user_id": "test-user",
            "steps_completed": [],
            "current_step": "connect_data",
            "completed_at": None,
            "skipped_at": None,
            "created_at": now,
            "golden_path_progress": {},
            "first_insight_dismissed_at": now,
        }
        session.execute.return_value.mappings.return_value.fetchone.return_value = expected_row

        repo = OnboardingRepository(session)
        result = repo.dismiss_first_insight(tenant_id=1, user_id="test-user")

        session.execute.assert_called_once()
        assert result["first_insight_dismissed_at"] is not None

    def test_raises_on_missing_returning_row(self) -> None:
        session = MagicMock()
        session.execute.return_value.mappings.return_value.fetchone.return_value = None

        repo = OnboardingRepository(session)
        with pytest.raises(RuntimeError, match="UPSERT RETURNING"):
            repo.dismiss_first_insight(tenant_id=1, user_id="test-user")


class TestGetStatusReturnsNewFields:
    """get_status SELECT includes the two new columns."""

    def test_returns_golden_path_progress_and_dismissed_at(self) -> None:
        session = MagicMock()
        now = datetime.now(UTC)
        progress = {"upload_data": "2026-04-17T10:00:00Z"}

        session.execute.return_value.mappings.return_value.fetchone.return_value = {
            "id": 1,
            "tenant_id": 1,
            "user_id": "test-user",
            "steps_completed": [],
            "current_step": "connect_data",
            "completed_at": None,
            "skipped_at": None,
            "created_at": now,
            "golden_path_progress": progress,
            "first_insight_dismissed_at": now,
        }

        repo = OnboardingRepository(session)
        result = repo.get_status("test-user")

        assert result is not None
        assert result["golden_path_progress"] == progress
        assert result["first_insight_dismissed_at"] == now


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------


class TestUpdateGoldenPathProgressService:
    """OnboardingService.update_golden_path_progress delegates to repo."""

    def test_calls_repo_method(self) -> None:
        repo = MagicMock(spec=OnboardingRepository)
        progress = {"upload_data": "2026-04-17T10:00:00Z"}
        repo.upsert_golden_path_progress.return_value = {
            "id": 1,
            "tenant_id": 1,
            "user_id": "test-user",
            "steps_completed": [],
            "current_step": "connect_data",
            "completed_at": None,
            "skipped_at": None,
            "created_at": datetime.now(UTC),
            "golden_path_progress": progress,
            "first_insight_dismissed_at": None,
        }

        svc = OnboardingService(repo)
        result = svc.update_golden_path_progress(
            tenant_id=1, user_id="test-user", progress=progress
        )

        repo.upsert_golden_path_progress.assert_called_once_with(
            tenant_id=1, user_id="test-user", progress=progress
        )
        assert result.golden_path_progress == progress

    def test_returns_onboarding_status(self) -> None:
        repo = MagicMock(spec=OnboardingRepository)
        repo.upsert_golden_path_progress.return_value = {
            "id": 1,
            "tenant_id": 1,
            "user_id": "test-user",
            "steps_completed": [],
            "current_step": "connect_data",
            "completed_at": None,
            "skipped_at": None,
            "created_at": datetime.now(UTC),
            "golden_path_progress": {},
            "first_insight_dismissed_at": None,
        }

        svc = OnboardingService(repo)
        result = svc.update_golden_path_progress(tenant_id=1, user_id="test-user", progress={})

        assert isinstance(result, OnboardingStatus)


class TestDismissFirstInsightService:
    """OnboardingService.dismiss_first_insight delegates to repo."""

    def test_calls_repo_method(self) -> None:
        repo = MagicMock(spec=OnboardingRepository)
        now = datetime.now(UTC)
        repo.dismiss_first_insight.return_value = {
            "id": 1,
            "tenant_id": 1,
            "user_id": "test-user",
            "steps_completed": [],
            "current_step": "connect_data",
            "completed_at": None,
            "skipped_at": None,
            "created_at": now,
            "golden_path_progress": {},
            "first_insight_dismissed_at": now,
        }

        svc = OnboardingService(repo)
        result = svc.dismiss_first_insight(tenant_id=1, user_id="test-user")

        repo.dismiss_first_insight.assert_called_once_with(tenant_id=1, user_id="test-user")
        assert result.first_insight_dismissed_at is not None


# ---------------------------------------------------------------------------
# Route integration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_service_ext() -> MagicMock:
    """Mock service with all methods needed for cross-device endpoints."""
    svc = MagicMock()
    now = datetime.now(UTC)
    progress = {"upload_data": "2026-04-17T10:00:00Z"}

    svc.get_status.return_value = _make_status(
        golden_path_progress=progress, first_insight_dismissed_at=now
    )
    svc.update_golden_path_progress.return_value = _make_status(golden_path_progress=progress)
    svc.dismiss_first_insight.return_value = _make_status(first_insight_dismissed_at=now)
    return svc


@pytest.fixture()
def app_ext(mock_user, mock_service_ext):
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_onboarding_service] = lambda: mock_service_ext
    yield app
    app.dependency_overrides.clear()


@pytest.fixture()
def client_ext(app_ext):
    return TestClient(app_ext)


class TestGoldenPathProgressRoute:
    """PUT /api/v1/onboarding/golden-path-progress."""

    def test_returns_200_with_status(self, client_ext, mock_service_ext) -> None:
        resp = client_ext.put(
            "/api/v1/onboarding/golden-path-progress",
            json={"progress": {"upload_data": "2026-04-17T10:00:00Z"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "golden_path_progress" in data

    def test_calls_service_with_progress(self, client_ext, mock_service_ext) -> None:
        progress = {"upload_data": "2026-04-17T10:00:00Z", "validate": None}
        client_ext.put(
            "/api/v1/onboarding/golden-path-progress",
            json={"progress": progress},
        )
        mock_service_ext.update_golden_path_progress.assert_called_once()
        kwargs = mock_service_ext.update_golden_path_progress.call_args.kwargs
        assert kwargs["progress"] == progress

    def test_requires_progress_field(self, client_ext) -> None:
        resp = client_ext.put(
            "/api/v1/onboarding/golden-path-progress",
            json={},
        )
        assert resp.status_code == 422


class TestDismissFirstInsightRoute:
    """POST /api/v1/onboarding/dismiss-first-insight."""

    def test_returns_200_with_status(self, client_ext, mock_service_ext) -> None:
        resp = client_ext.post("/api/v1/onboarding/dismiss-first-insight")
        assert resp.status_code == 200
        data = resp.json()
        assert "first_insight_dismissed_at" in data

    def test_calls_service(self, client_ext, mock_service_ext) -> None:
        client_ext.post("/api/v1/onboarding/dismiss-first-insight")
        mock_service_ext.dismiss_first_insight.assert_called_once()
        kwargs = mock_service_ext.dismiss_first_insight.call_args.kwargs
        assert kwargs["user_id"] == "test-user"


class TestGetStatusIncludesNewFields:
    """GET /api/v1/onboarding/status returns golden_path_progress + first_insight_dismissed_at."""

    def test_status_contains_golden_path_progress(self, client_ext, mock_service_ext) -> None:
        resp = client_ext.get("/api/v1/onboarding/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "golden_path_progress" in data

    def test_status_contains_first_insight_dismissed_at(self, client_ext, mock_service_ext) -> None:
        resp = client_ext.get("/api/v1/onboarding/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "first_insight_dismissed_at" in data

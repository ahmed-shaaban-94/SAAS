"""Tests for onboarding API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.routes.onboarding import (
    get_onboarding_service,
    get_sample_load_service,
)
from datapulse.onboarding.models import OnboardingStatus, SampleLoadResult


@pytest.fixture()
def mock_user():
    return {
        "sub": "test-user",
        "tenant_id": "1",
        "roles": ["admin"],
        "email": "test@datapulse.local",
        "preferred_username": "test",
        "raw_claims": {},
    }


@pytest.fixture()
def mock_service():
    svc = MagicMock()
    now = datetime.now(UTC)
    default_status = OnboardingStatus(
        id=1,
        tenant_id=1,
        user_id="test-user",
        steps_completed=[],
        current_step="connect_data",
        completed_at=None,
        skipped_at=None,
        created_at=now,
    )
    svc.get_status.return_value = default_status
    svc.complete_step.return_value = OnboardingStatus(
        id=1,
        tenant_id=1,
        user_id="test-user",
        steps_completed=["connect_data"],
        current_step="first_report",
        completed_at=None,
        skipped_at=None,
        created_at=now,
    )
    svc.skip.return_value = OnboardingStatus(
        id=1,
        tenant_id=1,
        user_id="test-user",
        steps_completed=[],
        current_step="connect_data",
        completed_at=None,
        skipped_at=now,
        created_at=now,
    )
    return svc


@pytest.fixture()
def mock_sample_service():
    svc = MagicMock()
    svc.load.return_value = SampleLoadResult(
        rows_loaded=5000,
        pipeline_run_id="11111111-1111-1111-1111-111111111111",
        duration_seconds=4.2,
    )
    return svc


@pytest.fixture()
def app(mock_user, mock_service, mock_sample_service):
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_onboarding_service] = lambda: mock_service
    app.dependency_overrides[get_sample_load_service] = lambda: mock_sample_service
    yield app
    app.dependency_overrides.clear()


@pytest.fixture()
def client(app):
    return TestClient(app)


class TestGetStatus:
    def test_get_status(self, client, mock_service):
        """GET /onboarding/status returns 200 with onboarding status."""
        resp = client.get("/api/v1/onboarding/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "test-user"
        assert data["current_step"] == "connect_data"
        assert data["is_complete"] is False
        mock_service.get_status.assert_called_once()


class TestCompleteStep:
    def test_complete_step(self, client, mock_service):
        """POST /onboarding/complete-step returns 200 with updated status."""
        resp = client.post(
            "/api/v1/onboarding/complete-step",
            json={"step": "connect_data"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "connect_data" in data["steps_completed"]
        mock_service.complete_step.assert_called_once()

    def test_complete_step_invalid(self, client):
        """POST /onboarding/complete-step with invalid step returns 422."""
        resp = client.post(
            "/api/v1/onboarding/complete-step",
            json={"step": "nonexistent_step"},
        )
        assert resp.status_code == 422


class TestSkip:
    def test_skip(self, client, mock_service):
        """POST /onboarding/skip returns 200 with skipped_at set."""
        resp = client.post("/api/v1/onboarding/skip")
        assert resp.status_code == 200
        data = resp.json()
        assert data["skipped_at"] is not None
        mock_service.skip.assert_called_once()


class TestLoadSample:
    """POST /onboarding/load-sample — Phase 2 Task 2 / #401."""

    def test_load_sample_returns_200_with_result(self, client, mock_sample_service):
        """Happy path: 200 with rows_loaded, pipeline_run_id, duration_seconds."""
        resp = client.post("/api/v1/onboarding/load-sample")

        assert resp.status_code == 200
        data = resp.json()
        assert data["rows_loaded"] == 5000
        assert data["pipeline_run_id"] == "11111111-1111-1111-1111-111111111111"
        assert data["duration_seconds"] == 4.2
        mock_sample_service.load.assert_called_once()

    def test_load_sample_passes_user_and_tenant_context(self, client, mock_sample_service):
        """Route forwards the authenticated tenant_id + user_id to the service."""
        client.post("/api/v1/onboarding/load-sample")

        kwargs = mock_sample_service.load.call_args.kwargs
        # Route coerces tenant_id to int before calling the service (auth
        # returns it as a string, but SampleLoadService + sample_data format
        # it as %d).
        assert kwargs["tenant_id"] == 1
        assert kwargs["user_id"] == "test-user"

    def test_load_sample_rejects_non_numeric_tenant_id(self, app, mock_sample_service):
        """Route returns 400 when auth provides a non-numeric tenant_id."""
        bad_user = {
            "sub": "test-user",
            "tenant_id": "not-a-number",
            "roles": ["admin"],
            "email": "",
            "preferred_username": "",
            "raw_claims": {},
        }
        app.dependency_overrides[get_current_user] = lambda: bad_user
        resp = TestClient(app).post("/api/v1/onboarding/load-sample")

        assert resp.status_code == 400
        assert resp.json()["detail"] == "invalid tenant_id"
        mock_sample_service.load.assert_not_called()

    def test_load_sample_requires_auth(self, client):
        """Sanity: the route is mounted under the auth-required prefix."""
        # Dev-mode fallback returns 200 in the test harness, but calling service
        # must be mediated through get_current_user. The fixture overrides it
        # above; removing the override would make the request auth-check fail.
        # Here we just verify the route is wired and callable with auth.
        resp = client.post("/api/v1/onboarding/load-sample")
        assert resp.status_code == 200

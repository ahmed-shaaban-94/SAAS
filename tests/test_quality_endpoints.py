"""Tests for quality gate API endpoints — Phase 2.5.

Covers:
- GET /api/v1/pipeline/runs/{run_id}/quality
- POST /api/v1/pipeline/execute/quality-check

Both endpoints use the quality_api_client fixture which swaps out the real
QualityService with a MagicMock, preventing any real DB connections.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from datapulse.api import deps
from datapulse.api.app import create_app
from datapulse.pipeline.quality import (
    QualityCheckList,
    QualityCheckResponse,
    QualityCheckResult,
    QualityReport,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_check_response(**overrides) -> QualityCheckResponse:
    """Build a QualityCheckResponse with sane defaults, merging *overrides*."""
    defaults = dict(
        id=1,
        tenant_id=1,
        pipeline_run_id=uuid4(),
        check_name="row_count",
        stage="bronze",
        severity="error",
        passed=True,
        message="50000 rows loaded",
        details={"row_count": 50_000},
        checked_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return QualityCheckResponse(**defaults)


def _make_quality_report(
    run_id: UUID | None = None,
    stage: str = "bronze",
    gate_passed: bool = True,
    checks: list[QualityCheckResult] | None = None,
) -> QualityReport:
    """Build a QualityReport for use in mock return values."""
    if run_id is None:
        run_id = uuid4()
    if checks is None:
        checks = [
            QualityCheckResult(
                check_name="row_count",
                stage=stage,
                severity="error",
                passed=gate_passed,
                message=None if gate_passed else "No rows",
                details={"row_count": 50_000 if gate_passed else 0},
            )
        ]
    return QualityReport(
        pipeline_run_id=run_id,
        stage=stage,
        checks=checks,
        all_passed=all(c.passed for c in checks),
        gate_passed=gate_passed,
        checked_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def quality_api_client():
    """FastAPI TestClient with mocked QualityService and other pipeline deps."""
    from datapulse.api.auth import get_current_user, require_pipeline_token
    from datapulse.config import Settings, get_settings

    _dev_user = {
        "sub": "test-user",
        "email": "test@datapulse.local",
        "preferred_username": "test",
        "tenant_id": "1",
        "roles": ["admin"],
        "raw_claims": {},
    }
    clean_settings = Settings(_env_file=None, api_key="test-api-key", database_url="")

    app = create_app()
    mock_quality_svc = MagicMock()

    # Override all deps so no real DB connection is attempted
    app.dependency_overrides[get_settings] = lambda: clean_settings
    app.dependency_overrides[deps.get_quality_service] = lambda: mock_quality_svc
    app.dependency_overrides[deps.get_tenant_session] = lambda: MagicMock()
    app.dependency_overrides[deps.get_pipeline_service] = lambda: MagicMock()
    app.dependency_overrides[deps.get_pipeline_executor] = lambda: MagicMock()
    app.dependency_overrides[get_current_user] = lambda: _dev_user
    app.dependency_overrides[require_pipeline_token] = lambda: None

    client = TestClient(app, raise_server_exceptions=True, headers={"X-API-Key": "test-api-key"})
    yield client, mock_quality_svc
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# TestGetQualityChecks — GET /api/v1/pipeline/runs/{run_id}/quality
# ---------------------------------------------------------------------------


class TestGetQualityChecks:
    """GET /api/v1/pipeline/runs/{run_id}/quality"""

    _BASE = "/api/v1/pipeline/runs/{run_id}/quality"

    def _url(self, run_id: UUID, **params) -> str:
        base = self._BASE.format(run_id=run_id)
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            return f"{base}?{qs}"
        return base

    def test_returns_checks_200(self, quality_api_client):
        """Happy path: service returns 2 checks → 200 with items."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        item1 = _make_check_response(id=1, pipeline_run_id=run_id, check_name="row_count")
        item2 = _make_check_response(id=2, pipeline_run_id=run_id, check_name="row_delta")
        mock_svc.get_checks.return_value = QualityCheckList(items=[item1, item2], total=2)

        response = client.get(self._url(run_id))

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["check_name"] == "row_count"
        assert data["items"][1]["check_name"] == "row_delta"

    def test_empty_list_200(self, quality_api_client):
        """No checks persisted yet → 200 with total=0 and empty items."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        mock_svc.get_checks.return_value = QualityCheckList(items=[], total=0)

        response = client.get(self._url(run_id))

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_filter_by_stage_bronze(self, quality_api_client):
        """?stage=bronze → service called with stage='bronze'."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        mock_svc.get_checks.return_value = QualityCheckList(items=[], total=0)

        response = client.get(self._url(run_id, stage="bronze"))

        assert response.status_code == 200
        mock_svc.get_checks.assert_called_once_with(run_id, "bronze")

    def test_filter_by_stage_silver(self, quality_api_client):
        """?stage=silver → service called with stage='silver'."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        mock_svc.get_checks.return_value = QualityCheckList(items=[], total=0)

        response = client.get(self._url(run_id, stage="silver"))

        assert response.status_code == 200
        mock_svc.get_checks.assert_called_once_with(run_id, "silver")

    def test_filter_by_stage_gold(self, quality_api_client):
        """?stage=gold → service called with stage='gold'."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        mock_svc.get_checks.return_value = QualityCheckList(items=[], total=0)

        response = client.get(self._url(run_id, stage="gold"))

        assert response.status_code == 200
        mock_svc.get_checks.assert_called_once_with(run_id, "gold")

    def test_no_stage_filter_calls_service_with_none(self, quality_api_client):
        """No ?stage param → service called with stage=None."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        mock_svc.get_checks.return_value = QualityCheckList(items=[], total=0)

        client.get(self._url(run_id))

        mock_svc.get_checks.assert_called_once_with(run_id, None)

    def test_invalid_stage_returns_422(self, quality_api_client):
        """?stage=invalid → 422, no service call."""
        client, mock_svc = quality_api_client
        run_id = uuid4()

        response = client.get(self._url(run_id, stage="invalid"))

        assert response.status_code == 422
        mock_svc.get_checks.assert_not_called()

    def test_invalid_stage_platinum_returns_422(self, quality_api_client):
        """?stage=platinum → 422."""
        client, mock_svc = quality_api_client
        run_id = uuid4()

        response = client.get(self._url(run_id, stage="platinum"))

        assert response.status_code == 422

    def test_response_includes_passed_field(self, quality_api_client):
        """Response items include the passed boolean field."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        item = _make_check_response(pipeline_run_id=run_id, passed=False, check_name="row_count")
        mock_svc.get_checks.return_value = QualityCheckList(items=[item], total=1)

        response = client.get(self._url(run_id))

        data = response.json()
        assert data["items"][0]["passed"] is False

    def test_response_item_fields_complete(self, quality_api_client):
        """All expected fields are present in each response item."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        item = _make_check_response(pipeline_run_id=run_id)
        mock_svc.get_checks.return_value = QualityCheckList(items=[item], total=1)

        response = client.get(self._url(run_id))

        item_data = response.json()["items"][0]
        for field in (
            "id",
            "tenant_id",
            "pipeline_run_id",
            "check_name",
            "stage",
            "severity",
            "passed",
            "message",
            "details",
            "checked_at",
        ):
            assert field in item_data, f"Field '{field}' missing from response item"

    def test_invalid_run_id_format_returns_422(self, quality_api_client):
        """Malformed UUID in path → FastAPI returns 422."""
        client, mock_svc = quality_api_client

        response = client.get("/api/v1/pipeline/runs/not-a-uuid/quality")

        assert response.status_code == 422

    def test_service_returns_checks_with_null_message(self, quality_api_client):
        """Null message field is serialized correctly (not omitted)."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        item = _make_check_response(pipeline_run_id=run_id, message=None)
        mock_svc.get_checks.return_value = QualityCheckList(items=[item], total=1)

        response = client.get(self._url(run_id))

        assert response.status_code == 200
        assert response.json()["items"][0]["message"] is None


# ---------------------------------------------------------------------------
# TestExecuteQualityCheck — POST /api/v1/pipeline/execute/quality-check
# ---------------------------------------------------------------------------


class TestExecuteQualityCheck:
    """POST /api/v1/pipeline/execute/quality-check"""

    _URL = "/api/v1/pipeline/execute/quality-check"

    def test_runs_checks_bronze_gate_passed(self, quality_api_client):
        """Bronze stage, all checks pass → 200 with gate_passed=True."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        report = _make_quality_report(run_id=run_id, stage="bronze", gate_passed=True)
        mock_svc.run_checks_for_stage.return_value = report

        response = client.post(
            self._URL,
            json={"run_id": str(run_id), "stage": "bronze", "tenant_id": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["gate_passed"] is True
        assert data["stage"] == "bronze"
        assert data["pipeline_run_id"] == str(run_id)

    def test_runs_checks_silver_stage(self, quality_api_client):
        """Silver stage dispatched correctly."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        report = _make_quality_report(run_id=run_id, stage="silver", gate_passed=True)
        mock_svc.run_checks_for_stage.return_value = report

        response = client.post(
            self._URL,
            json={"run_id": str(run_id), "stage": "silver"},
        )

        assert response.status_code == 200
        assert response.json()["stage"] == "silver"

    def test_runs_checks_gold_stage(self, quality_api_client):
        """Gold stage dispatched correctly."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        report = _make_quality_report(run_id=run_id, stage="gold", gate_passed=True)
        mock_svc.run_checks_for_stage.return_value = report

        response = client.post(
            self._URL,
            json={"run_id": str(run_id), "stage": "gold"},
        )

        assert response.status_code == 200
        assert response.json()["stage"] == "gold"

    def test_gate_blocks_on_error_still_200(self, quality_api_client):
        """gate_passed=False → still HTTP 200 (caller must inspect gate_passed)."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        report = _make_quality_report(run_id=run_id, stage="bronze", gate_passed=False)
        mock_svc.run_checks_for_stage.return_value = report

        response = client.post(
            self._URL,
            json={"run_id": str(run_id), "stage": "bronze"},
        )

        assert response.status_code == 200
        assert response.json()["gate_passed"] is False

    def test_invalid_stage_returns_422(self, quality_api_client):
        """Unknown stage → 422, no service call."""
        client, mock_svc = quality_api_client
        run_id = uuid4()

        response = client.post(
            self._URL,
            json={"run_id": str(run_id), "stage": "invalid"},
        )

        assert response.status_code == 422
        mock_svc.run_checks_for_stage.assert_not_called()

    def test_missing_run_id_returns_422(self, quality_api_client):
        """run_id is required — omitting it → 422."""
        client, mock_svc = quality_api_client

        response = client.post(
            self._URL,
            json={"stage": "bronze"},
        )

        assert response.status_code == 422
        mock_svc.run_checks_for_stage.assert_not_called()

    def test_missing_stage_returns_422(self, quality_api_client):
        """stage is required — omitting it → 422."""
        client, mock_svc = quality_api_client

        response = client.post(
            self._URL,
            json={"run_id": str(uuid4())},
        )

        assert response.status_code == 422

    def test_service_called_with_correct_args(self, quality_api_client):
        """Verifies run_checks_for_stage receives tenant_id from JWT, not body."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        report = _make_quality_report(run_id=run_id, stage="bronze")
        mock_svc.run_checks_for_stage.return_value = report

        # body.tenant_id=7 is ignored — tenant derived from JWT (mock user="1")
        client.post(
            self._URL,
            json={"run_id": str(run_id), "stage": "bronze", "tenant_id": 7},
        )

        mock_svc.run_checks_for_stage.assert_called_once_with(
            run_id=run_id,
            stage="bronze",
            tenant_id=1,
        )

    def test_default_tenant_id_is_1(self, quality_api_client):
        """When tenant_id is omitted from body it defaults to 1."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        report = _make_quality_report(run_id=run_id, stage="bronze")
        mock_svc.run_checks_for_stage.return_value = report

        client.post(
            self._URL,
            json={"run_id": str(run_id), "stage": "bronze"},
        )

        call_kwargs = mock_svc.run_checks_for_stage.call_args.kwargs
        assert call_kwargs["tenant_id"] == 1

    def test_report_contains_checks_list(self, quality_api_client):
        """Response includes the checks list with at least one entry."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        checks = [
            QualityCheckResult(
                check_name="row_count",
                stage="bronze",
                severity="error",
                passed=True,
                message=None,
                details={"row_count": 1000},
            ),
            QualityCheckResult(
                check_name="row_delta",
                stage="bronze",
                severity="warn",
                passed=True,
                message="No previous run",
                details={},
            ),
        ]
        report = _make_quality_report(run_id=run_id, stage="bronze", checks=checks)
        mock_svc.run_checks_for_stage.return_value = report

        response = client.post(
            self._URL,
            json={"run_id": str(run_id), "stage": "bronze"},
        )

        data = response.json()
        assert len(data["checks"]) == 2
        check_names = [c["check_name"] for c in data["checks"]]
        assert "row_count" in check_names
        assert "row_delta" in check_names

    def test_response_all_passed_field(self, quality_api_client):
        """Response contains all_passed boolean."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        report = _make_quality_report(run_id=run_id, stage="silver", gate_passed=True)
        mock_svc.run_checks_for_stage.return_value = report

        response = client.post(
            self._URL,
            json={"run_id": str(run_id), "stage": "silver"},
        )

        assert "all_passed" in response.json()

    def test_response_checked_at_field(self, quality_api_client):
        """Response contains checked_at timestamp."""
        client, mock_svc = quality_api_client
        run_id = uuid4()
        report = _make_quality_report(run_id=run_id, stage="bronze")
        mock_svc.run_checks_for_stage.return_value = report

        response = client.post(
            self._URL,
            json={"run_id": str(run_id), "stage": "bronze"},
        )

        assert "checked_at" in response.json()

    def test_malformed_run_id_returns_422(self, quality_api_client):
        """Non-UUID run_id in JSON body → 422 validation error."""
        client, mock_svc = quality_api_client

        response = client.post(
            self._URL,
            json={"run_id": "not-a-uuid", "stage": "bronze"},
        )

        assert response.status_code == 422

    def test_empty_body_returns_422(self, quality_api_client):
        """Empty JSON body → 422."""
        client, mock_svc = quality_api_client

        response = client.post(self._URL, json={})

        assert response.status_code == 422

    def test_empty_stage_string_returns_422(self, quality_api_client):
        """stage='' is not a valid stage → 422."""
        client, mock_svc = quality_api_client

        response = client.post(
            self._URL,
            json={"run_id": str(uuid4()), "stage": ""},
        )

        assert response.status_code == 422

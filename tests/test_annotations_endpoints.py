"""Tests for annotation API endpoints."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.routes.annotations import get_annotation_repo


def _make_row(**overrides):
    base = {
        "id": 1,
        "chart_id": "daily_trend",
        "data_point": "2024-01-15",
        "note": "Test",
        "color": "#D97706",
        "user_id": "test-user",
        "created_at": datetime.now(UTC),
    }
    base.update(overrides)
    return base


@pytest.fixture()
def mock_user():
    return {"sub": "test-user", "tenant_id": "1", "roles": ["admin"]}


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    repo.list_by_chart.return_value = [_make_row()]
    repo.create.return_value = _make_row()
    repo.delete.return_value = True
    return repo


@pytest.fixture()
def client(mock_user, mock_repo):
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_annotation_repo] = lambda: mock_repo
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_annotations(client, mock_repo):
    res = client.get("/api/v1/annotations?chart_id=daily_trend")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_list_requires_chart_id(client):
    res = client.get("/api/v1/annotations")
    assert res.status_code == 422


def test_create_annotation(client, mock_repo):
    res = client.post(
        "/api/v1/annotations",
        json={
            "chart_id": "daily_trend",
            "data_point": "2024-01-15",
            "note": "New",
            "color": "#4F46E5",
        },
    )
    assert res.status_code == 201
    mock_repo.create.assert_called_once()


def test_delete_annotation(client, mock_repo):
    res = client.delete("/api/v1/annotations/1")
    assert res.status_code == 204


def test_delete_not_found(client, mock_repo):
    mock_repo.delete.return_value = False
    res = client.delete("/api/v1/annotations/999")
    assert res.status_code == 404

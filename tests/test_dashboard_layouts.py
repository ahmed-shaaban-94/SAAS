"""Tests for dashboard layout API endpoints."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session


@pytest.fixture()
def mock_user():
    return {"sub": "test-user", "tenant_id": "1", "roles": ["admin"]}


@pytest.fixture()
def mock_session():
    return MagicMock()


@pytest.fixture()
def client(mock_user, mock_session):
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_tenant_session] = lambda: mock_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_layout_empty(client, mock_session):
    mock_session.execute.return_value.scalar.return_value = None
    res = client.get("/api/v1/dashboard/layout")
    assert res.status_code == 200
    assert res.json() == {"layout": []}


def test_get_layout_saved(client, mock_session):
    saved = [{"i": "kpi-grid", "x": 0, "y": 0, "w": 12, "h": 3}]
    mock_session.execute.return_value.scalar.return_value = saved
    res = client.get("/api/v1/dashboard/layout")
    assert res.status_code == 200
    assert res.json()["layout"] == saved


def test_save_layout(client, mock_session):
    layout = [{"i": "kpi-grid", "x": 0, "y": 0, "w": 12, "h": 3}]
    res = client.put("/api/v1/dashboard/layout", json={"layout": layout})
    assert res.status_code == 200
    assert res.json()["layout"] == layout
    mock_session.execute.assert_called_once()
    mock_session.flush.assert_called_once()


def test_save_layout_empty(client, mock_session):
    res = client.put("/api/v1/dashboard/layout", json={"layout": []})
    assert res.status_code == 200
    assert res.json()["layout"] == []

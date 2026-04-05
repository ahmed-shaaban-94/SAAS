"""Tests for notification center API endpoints."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.routes.notifications import get_notification_service
from datapulse.notifications_center.models import NotificationCount, NotificationResponse


@pytest.fixture()
def mock_user():
    return {"sub": "test-user", "tenant_id": "1", "roles": ["admin"]}


@pytest.fixture()
def mock_service():
    svc = MagicMock()
    now = datetime.now(timezone.utc)
    svc.list_notifications.return_value = [
        NotificationResponse(id=1, type="info", title="Hi", message="Hello", link=None, read=False, created_at=now),
    ]
    svc.unread_count.return_value = NotificationCount(unread=3)
    return svc


@pytest.fixture()
def client(mock_user, mock_service):
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_notification_service] = lambda: mock_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_notifications(client, mock_service):
    res = client.get("/api/v1/notifications")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["title"] == "Hi"


def test_list_notifications_unread_only(client, mock_service):
    client.get("/api/v1/notifications?unread_only=true&limit=5")
    mock_service.list_notifications.assert_called_once_with("test-user", True, 5)


def test_unread_count(client, mock_service):
    res = client.get("/api/v1/notifications/count")
    assert res.status_code == 200
    assert res.json()["unread"] == 3


def test_mark_read(client, mock_service):
    res = client.post("/api/v1/notifications/1/read")
    assert res.status_code == 204
    mock_service.mark_read.assert_called_once_with(1, "test-user")


def test_mark_all_read(client, mock_service):
    res = client.post("/api/v1/notifications/read-all")
    assert res.status_code == 204
    mock_service.mark_all_read.assert_called_once_with("test-user")

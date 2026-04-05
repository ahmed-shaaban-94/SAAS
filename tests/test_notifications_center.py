"""Tests for NotificationService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from datapulse.notifications_center.models import NotificationCount, NotificationResponse
from datapulse.notifications_center.service import NotificationService


def _make_row(**overrides):
    base = {
        "id": 1,
        "type": "info",
        "title": "Test",
        "message": "Test message",
        "link": None,
        "read": False,
        "created_at": datetime.now(UTC),
    }
    base.update(overrides)
    return base


def test_list_notifications():
    repo = MagicMock()
    repo.list_notifications.return_value = [_make_row(), _make_row(id=2)]
    svc = NotificationService(repo)
    result = svc.list_notifications("user1")
    assert len(result) == 2
    assert isinstance(result[0], NotificationResponse)
    repo.list_notifications.assert_called_once_with("user1", False, 20)


def test_list_notifications_unread_only():
    repo = MagicMock()
    repo.list_notifications.return_value = [_make_row()]
    svc = NotificationService(repo)
    svc.list_notifications("user1", unread_only=True, limit=5)
    repo.list_notifications.assert_called_once_with("user1", True, 5)


def test_unread_count():
    repo = MagicMock()
    repo.unread_count.return_value = 7
    svc = NotificationService(repo)
    result = svc.unread_count("user1")
    assert isinstance(result, NotificationCount)
    assert result.unread == 7


def test_mark_read():
    repo = MagicMock()
    svc = NotificationService(repo)
    svc.mark_read(42, "user1")
    repo.mark_read.assert_called_once_with(42, "user1")


def test_mark_all_read():
    repo = MagicMock()
    svc = NotificationService(repo)
    svc.mark_all_read("user1")
    repo.mark_all_read.assert_called_once_with("user1")


def test_create_notification():
    repo = MagicMock()
    repo.create.return_value = _make_row(type="success", title="Pipeline done")
    svc = NotificationService(repo)
    result = svc.create_notification(1, "success", "Pipeline done", "Completed OK")
    assert isinstance(result, NotificationResponse)
    assert result.title == "Pipeline done"
    repo.create.assert_called_once_with(1, "success", "Pipeline done", "Completed OK", None, None)

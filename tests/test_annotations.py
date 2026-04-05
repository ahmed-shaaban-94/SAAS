"""Tests for AnnotationRepository."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from datapulse.annotations.repository import AnnotationRepository


def _make_row(**overrides):
    base = {
        "id": 1,
        "chart_id": "daily_trend",
        "data_point": "2024-01-15",
        "note": "Ramadan sale started",
        "color": "#D97706",
        "user_id": "user1",
        "created_at": datetime.now(UTC),
    }
    base.update(overrides)
    return base


def test_list_by_chart():
    session = MagicMock()
    session.execute.return_value.mappings.return_value.all.return_value = [
        _make_row(),
        _make_row(id=2, data_point="2024-02-01"),
    ]
    repo = AnnotationRepository(session)
    result = repo.list_by_chart("daily_trend")
    assert len(result) == 2
    assert result[0]["chart_id"] == "daily_trend"


def test_list_by_chart_empty():
    session = MagicMock()
    session.execute.return_value.mappings.return_value.all.return_value = []
    repo = AnnotationRepository(session)
    assert repo.list_by_chart("nonexistent") == []


def test_create():
    session = MagicMock()
    session.execute.return_value.mappings.return_value.first.return_value = _make_row()
    repo = AnnotationRepository(session)
    result = repo.create(1, "user1", "daily_trend", "2024-01-15", "Test", "#D97706")
    assert result["note"] == "Ramadan sale started"
    session.flush.assert_called_once()


def test_create_no_row():
    session = MagicMock()
    session.execute.return_value.mappings.return_value.first.return_value = None
    repo = AnnotationRepository(session)
    assert repo.create(1, "user1", "x", "y", "z", "#000000") == {}


def test_delete_success():
    session = MagicMock()
    session.execute.return_value.rowcount = 1
    repo = AnnotationRepository(session)
    assert repo.delete(1, "user1") is True


def test_delete_not_found():
    session = MagicMock()
    session.execute.return_value.rowcount = 0
    repo = AnnotationRepository(session)
    assert repo.delete(999, "user1") is False

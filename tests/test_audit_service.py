"""Tests for audit log service — covers the SQL date filter crash fix."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from datapulse.audit.models import AuditLogPage
from datapulse.audit.repository import AuditRepository
from datapulse.audit.service import AuditService


@pytest.fixture()
def mock_repo():
    return create_autospec(AuditRepository, instance=True)


@pytest.fixture()
def service(mock_repo):
    return AuditService(mock_repo)


class TestListEntries:
    def test_empty_result(self, service, mock_repo):
        mock_repo.list.return_value = ([], 0)
        result = service.list_entries()
        assert isinstance(result, AuditLogPage)
        assert result.items == []
        assert result.total == 0

    def test_with_entries(self, service, mock_repo):
        mock_repo.list.return_value = (
            [
                {
                    "id": 1,
                    "action": "READ",
                    "endpoint": "/api/v1/sales",
                    "method": "GET",
                    "ip_address": "127.0.0.1",
                    "user_id": "test-user",
                    "response_status": 200,
                    "duration_ms": 45.2,
                    "created_at": "2026-04-12T10:00:00+00:00",
                },
            ],
            1,
        )
        result = service.list_entries(action="READ", page=1, page_size=10)
        assert len(result.items) == 1
        assert result.items[0].action == "READ"
        assert result.total == 1

    def test_with_date_filters(self, service, mock_repo):
        """Verify date filters are passed through without crash (was: CAST syntax fix)."""
        mock_repo.list.return_value = ([], 0)
        result = service.list_entries(
            start_date="2026-04-01",
            end_date="2026-04-12",
        )
        mock_repo.list.assert_called_once_with(
            action=None,
            endpoint=None,
            method=None,
            user_id=None,
            start_date="2026-04-01",
            end_date="2026-04-12",
            page=1,
            page_size=50,
        )
        assert result.total == 0


class TestRepositoryDateSQL:
    def test_cast_syntax_in_date_conditions(self):
        """The SQL must use CAST() not :: to avoid psycopg2 param conflicts."""
        import inspect

        source = inspect.getsource(AuditRepository.list)
        # Must use CAST syntax, not :: (which conflicts with :param)
        assert "CAST(:start_date AS timestamptz)" in source
        assert "CAST(:end_date AS date)" in source
        # Must NOT have the old :: syntax
        assert ":start_date::timestamptz" not in source
        assert ":end_date::date" not in source

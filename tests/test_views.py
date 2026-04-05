"""Tests for ViewsService business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest
from fastapi import HTTPException

from datapulse.views.models import SavedViewCreate, SavedViewResponse, SavedViewUpdate
from datapulse.views.repository import ViewsRepository
from datapulse.views.service import ViewsService


@pytest.fixture()
def mock_repo():
    repo = create_autospec(ViewsRepository, instance=True)
    repo.MAX_VIEWS_PER_USER = ViewsRepository.MAX_VIEWS_PER_USER
    return repo


@pytest.fixture()
def service(mock_repo):
    return ViewsService(mock_repo)


NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)

SAMPLE_VIEW = {
    "id": 1,
    "name": "My View",
    "page_path": "/dashboard",
    "filters": {"date_range": "30d"},
    "is_default": False,
    "created_at": NOW,
}


class TestListViews:
    def test_list_views(self, service, mock_repo):
        """Returns list of SavedViewResponse objects."""
        mock_repo.list_views.return_value = [SAMPLE_VIEW]

        result = service.list_views("user-1")

        assert len(result) == 1
        assert isinstance(result[0], SavedViewResponse)
        assert result[0].name == "My View"
        mock_repo.list_views.assert_called_once_with("user-1")

    def test_list_views_empty(self, service, mock_repo):
        """Empty list when user has no views."""
        mock_repo.list_views.return_value = []

        result = service.list_views("user-1")

        assert result == []


class TestCreateView:
    def test_create_view(self, service, mock_repo):
        """Creates and returns a SavedViewResponse."""
        mock_repo.count_views.return_value = 0
        mock_repo.create_view.return_value = SAMPLE_VIEW

        data = SavedViewCreate(
            name="My View",
            page_path="/dashboard",
            filters={"date_range": "30d"},
        )
        result = service.create_view(1, "user-1", data)

        assert isinstance(result, SavedViewResponse)
        assert result.id == 1
        mock_repo.create_view.assert_called_once_with(
            1, "user-1", "My View", "/dashboard", {"date_range": "30d"}, False
        )

    def test_create_view_max_limit(self, service, mock_repo):
        """Raises HTTPException 422 when at max views."""
        mock_repo.count_views.return_value = 20
        mock_repo.MAX_VIEWS_PER_USER = 20

        data = SavedViewCreate(name="One Too Many")
        with pytest.raises(HTTPException) as exc_info:
            service.create_view(1, "user-1", data)

        assert exc_info.value.status_code == 422
        assert "Maximum" in str(exc_info.value.detail)
        mock_repo.create_view.assert_not_called()


class TestUpdateView:
    def test_update_view(self, service, mock_repo):
        """Updates and returns a SavedViewResponse."""
        updated = {**SAMPLE_VIEW, "name": "Updated View"}
        mock_repo.update_view.return_value = updated

        data = SavedViewUpdate(name="Updated View")
        result = service.update_view(1, "user-1", data)

        assert result.name == "Updated View"
        mock_repo.update_view.assert_called_once_with(1, "user-1", name="Updated View")

    def test_update_view_not_found(self, service, mock_repo):
        """Raises HTTPException 404 when view not found."""
        mock_repo.update_view.return_value = None

        data = SavedViewUpdate(name="Ghost")
        with pytest.raises(HTTPException) as exc_info:
            service.update_view(999, "user-1", data)

        assert exc_info.value.status_code == 404


class TestDeleteView:
    def test_delete_view(self, service, mock_repo):
        """Successful delete does not raise."""
        mock_repo.delete_view.return_value = True

        service.delete_view(1, "user-1")

        mock_repo.delete_view.assert_called_once_with(1, "user-1")

    def test_delete_view_not_found(self, service, mock_repo):
        """Raises HTTPException 404 when view not found."""
        mock_repo.delete_view.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            service.delete_view(999, "user-1")

        assert exc_info.value.status_code == 404

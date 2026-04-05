"""Service layer for saved views."""

from __future__ import annotations

from fastapi import HTTPException

from datapulse.views.models import SavedViewCreate, SavedViewResponse, SavedViewUpdate
from datapulse.views.repository import ViewsRepository


class ViewsService:
    def __init__(self, repo: ViewsRepository) -> None:
        self._repo = repo

    def list_views(self, user_id: str) -> list[SavedViewResponse]:
        rows = self._repo.list_views(user_id)
        return [SavedViewResponse(**r) for r in rows]

    def create_view(self, tenant_id: int, user_id: str, data: SavedViewCreate) -> SavedViewResponse:
        count = self._repo.count_views(user_id)
        if count >= self._repo.MAX_VIEWS_PER_USER:
            raise HTTPException(
                status_code=422,
                detail=f"Maximum {self._repo.MAX_VIEWS_PER_USER} saved views reached",
            )
        row = self._repo.create_view(
            tenant_id, user_id, data.name, data.page_path, data.filters, data.is_default
        )
        return SavedViewResponse(**row)

    def update_view(self, view_id: int, user_id: str, data: SavedViewUpdate) -> SavedViewResponse:
        row = self._repo.update_view(view_id, user_id, **data.model_dump(exclude_none=True))
        if not row:
            raise HTTPException(status_code=404, detail="View not found")
        return SavedViewResponse(**row)

    def delete_view(self, view_id: int, user_id: str) -> None:
        deleted = self._repo.delete_view(view_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="View not found")

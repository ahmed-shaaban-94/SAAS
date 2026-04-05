"""Saved views API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.orm import Session

from datapulse.api.auth import get_current_user
from datapulse.api.deps import CurrentUser, get_tenant_session
from datapulse.api.limiter import limiter
from datapulse.views.models import SavedViewCreate, SavedViewResponse, SavedViewUpdate
from datapulse.views.repository import ViewsRepository
from datapulse.views.service import ViewsService

router = APIRouter(
    prefix="/views",
    tags=["views"],
    dependencies=[Depends(get_current_user)],
)


def get_views_service(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> ViewsService:
    return ViewsService(ViewsRepository(session))


ServiceDep = Annotated[ViewsService, Depends(get_views_service)]


@router.get("", response_model=list[SavedViewResponse])
@limiter.limit("30/minute")
def list_views(request: Request, service: ServiceDep, user: CurrentUser):
    return service.list_views(user["sub"])


@router.post("", response_model=SavedViewResponse, status_code=201)
@limiter.limit("10/minute")
def create_view(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
    body: SavedViewCreate,
):
    return service.create_view(int(user.get("tenant_id", "1")), user["sub"], body)


@router.patch("/{view_id}", response_model=SavedViewResponse)
@limiter.limit("10/minute")
def update_view(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
    body: SavedViewUpdate,
    view_id: int = Path(),
):
    return service.update_view(view_id, user["sub"], body)


@router.delete("/{view_id}", status_code=204)
@limiter.limit("10/minute")
def delete_view(
    request: Request,
    service: ServiceDep,
    user: CurrentUser,
    view_id: int = Path(),
):
    service.delete_view(view_id, user["sub"])

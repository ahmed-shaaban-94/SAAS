"""Chart annotations API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.orm import Session

from datapulse.annotations.models import AnnotationCreate, AnnotationResponse
from datapulse.annotations.repository import AnnotationRepository
from datapulse.api.auth import get_current_user
from datapulse.api.deps import CurrentUser, get_tenant_session
from datapulse.api.limiter import limiter

router = APIRouter(
    prefix="/annotations",
    tags=["annotations"],
    dependencies=[Depends(get_current_user)],
)


def get_annotation_repo(
    session: Annotated[Session, Depends(get_tenant_session)],
) -> AnnotationRepository:
    return AnnotationRepository(session)


RepoDep = Annotated[AnnotationRepository, Depends(get_annotation_repo)]


@router.get("", response_model=list[AnnotationResponse])
@limiter.limit("30/minute")
def list_annotations(
    request: Request,
    repo: RepoDep,
    chart_id: str = Query(...),
) -> list[AnnotationResponse]:
    rows = repo.list_by_chart(chart_id)
    return [AnnotationResponse(**r) for r in rows]


@router.post("", response_model=AnnotationResponse, status_code=201)
@limiter.limit("10/minute")
def create_annotation(
    request: Request,
    repo: RepoDep,
    user: CurrentUser,
    body: AnnotationCreate,
) -> AnnotationResponse:
    row = repo.create(
        int(user.get("tenant_id", "1")),
        user["sub"],
        body.chart_id,
        body.data_point,
        body.note,
        body.color,
    )
    return AnnotationResponse(**row)


@router.delete("/{annotation_id}", status_code=204)
@limiter.limit("10/minute")
def delete_annotation(
    request: Request,
    repo: RepoDep,
    user: CurrentUser,
    annotation_id: int = Path(),
) -> None:
    deleted = repo.delete(annotation_id, user["sub"])
    if not deleted:
        raise HTTPException(404, "Annotation not found")

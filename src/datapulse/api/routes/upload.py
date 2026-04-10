"""File upload API endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel

from datapulse.api.auth import get_current_user
from datapulse.api.limiter import limiter
from datapulse.rbac.dependencies import require_permission
from datapulse.upload.models import PreviewResult, UploadedFile
from datapulse.upload.service import UploadService

router = APIRouter(
    prefix="/upload",
    tags=["upload"],
    dependencies=[Depends(require_permission("pipeline:run"))],
)

UserDep = Annotated[dict[str, Any], Depends(get_current_user)]


def _get_service(user: UserDep) -> UploadService:
    """Create an UploadService scoped to the current user's tenant."""
    return UploadService(tenant_id=user.get("tenant_id", "0"))


class ConfirmRequest(BaseModel):
    file_ids: list[str]


class ConfirmResponse(BaseModel):
    moved_files: list[str]


@router.post("/files", response_model=list[UploadedFile])
@limiter.limit("10/minute")
async def upload_files(
    request: Request,
    files: list[UploadFile],
    service: Annotated[UploadService, Depends(_get_service)],
) -> list[UploadedFile]:
    """Upload one or more files for preview before import."""
    results = []
    for f in files:
        if not f.filename:
            continue
        content = await f.read()
        max_size = 100 * 1024 * 1024  # 100MB
        if len(content) > max_size:
            raise HTTPException(413, f"File {f.filename} exceeds 100MB limit")
        try:
            result = service.save_temp_file(f.filename, content)
            results.append(result)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
    return results


@router.get("/preview/{file_id}", response_model=PreviewResult)
@limiter.limit("10/minute")
def preview_file(
    request: Request,
    file_id: str,
    service: Annotated[UploadService, Depends(_get_service)],
) -> PreviewResult:
    """Preview first 100 rows of an uploaded file."""
    try:
        return service.preview_file(file_id)
    except FileNotFoundError as e:
        raise HTTPException(404, "File not found") from e


@router.post("/confirm", response_model=ConfirmResponse)
@limiter.limit("5/minute")
def confirm_upload(
    request: Request,
    body: ConfirmRequest,
    service: Annotated[UploadService, Depends(_get_service)],
) -> ConfirmResponse:
    """Move confirmed files to the raw data directory."""
    moved = service.confirm_upload(body.file_ids)
    return ConfirmResponse(moved_files=moved)

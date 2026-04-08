"""File upload API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel

from datapulse.api.auth import get_current_user
from datapulse.api.limiter import limiter
from datapulse.upload.models import PreviewResult, UploadedFile
from datapulse.upload.service import UploadService

router = APIRouter(
    prefix="/upload",
    tags=["upload"],
    dependencies=[Depends(get_current_user)],
)

_service = UploadService()


class ConfirmRequest(BaseModel):
    file_ids: list[str]


class ConfirmResponse(BaseModel):
    moved_files: list[str]


@router.post("/files", response_model=list[UploadedFile])
@limiter.limit("10/minute")
async def upload_files(request: Request, files: list[UploadFile]) -> list[UploadedFile]:
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
            result = _service.save_temp_file(f.filename, content)
            results.append(result)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
    return results


@router.get("/preview/{file_id}", response_model=PreviewResult)
@limiter.limit("10/minute")
def preview_file(request: Request, file_id: str) -> PreviewResult:
    """Preview first 100 rows of an uploaded file."""
    try:
        return _service.preview_file(file_id)
    except FileNotFoundError as e:
        raise HTTPException(404, "File not found") from e


@router.post("/confirm", response_model=ConfirmResponse)
@limiter.limit("5/minute")
def confirm_upload(request: Request, body: ConfirmRequest) -> ConfirmResponse:
    """Move confirmed files to the raw data directory."""
    moved = _service.confirm_upload(body.file_ids)
    return ConfirmResponse(moved_files=moved)

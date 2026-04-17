"""File upload API endpoints."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel

from datapulse.api.auth import get_current_user
from datapulse.api.limiter import limiter
from datapulse.rbac.dependencies import require_permission
from datapulse.upload.models import InventoryPreviewResult, PreviewResult, UploadedFile
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


class InventoryConfirmRequest(BaseModel):
    file_ids: list[str]
    target_dir: str | None = None


async def _iter_upload_chunks(
    upload: UploadFile,
    *,
    max_size: int,
    chunk_size: int,
) -> AsyncIterator[bytes]:
    """Yield upload chunks while enforcing the request size ceiling."""
    if upload.size and upload.size > max_size:
        raise HTTPException(413, f"File {upload.filename} exceeds 100MB limit")

    total = 0
    while True:
        chunk = await upload.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise HTTPException(413, f"File {upload.filename} exceeds 100MB limit")
        yield chunk


async def _close_upload_file(upload: UploadFile) -> None:
    """Close UploadFile objects without assuming the test double is async-aware."""
    close_result = upload.close()
    if inspect.isawaitable(close_result):
        await close_result


@router.post("/files", response_model=list[UploadedFile])
@limiter.limit("10/minute")
async def upload_files(
    request: Request,
    files: list[UploadFile],
    service: Annotated[UploadService, Depends(_get_service)],
) -> list[UploadedFile]:
    """Upload one or more files for preview before import."""
    results = []
    max_size = 100 * 1024 * 1024  # 100MB
    chunk_size = 64 * 1024  # 64KB — stream to cap memory per upload
    for f in files:
        try:
            if not f.filename:
                continue
            result = await service.save_temp_file_stream(
                f.filename,
                _iter_upload_chunks(f, max_size=max_size, chunk_size=chunk_size),
            )
            results.append(result)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        finally:
            await _close_upload_file(f)
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


# ── Inventory file upload endpoints ────────────────────────────────


@router.post("/inventory-files", response_model=list[UploadedFile])
@limiter.limit("10/minute")
async def upload_inventory_files(
    request: Request,
    files: list[UploadFile],
    service: Annotated[UploadService, Depends(_get_service)],
) -> list[UploadedFile]:
    """Upload inventory Excel files (receipts, adjustments, counts, batches).

    Reuses the same temp storage as sales uploads. File type is detected
    from headers during preview.
    """
    results = []
    max_size = 100 * 1024 * 1024
    chunk_size = 64 * 1024
    for f in files:
        try:
            if not f.filename:
                continue
            result = await service.save_temp_file_stream(
                f.filename,
                _iter_upload_chunks(f, max_size=max_size, chunk_size=chunk_size),
            )
            results.append(result)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        finally:
            await _close_upload_file(f)
    return results


@router.get("/inventory-preview/{file_id}", response_model=InventoryPreviewResult)
@limiter.limit("10/minute")
def preview_inventory_file(
    request: Request,
    file_id: str,
    service: Annotated[UploadService, Depends(_get_service)],
) -> InventoryPreviewResult:
    """Preview an uploaded inventory file with automatic type detection.

    Reads headers, matches against known inventory column maps, and returns
    the detected file type along with preview data.
    """
    try:
        return service.preview_inventory_file(file_id)
    except FileNotFoundError as e:
        raise HTTPException(404, "File not found") from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/inventory-confirm", response_model=ConfirmResponse)
@limiter.limit("5/minute")
def confirm_inventory_upload(
    request: Request,
    body: InventoryConfirmRequest,
    service: Annotated[UploadService, Depends(_get_service)],
) -> ConfirmResponse:
    """Move confirmed inventory files to the inventory raw data directory."""
    moved = service.confirm_inventory_upload(body.file_ids, body.target_dir)
    return ConfirmResponse(moved_files=moved)

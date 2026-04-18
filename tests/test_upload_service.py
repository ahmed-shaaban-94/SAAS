"""Tests for upload service — save_temp_file, preview_file, confirm_upload."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from datapulse.upload.service import UploadService

# Minimal valid XLSX magic bytes (PK\x03\x04)
_XLSX_MAGIC = b"PK\x03\x04" + b" " * 100
# Minimal valid XLS magic bytes (OLE2: D0 CF 11 E0)
_XLS_MAGIC = b"\xd0\xcf\x11\xe0" + b" " * 100
# Valid CSV content
_CSV_CONTENT = b"name,value\nfoo,1\nbar,2\n"


@pytest.fixture
def svc(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    return UploadService(raw_data_dir=str(raw_dir), tenant_id="test-tenant")


async def _yield_chunks(*chunks: bytes) -> AsyncIterator[bytes]:
    for chunk in chunks:
        yield chunk


# ------------------------------------------------------------------
# save_temp_file
# ------------------------------------------------------------------


@pytest.mark.unit
def test_save_valid_csv(svc):
    result = svc.save_temp_file("report.csv", _CSV_CONTENT)
    assert result.status == "uploaded"
    assert result.size_bytes == len(_CSV_CONTENT)
    assert uuid.UUID(result.file_id)  # valid UUID


@pytest.mark.unit
def test_save_valid_xlsx(svc):
    result = svc.save_temp_file("report.xlsx", _XLSX_MAGIC)
    assert result.status == "uploaded"
    assert uuid.UUID(result.file_id)


@pytest.mark.unit
def test_reject_unsupported_extension(svc):
    with pytest.raises(ValueError, match="Unsupported file type"):
        svc.save_temp_file("malware.exe", b"MZ" + b" " * 100)


@pytest.mark.unit
def test_reject_empty_content(svc):
    with pytest.raises(ValueError, match="empty"):
        svc.save_temp_file("empty.csv", b"")


@pytest.mark.unit
def test_reject_bad_magic_bytes_xlsx(svc):
    with pytest.raises(ValueError, match="magic bytes"):
        svc.save_temp_file("trick.xlsx", b"definitely not excel content here")


@pytest.mark.unit
def test_reject_csv_with_null_bytes(svc):
    with pytest.raises(ValueError, match="null bytes"):
        svc.save_temp_file("binary.csv", b"col1,col2\n\x00,value\n")


@pytest.mark.unit
def test_uuid_filename(svc):
    result = svc.save_temp_file("mydata.csv", _CSV_CONTENT)
    file_id = result.file_id
    stored = list(svc._tenant_dir.glob(f"{file_id}.*"))
    assert len(stored) == 1
    assert stored[0].name == f"{file_id}.csv"
    assert "mydata" not in stored[0].name


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_valid_csv_stream(svc):
    result = await svc.save_temp_file_stream("report.csv", _yield_chunks(b"name,", b"value\n"))
    assert result.status == "uploaded"
    assert result.size_bytes == len(b"name,value\n")
    stored = list(svc._tenant_dir.glob(f"{result.file_id}.*"))
    assert len(stored) == 1


# ------------------------------------------------------------------
# preview_file
# ------------------------------------------------------------------


@pytest.mark.unit
def test_preview_invalid_uuid_format(svc):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        svc.preview_file("not-a-uuid")
    assert exc_info.value.status_code == 400


@pytest.mark.unit
def test_preview_file_not_found(svc):
    with pytest.raises(FileNotFoundError):
        svc.preview_file(str(uuid.uuid4()))


@pytest.mark.unit
def test_preview_csv_columns(svc):
    csv_data = b"product,quantity,price\nAlpha,10,5.5\nBeta,20,3.0\n"
    result = svc.save_temp_file("data.csv", csv_data)
    preview = svc.preview_file(result.file_id)
    col_names = [c.name for c in preview.columns]
    assert "product" in col_names
    assert "quantity" in col_names
    assert "price" in col_names
    assert preview.row_count == 2


@pytest.mark.unit
def test_preview_high_null_warning(svc):
    csv_data = b"a,b\n1,\n2,\n3,\n4,hello\n"
    result = svc.save_temp_file("nulls.csv", csv_data)
    preview = svc.preview_file(result.file_id)
    assert any(">50% nulls" in w for w in preview.warnings)


# ------------------------------------------------------------------
# confirm_upload
# ------------------------------------------------------------------


@pytest.mark.unit
def test_confirm_moves_to_raw_dir(svc):
    result = svc.save_temp_file("confirm_me.csv", _CSV_CONTENT)
    moved = svc.confirm_upload([result.file_id])
    assert len(moved) == 1
    assert Path(moved[0]).exists()
    remaining = list(svc._tenant_dir.glob(f"{result.file_id}.*"))
    assert len(remaining) == 0


@pytest.mark.unit
def test_confirm_invalid_uuid(svc):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        svc.confirm_upload(["not-a-uuid"])
    assert exc_info.value.status_code == 400


@pytest.mark.unit
def test_confirm_missing_file_skipped(svc):
    moved = svc.confirm_upload([str(uuid.uuid4())])
    assert moved == []


# ------------------------------------------------------------------
# Tenant isolation
# ------------------------------------------------------------------


@pytest.mark.unit
def test_tenant_dir_isolation(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    svc_a = UploadService(raw_data_dir=str(raw), tenant_id="A")
    svc_b = UploadService(raw_data_dir=str(raw), tenant_id="B")
    assert svc_a._tenant_dir != svc_b._tenant_dir
    assert "A" in str(svc_a._tenant_dir)
    assert "B" in str(svc_b._tenant_dir)

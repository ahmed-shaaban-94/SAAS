"""Tests for upload service UUID validation (path traversal prevention)."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from datapulse.upload.service import UploadService


@pytest.fixture()
def service(tmp_path):
    """Return an UploadService with a temp raw data dir and mocked TEMP_DIR."""
    with patch("datapulse.upload.service.TEMP_DIR", tmp_path):
        yield UploadService(raw_data_dir=str(tmp_path / "raw"))


# ---------------------------------------------------------------------------
# preview_file — UUID validation
# ---------------------------------------------------------------------------


def test_preview_file_path_traversal_rejected(service):
    """Path traversal sequences in file_id must return HTTP 400."""
    with pytest.raises(HTTPException) as exc_info:
        service.preview_file("../../../etc/passwd")
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid file ID format"


def test_preview_file_glob_wildcard_rejected(service):
    """Glob wildcard characters in file_id must return HTTP 400."""
    with pytest.raises(HTTPException) as exc_info:
        service.preview_file("*")
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid file ID format"


def test_preview_file_valid_uuid_no_file_raises_not_found(service):
    """A valid UUID that has no corresponding file raises FileNotFoundError."""
    valid_id = str(uuid.uuid4())
    with pytest.raises(FileNotFoundError):
        service.preview_file(valid_id)


# ---------------------------------------------------------------------------
# confirm_upload — UUID validation
# ---------------------------------------------------------------------------


def test_confirm_upload_path_traversal_rejected(service):
    """Path traversal sequences in file_ids must return HTTP 400."""
    with pytest.raises(HTTPException) as exc_info:
        service.confirm_upload(["../../../etc/passwd"])
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid file ID format"


def test_confirm_upload_glob_wildcard_rejected(service):
    """Glob wildcard characters in file_ids must return HTTP 400."""
    with pytest.raises(HTTPException) as exc_info:
        service.confirm_upload(["*"])
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid file ID format"


def test_confirm_upload_valid_uuid_no_file_returns_empty(service):
    """A valid UUID with no matching temp file is silently skipped (returns empty list)."""
    valid_id = str(uuid.uuid4())
    result = service.confirm_upload([valid_id])
    assert result == []


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


def test_preview_file_empty_string_rejected(service):
    """Empty string for file_id must be rejected as invalid UUID."""
    with pytest.raises(HTTPException) as exc_info:
        service.preview_file("")
    assert exc_info.value.status_code == 400


def test_preview_file_arbitrary_string_rejected(service):
    """Arbitrary non-UUID string must be rejected."""
    with pytest.raises(HTTPException) as exc_info:
        service.preview_file("notauuid")
    assert exc_info.value.status_code == 400


def test_confirm_upload_mixed_ids_rejects_on_first_invalid(service):
    """If any file_id is invalid, HTTP 400 is raised immediately."""
    valid_id = str(uuid.uuid4())
    with pytest.raises(HTTPException) as exc_info:
        service.confirm_upload([valid_id, "../traversal"])
    assert exc_info.value.status_code == 400


def test_preview_file_brace_form_uuid_normalized_not_injected(service):
    """Brace-form UUID is normalized by uuid.UUID() — braces never reach the glob.

    Python's uuid.UUID() accepts ``{uuid}`` form and returns the canonical
    hyphenated string (no braces), so ``str(uuid.UUID(...))`` strips the
    braces before they can be used in a glob pattern.  The service must
    therefore NOT raise HTTPException(400) for this input; it should raise
    FileNotFoundError because no matching file exists, confirming that the
    normalized (safe) form was used in the glob call.
    """
    brace_form_id = "{12345678-1234-5678-1234-567812345678}"
    # Must NOT raise HTTPException — UUID is valid, just non-standard form
    with pytest.raises(FileNotFoundError):
        service.preview_file(brace_form_id)


# ---------------------------------------------------------------------------
# Extension spoofing — save_temp_file validation
# ---------------------------------------------------------------------------


def test_save_temp_file_disallowed_extension_rejected(service):
    """Files with a disallowed extension must raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported file type"):
        service.save_temp_file("malware.exe", b"MZ\x90\x00")


def test_save_temp_file_php_extension_rejected(service):
    """Double-extension where the outer extension is disallowed must be rejected.

    ``report.csv.php`` → suffix is ``.php`` → rejected.
    This prevents disguising executable scripts as data files.
    """
    with pytest.raises(ValueError, match="Unsupported file type"):
        service.save_temp_file("report.csv.php", b"<?php system($_GET['cmd']); ?>")


def test_save_temp_file_double_extension_csv_outer_accepted(service):
    """Double-extension where the outer extension IS allowed must be accepted.

    ``report.php.csv`` → suffix is ``.csv`` → accepted.
    The inner ``php`` component never reaches the filesystem as executable code;
    the file is stored under a fresh UUID name, making the original name irrelevant.
    """
    result = service.save_temp_file("report.php.csv", b"col1,col2\n1,2\n3,4")
    assert result.file_id  # a UUID was generated
    assert result.size_bytes == len(b"col1,col2\n1,2\n3,4")


def test_save_temp_file_allowed_extensions(service):
    """All three allowed extensions must succeed."""
    for ext, content in [
        ("data.xlsx", b"PK\x03\x04"),  # fake zip header (won't parse, but saves ok)
        ("data.xls", b"\xd0\xcf\x11\xe0"),  # OLE compound document magic bytes
        ("data.csv", b"a,b,c\n1,2,3\n"),
    ]:
        result = service.save_temp_file(ext, content)
        assert result.file_id, f"Expected file_id for {ext}"


# ---------------------------------------------------------------------------
# Concurrent confirm — two simultaneous calls must not cross-corrupt
# ---------------------------------------------------------------------------


def test_confirm_upload_concurrent_calls_independent(service, tmp_path):
    """Two concurrent confirm_upload calls for disjoint file sets produce independent results.

    Each call should move only its own files; neither call should interfere
    with the files belonging to the other call.
    """
    import concurrent.futures
    from unittest.mock import patch

    with patch("datapulse.upload.service.TEMP_DIR", tmp_path):
        # Create two distinct temp files (simulate prior save_temp_file calls)
        id_a = str(uuid.uuid4())
        id_b = str(uuid.uuid4())
        (tmp_path / f"{id_a}.csv").write_bytes(b"a,b\n1,2\n")
        (tmp_path / f"{id_b}.csv").write_bytes(b"x,y\n9,8\n")

        raw_dir_a = tmp_path / "raw_a"
        raw_dir_b = tmp_path / "raw_b"

        svc = UploadService(raw_data_dir=str(raw_dir_a))
        svc_b = UploadService(raw_data_dir=str(raw_dir_b))

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            fut_a = pool.submit(svc.confirm_upload, [id_a])
            fut_b = pool.submit(svc_b.confirm_upload, [id_b])
            result_a = fut_a.result()
            result_b = fut_b.result()

    assert len(result_a) == 1, "Service A must have moved exactly one file"
    assert len(result_b) == 1, "Service B must have moved exactly one file"
    # Files must have gone to their own raw directories
    assert "raw_a" in result_a[0]
    assert "raw_b" in result_b[0]

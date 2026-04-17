"""Tests for inventory file upload: type detection, preview, and confirm.

Tests the UploadService extension for inventory file type detection
from Excel/CSV headers, preview with detected type, and confirm flow.
"""

from __future__ import annotations

import uuid

import pytest

from datapulse.upload.service import (
    _MIN_MATCH_RATIO,
    INVENTORY_HEADER_SIGNATURES,
    UploadService,
)

# ── File type detection tests ──────────────────────────────────────


class TestDetectInventoryType:
    """Test file type detection from Excel headers."""

    def test_detect_stock_receipts(self):
        headers = [
            "Receipt Date",
            "Receipt Reference",
            "Drug Code",
            "Site Code",
            "Batch Number",
            "Expiry Date",
            "Quantity",
            "Unit Cost",
            "Supplier Code",
        ]
        result = UploadService.detect_inventory_type(headers)
        assert result == "stock_receipts"

    def test_detect_stock_adjustments(self):
        headers = [
            "Adjustment Date",
            "Adjustment Type",
            "Drug Code",
            "Site Code",
            "Quantity",
            "Reason",
            "Notes",
        ]
        result = UploadService.detect_inventory_type(headers)
        assert result == "stock_adjustments"

    def test_detect_inventory_counts(self):
        headers = [
            "Count Date",
            "Drug Code",
            "Site Code",
            "Batch Number",
            "Counted Quantity",
            "Counted By",
        ]
        result = UploadService.detect_inventory_type(headers)
        assert result == "inventory_counts"

    def test_detect_batches(self):
        headers = [
            "Drug Code",
            "Site Code",
            "Batch Number",
            "Expiry Date",
            "Initial Quantity",
            "Current Quantity",
            "Unit Cost",
            "Status",
        ]
        result = UploadService.detect_inventory_type(headers)
        assert result == "batches"

    def test_detect_suppliers(self):
        headers = [
            "Supplier Code",
            "Supplier Name",
            "Contact Name",
            "Contact Phone",
            "Payment Terms (Days)",
            "Lead Time (Days)",
        ]
        result = UploadService.detect_inventory_type(headers)
        assert result == "suppliers"

    def test_detect_purchase_orders(self):
        headers = [
            "PO Number",
            "PO Date",
            "Supplier Code",
            "Site Code",
            "Status",
            "Expected Date",
        ]
        result = UploadService.detect_inventory_type(headers)
        assert result == "purchase_orders"

    def test_unknown_headers_returns_none(self):
        headers = ["Column A", "Column B", "Column C"]
        result = UploadService.detect_inventory_type(headers)
        assert result is None

    def test_empty_headers_returns_none(self):
        result = UploadService.detect_inventory_type([])
        assert result is None

    def test_partial_match_above_threshold(self):
        """Headers with enough matches should still detect correctly."""
        # stock_receipts has 6 signature headers; 4 out of 6 = 67% > 60%
        headers = [
            "Receipt Date",
            "Drug Code",
            "Quantity",
            "Unit Cost",
            "Extra Column",
            "Another Column",
        ]
        result = UploadService.detect_inventory_type(headers)
        assert result == "stock_receipts"

    def test_partial_match_below_threshold(self):
        """Headers with too few matches should not detect."""
        # Only 1 out of 6 = 17% < 60%
        headers = ["Drug Code", "Random Column", "Other Column"]
        result = UploadService.detect_inventory_type(headers)
        # Could match batches (Drug Code alone) but ratio too low
        assert result is None

    def test_best_match_wins_on_ambiguity(self):
        """When headers overlap, the best scoring type wins."""
        # Both stock_receipts and batches have Drug Code + Batch Number
        # but receipts-specific headers tip the score
        headers = [
            "Receipt Date",
            "Receipt Reference",
            "Drug Code",
            "Batch Number",
            "Quantity",
            "Unit Cost",
        ]
        result = UploadService.detect_inventory_type(headers)
        assert result == "stock_receipts"


class TestAllSignaturesHaveEntries:
    """Verify the signature registry is well-formed."""

    def test_all_signatures_nonempty(self):
        for key, sig in INVENTORY_HEADER_SIGNATURES.items():
            assert len(sig) >= 3, f"{key} signature has too few headers"

    def test_min_match_ratio_is_sensible(self):
        assert 0.5 <= _MIN_MATCH_RATIO <= 0.8


# ── Preview tests ──────────────────────────────────────────────────


class TestInventoryPreview:
    """Test inventory file preview with type detection."""

    @pytest.fixture()
    def service(self, tmp_path):
        """UploadService with temp directory."""
        svc = UploadService(raw_data_dir=str(tmp_path / "raw"), tenant_id="test-tenant")
        svc._tenant_dir = tmp_path / "temp"
        svc._tenant_dir.mkdir(parents=True, exist_ok=True)
        return svc

    def test_preview_detects_receipts(self, service):
        """Preview a receipts CSV and detect type."""
        file_id = str(uuid.uuid4())
        csv_content = (
            "Receipt Date,Receipt Reference,Drug Code,Site Code,"
            "Batch Number,Quantity,Unit Cost\n"
            "2025-01-15,GRN-001,PARA500,SITE01,B2025-001,100,10.00\n"
        )
        csv_path = service._tenant_dir / f"{file_id}.csv"
        csv_path.write_text(csv_content)

        result = service.preview_inventory_file(file_id)
        assert result.detected_type == "stock_receipts"
        assert result.row_count == 1
        assert "Receipt Date" in result.matched_headers
        assert "Drug Code" in result.matched_headers

    def test_preview_detects_adjustments(self, service):
        """Preview an adjustments CSV and detect type."""
        file_id = str(uuid.uuid4())
        csv_content = (
            "Adjustment Date,Adjustment Type,Drug Code,Site Code,"
            "Quantity,Reason\n"
            "2025-01-20,damage,AMOX250,SITE01,-5,Broken packaging\n"
        )
        csv_path = service._tenant_dir / f"{file_id}.csv"
        csv_path.write_text(csv_content)

        result = service.preview_inventory_file(file_id)
        assert result.detected_type == "stock_adjustments"

    def test_preview_unknown_type_raises(self, service):
        """Unknown file type raises ValueError."""
        file_id = str(uuid.uuid4())
        csv_content = "Col A,Col B,Col C\n1,2,3\n"
        csv_path = service._tenant_dir / f"{file_id}.csv"
        csv_path.write_text(csv_content)

        with pytest.raises(ValueError, match="Cannot detect inventory file type"):
            service.preview_inventory_file(file_id)

    def test_preview_invalid_file_id(self, service):
        """Invalid UUID format raises HTTPException."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            service.preview_inventory_file("not-a-uuid")
        assert exc_info.value.status_code == 400

    def test_preview_missing_file_raises(self, service):
        """Missing file raises FileNotFoundError."""
        fake_id = str(uuid.uuid4())
        with pytest.raises(FileNotFoundError):
            service.preview_inventory_file(fake_id)

    def test_preview_returns_warnings_for_sparse_columns(self, service):
        """Columns with >50% nulls should generate warnings."""
        file_id = str(uuid.uuid4())
        csv_content = (
            "Receipt Date,Receipt Reference,Drug Code,Site Code,"
            "Batch Number,Quantity,Unit Cost\n"
            "2025-01-15,GRN-001,PARA500,SITE01,,100,\n"
            "2025-01-16,GRN-002,AMOX250,SITE01,,200,\n"
            "2025-01-17,GRN-003,IBU400,SITE01,,50,\n"
        )
        csv_path = service._tenant_dir / f"{file_id}.csv"
        csv_path.write_text(csv_content)

        result = service.preview_inventory_file(file_id)
        # Batch Number and Unit Cost are all empty -> >50% nulls
        warning_cols = [w for w in result.warnings if "Batch Number" in w or "Unit Cost" in w]
        assert len(warning_cols) >= 1


# ── Confirm tests ──────────────────────────────────────────────────


class TestInventoryConfirm:
    """Test inventory file confirmation."""

    @pytest.fixture()
    def service(self, tmp_path):
        svc = UploadService(raw_data_dir=str(tmp_path / "raw" / "sales"), tenant_id="test-tenant")
        svc._tenant_dir = tmp_path / "temp"
        svc._tenant_dir.mkdir(parents=True, exist_ok=True)
        svc._raw_dir = tmp_path / "raw" / "sales"
        return svc

    def test_confirm_moves_to_inventory_dir(self, service, tmp_path):
        """Confirmed files move to inventory raw data directory."""
        file_id = str(uuid.uuid4())
        src = service._tenant_dir / f"{file_id}.csv"
        src.write_text("test")

        target = tmp_path / "inventory"
        moved = service.confirm_inventory_upload([file_id], str(target))

        assert len(moved) == 1
        assert target.name in moved[0]
        assert not src.exists()  # original removed

    def test_confirm_default_dir(self, service, tmp_path):
        """Without target_dir, files go to sibling 'inventory' directory."""
        file_id = str(uuid.uuid4())
        src = service._tenant_dir / f"{file_id}.xlsx"
        src.write_bytes(b"dummy")

        moved = service.confirm_inventory_upload([file_id])
        assert len(moved) == 1

    def test_confirm_skips_missing_files(self, service):
        """Missing file IDs are silently skipped."""
        fake_id = str(uuid.uuid4())
        moved = service.confirm_inventory_upload([fake_id])
        assert moved == []

    def test_confirm_invalid_uuid_raises(self, service):
        """Invalid UUID raises HTTPException."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            service.confirm_inventory_upload(["not-a-uuid"])
        assert exc_info.value.status_code == 400


# ── Route integration tests ────────────────────────────────────────


class TestInventoryUploadEndpoints:
    """Test the inventory upload API endpoints."""

    @pytest.fixture()
    def client(self):
        """FastAPI TestClient with mocked upload service."""
        from fastapi.testclient import TestClient

        from datapulse.api.app import create_app
        from datapulse.api.auth import get_current_user

        _dev_user = {
            "sub": "test-user",
            "email": "test@datapulse.local",
            "preferred_username": "test",
            "tenant_id": "1",
            "roles": ["admin"],
            "raw_claims": {},
        }

        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: _dev_user

        client = TestClient(app, headers={"X-API-Key": "test-api-key"})
        yield client
        app.dependency_overrides.clear()

    def test_inventory_files_endpoint_exists(self, client):
        """POST /upload/inventory-files should exist (even if upload fails)."""
        resp = client.post("/api/v1/upload/inventory-files", files=[])
        # Empty file list returns empty array, not 404
        assert resp.status_code in (200, 422)

    def test_inventory_preview_not_found(self, client):
        """GET /upload/inventory-preview/bad-id returns 400."""
        resp = client.get("/api/v1/upload/inventory-preview/bad-id")
        assert resp.status_code == 400

    def test_inventory_confirm_endpoint_exists(self, client):
        """POST /upload/inventory-confirm should exist."""
        resp = client.post(
            "/api/v1/upload/inventory-confirm",
            json={"file_ids": [str(uuid.uuid4())]},
        )
        # Files don't exist but endpoint handles gracefully
        assert resp.status_code == 200

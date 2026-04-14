"""Unit tests for suppliers Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from datapulse.suppliers.models import (
    SupplierCreateRequest,
    SupplierInfo,
    SupplierUpdateRequest,
)


class TestSupplierCreateRequest:
    def test_valid(self):
        req = SupplierCreateRequest(
            supplier_code="SUP001",
            supplier_name="Test Supplier",
            payment_terms_days=30,
            lead_time_days=7,
        )
        assert req.supplier_code == "SUP001"
        assert req.is_active is True

    def test_empty_code_rejected(self):
        with pytest.raises(ValidationError):
            SupplierCreateRequest(supplier_code="  ", supplier_name="Test")

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            SupplierCreateRequest(supplier_code="SUP001", supplier_name="")

    def test_negative_payment_terms_rejected(self):
        with pytest.raises(ValidationError):
            SupplierCreateRequest(
                supplier_code="S1",
                supplier_name="Test",
                payment_terms_days=-1,
            )

    def test_optional_fields_default_none(self):
        req = SupplierCreateRequest(supplier_code="S1", supplier_name="Test")
        assert req.contact_name is None
        assert req.contact_email is None


class TestSupplierUpdateRequest:
    def test_all_fields_optional(self):
        req = SupplierUpdateRequest()
        assert req.supplier_name is None
        assert req.is_active is None

    def test_partial_update(self):
        req = SupplierUpdateRequest(is_active=False, lead_time_days=14)
        assert req.is_active is False
        assert req.lead_time_days == 14


class TestSupplierInfo:
    def test_immutable(self):
        from pydantic import ValidationError as PydanticValidationError

        info = SupplierInfo(supplier_code="S1", supplier_name="Test")
        with pytest.raises((PydanticValidationError, TypeError, AttributeError)):
            info.supplier_name = "Changed"  # type: ignore[misc]

    def test_defaults(self):
        info = SupplierInfo(supplier_code="S1", supplier_name="Test")
        assert info.payment_terms_days == 30
        assert info.lead_time_days == 7
        assert info.is_active is True

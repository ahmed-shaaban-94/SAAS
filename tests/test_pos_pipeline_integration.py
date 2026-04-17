"""Integration test: POS transaction -> bronze.pos_transactions -> stg_sales compatibility.

Verifies the end-to-end data flow from POS checkout through the bronze
write to ensure the columns match what stg_sales expects. This is the
critical pipeline integration that ensures POS transactions appear in
the existing analytics dashboards.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from datapulse.pos.constants import PaymentMethod
from datapulse.pos.inventory_contract import (
    MockInventoryService,
)
from datapulse.pos.models import CheckoutRequest
from datapulse.pos.repository import PosRepository
from datapulse.pos.service import PosService


@pytest.fixture()
def mock_repo():
    """Fully mocked PosRepository."""
    repo = create_autospec(PosRepository, instance=True)

    # Terminal lookup
    repo.get_terminal_session.return_value = {
        "id": 1,
        "tenant_id": 1,
        "site_code": "SITE01",
        "staff_id": "cashier-1",
        "terminal_name": "Terminal-1",
        "status": "active",
        "opened_at": datetime.now(tz=UTC),
        "closed_at": None,
        "opening_cash": Decimal("500"),
        "closing_cash": None,
    }

    # Transaction lookup
    repo.get_transaction.return_value = {
        "id": 101,
        "tenant_id": 1,
        "terminal_id": 1,
        "staff_id": "cashier-1",
        "pharmacist_id": None,
        "customer_id": None,
        "site_code": "SITE01",
        "subtotal": Decimal("0"),
        "discount_total": Decimal("0"),
        "tax_total": Decimal("0"),
        "grand_total": Decimal("0"),
        "payment_method": None,
        "status": "draft",
        "receipt_number": None,
        "created_at": datetime.now(tz=UTC),
    }

    # Transaction items
    repo.get_transaction_items.return_value = [
        {
            "id": 1,
            "drug_code": "PARA500",
            "drug_name": "Paracetamol 500mg",
            "batch_number": "BATCH-2026-001",
            "expiry_date": None,
            "quantity": Decimal("2"),
            "unit_price": Decimal("5.50"),
            "discount": Decimal("0"),
            "line_total": Decimal("11.00"),
            "is_controlled": False,
            "pharmacist_id": None,
        },
        {
            "id": 2,
            "drug_code": "IBUP400",
            "drug_name": "Ibuprofen 400mg",
            "batch_number": "BATCH-2026-002",
            "expiry_date": None,
            "quantity": Decimal("1"),
            "unit_price": Decimal("8.00"),
            "discount": Decimal("0"),
            "line_total": Decimal("8.00"),
            "is_controlled": False,
            "pharmacist_id": None,
        },
    ]

    # Update transaction status returns updated dict
    repo.update_transaction_status.return_value = {
        "id": 101,
        "status": "completed",
        "receipt_number": None,  # Will be set by service
    }

    # Product lookup
    repo.get_product_by_code.return_value = {
        "drug_code": "PARA500",
        "drug_name": "Paracetamol 500mg",
        "drug_category": "analgesic",
        "unit_price": Decimal("5.50"),
    }

    return repo


@pytest.fixture()
def mock_inventory():
    """In-memory mock inventory service."""
    return MockInventoryService()


@pytest.fixture()
def pos_service(mock_repo, mock_inventory):
    """POS service with mocked dependencies."""
    return PosService(repo=mock_repo, inventory=mock_inventory)


class TestBronzeWrite:
    """Verify insert_bronze_pos_transaction is called with correct columns."""

    @pytest.mark.asyncio()
    async def test_checkout_writes_bronze_rows_for_each_item(self, pos_service, mock_repo):
        """Each line item produces one bronze.pos_transactions row."""
        request = CheckoutRequest(
            payment_method=PaymentMethod.cash,
            cash_tendered=Decimal("20.00"),
        )

        await pos_service.checkout(
            transaction_id=101,
            tenant_id=1,
            request=request,
        )

        # Should write 2 bronze rows (one per item)
        assert mock_repo.insert_bronze_pos_transaction.call_count == 2

    @pytest.mark.asyncio()
    async def test_bronze_row_has_stg_sales_compatible_columns(self, pos_service, mock_repo):
        """Bronze row columns must map to stg_sales expectations."""
        request = CheckoutRequest(
            payment_method=PaymentMethod.cash,
            cash_tendered=Decimal("20.00"),
        )

        await pos_service.checkout(
            transaction_id=101,
            tenant_id=1,
            request=request,
        )

        # Inspect the first bronze write call
        first_call = mock_repo.insert_bronze_pos_transaction.call_args_list[0]
        kwargs = first_call.kwargs

        # Required columns for stg_sales compatibility
        assert "tenant_id" in kwargs
        assert "transaction_id" in kwargs
        assert "transaction_date" in kwargs
        assert "site_code" in kwargs
        assert "drug_code" in kwargs
        assert "quantity" in kwargs
        assert "unit_price" in kwargs
        assert "net_amount" in kwargs
        assert "payment_method" in kwargs
        assert "is_return" in kwargs

        # Verify data types and values
        assert kwargs["tenant_id"] == 1
        assert kwargs["drug_code"] == "PARA500"
        assert kwargs["quantity"] == Decimal("2")
        assert kwargs["unit_price"] == Decimal("5.50")
        assert kwargs["net_amount"] == Decimal("11.00")
        assert kwargs["payment_method"] == "cash"
        assert kwargs["is_return"] is False

    @pytest.mark.asyncio()
    async def test_bronze_transaction_id_has_pos_prefix(self, pos_service, mock_repo):
        """Transaction ID has 'POS-' prefix to prevent collision with ERP rows."""
        request = CheckoutRequest(
            payment_method=PaymentMethod.cash,
            cash_tendered=Decimal("20.00"),
        )

        await pos_service.checkout(
            transaction_id=101,
            tenant_id=1,
            request=request,
        )

        first_call = mock_repo.insert_bronze_pos_transaction.call_args_list[0]
        txn_id = first_call.kwargs["transaction_id"]

        assert txn_id.startswith("POS-")

    @pytest.mark.asyncio()
    async def test_checkout_records_inventory_movements(self, pos_service, mock_inventory):
        """Checkout records negative stock movements for each item."""
        request = CheckoutRequest(
            payment_method=PaymentMethod.cash,
            cash_tendered=Decimal("20.00"),
        )

        await pos_service.checkout(
            transaction_id=101,
            tenant_id=1,
            request=request,
        )

        movements = mock_inventory.get_recorded_movements()
        assert len(movements) == 2

        # First item: PARA500, qty -2
        assert movements[0].drug_code == "PARA500"
        assert movements[0].quantity_delta == Decimal("-2")
        assert movements[0].movement_type == "sale"

        # Second item: IBUP400, qty -1
        assert movements[1].drug_code == "IBUP400"
        assert movements[1].quantity_delta == Decimal("-1")
        assert movements[1].movement_type == "sale"


class TestPOSColumnMapping:
    """Verify that POS bronze columns map correctly to stg_sales expectations.

    This tests the column mapping documented in the blueprint:
    POS Field -> stg_sales Column
    """

    @pytest.mark.asyncio()
    async def test_payment_method_maps_to_billing_way(self, pos_service, mock_repo):
        """Payment method should be 'cash' (maps to billing_way='POS-CASH' in stg)."""
        request = CheckoutRequest(
            payment_method=PaymentMethod.cash,
            cash_tendered=Decimal("20.00"),
        )

        await pos_service.checkout(
            transaction_id=101,
            tenant_id=1,
            request=request,
        )

        first_call = mock_repo.insert_bronze_pos_transaction.call_args_list[0]
        assert first_call.kwargs["payment_method"] == "cash"

    @pytest.mark.asyncio()
    async def test_customer_id_maps_to_walk_in_when_null(self, pos_service, mock_repo):
        """Null customer_id -> walk-in transaction."""
        request = CheckoutRequest(
            payment_method=PaymentMethod.cash,
            cash_tendered=Decimal("20.00"),
        )

        await pos_service.checkout(
            transaction_id=101,
            tenant_id=1,
            request=request,
        )

        first_call = mock_repo.insert_bronze_pos_transaction.call_args_list[0]
        # customer_id is None for walk-in
        assert first_call.kwargs["customer_id"] is None

    @pytest.mark.asyncio()
    async def test_discount_field_present(self, pos_service, mock_repo):
        """Discount field must be present in bronze row."""
        request = CheckoutRequest(
            payment_method=PaymentMethod.cash,
            cash_tendered=Decimal("20.00"),
        )

        await pos_service.checkout(
            transaction_id=101,
            tenant_id=1,
            request=request,
        )

        first_call = mock_repo.insert_bronze_pos_transaction.call_args_list[0]
        assert "discount" in first_call.kwargs
        assert first_call.kwargs["discount"] == Decimal("0")


class TestReturnBronzeWrite:
    """Verify that returns write bronze rows with is_return=True."""

    @pytest.mark.asyncio()
    async def test_return_bronze_row_has_is_return_true(self, pos_service, mock_repo):
        """Return flow should write bronze rows with is_return=True."""
        from datapulse.pos.constants import ReturnReason
        from datapulse.pos.models import PosCartItem

        # Setup: original transaction is completed
        mock_repo.get_transaction.return_value = {
            "id": 101,
            "tenant_id": 1,
            "terminal_id": 1,
            "staff_id": "cashier-1",
            "pharmacist_id": None,
            "customer_id": None,
            "site_code": "SITE01",
            "subtotal": Decimal("11.00"),
            "discount_total": Decimal("0"),
            "tax_total": Decimal("0"),
            "grand_total": Decimal("11.00"),
            "payment_method": "cash",
            "status": "completed",
            "receipt_number": "R20260416-1-101",
            "created_at": datetime.now(tz=UTC),
        }

        # Return transaction creation
        mock_repo.create_transaction.return_value = {
            "id": 102,
            "tenant_id": 1,
            "terminal_id": 1,
            "staff_id": "cashier-1",
            "pharmacist_id": None,
            "customer_id": None,
            "site_code": "SITE01",
            "subtotal": Decimal("0"),
            "discount_total": Decimal("0"),
            "tax_total": Decimal("0"),
            "grand_total": Decimal("0"),
            "payment_method": None,
            "status": "draft",
            "receipt_number": None,
            "created_at": datetime.now(tz=UTC),
        }

        mock_repo.create_return.return_value = {
            "id": 1,
            "original_transaction_id": 101,
            "return_transaction_id": 102,
            "staff_id": "cashier-1",
            "reason": "customer_request",
            "refund_amount": Decimal("11.00"),
            "refund_method": "cash",
            "notes": None,
            "created_at": datetime.now(tz=UTC),
        }

        return_items = [
            PosCartItem(
                drug_code="PARA500",
                drug_name="Paracetamol 500mg",
                batch_number="BATCH-2026-001",
                quantity=Decimal("2"),
                unit_price=Decimal("5.50"),
                discount=Decimal("0"),
                line_total=Decimal("11.00"),
            )
        ]

        await pos_service.process_return(
            original_transaction_id=101,
            tenant_id=1,
            staff_id="cashier-1",
            items=return_items,
            reason=ReturnReason.customer_request,
            refund_method="cash",
        )

        # Should write bronze row with is_return=True
        assert mock_repo.insert_bronze_pos_transaction.call_count == 1
        bronze_call = mock_repo.insert_bronze_pos_transaction.call_args
        assert bronze_call.kwargs["is_return"] is True
        assert bronze_call.kwargs["transaction_id"].startswith("POS-RET-")

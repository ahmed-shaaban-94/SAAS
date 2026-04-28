"""Unit tests for PosService — checkout and voucher redemption."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from datapulse.pos.constants import PaymentMethod, TransactionStatus
from datapulse.pos.exceptions import PosError
from datapulse.pos.inventory_contract import (
    BatchInfo,
    InventoryServiceProtocol,
    StockLevel,
    StockMovement,
)
from datapulse.pos.models import CheckoutRequest
from datapulse.pos.service import PosService

pytestmark = pytest.mark.unit


@pytest.fixture()
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_inventory() -> AsyncMock:
    from datetime import date

    inv = AsyncMock(spec=InventoryServiceProtocol)
    inv.get_stock_level = AsyncMock(
        return_value=StockLevel(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_on_hand=Decimal("100"),
            quantity_reserved=Decimal("0"),
            quantity_available=Decimal("100"),
            reorder_point=Decimal("20"),
        )
    )
    inv.check_batch_expiry = AsyncMock(
        return_value=[
            BatchInfo(
                batch_number="BATCH-NEW",
                expiry_date=date(2027, 12, 31),
                quantity_available=Decimal("100"),
            )
        ]
    )
    inv.record_movement = AsyncMock(return_value=None)
    inv.get_reorder_alerts = AsyncMock(return_value=[])
    return inv


@pytest.fixture()
def service(mock_repo: MagicMock, mock_inventory: AsyncMock) -> PosService:
    return PosService(mock_repo, mock_inventory)


def _txn_row(status: str = "draft") -> dict:
    return {
        "id": 100,
        "tenant_id": 1,
        "terminal_id": 1,
        "staff_id": "staff-1",
        "pharmacist_id": None,
        "customer_id": None,
        "site_code": "SITE01",
        "subtotal": Decimal("0"),
        "discount_total": Decimal("0"),
        "tax_total": Decimal("0"),
        "grand_total": Decimal("0"),
        "payment_method": None,
        "status": status,
        "receipt_number": None,
        "created_at": datetime(2026, 4, 15, 10, 30, tzinfo=UTC),
    }


def _three_items() -> list[dict]:
    return [
        {
            "id": 1,
            "transaction_id": 100,
            "drug_code": "DRUG001",
            "drug_name": "A",
            "quantity": Decimal("2"),
            "unit_price": Decimal("10"),
            "line_total": Decimal("20"),
            "discount": Decimal("0"),
            "batch_number": "B1",
            "is_controlled": False,
            "pharmacist_id": None,
        },
        {
            "id": 2,
            "transaction_id": 100,
            "drug_code": "DRUG002",
            "drug_name": "B",
            "quantity": Decimal("3"),
            "unit_price": Decimal("5"),
            "line_total": Decimal("15"),
            "discount": Decimal("0"),
            "batch_number": "B2",
            "is_controlled": False,
            "pharmacist_id": None,
        },
        {
            "id": 3,
            "transaction_id": 100,
            "drug_code": "DRUG003",
            "drug_name": "C",
            "quantity": Decimal("4"),
            "unit_price": Decimal("10"),
            "line_total": Decimal("40"),
            "discount": Decimal("0"),
            "batch_number": "B3",
            "is_controlled": False,
            "pharmacist_id": None,
        },
    ]


@pytest.fixture()
def three_item_setup(mock_repo: MagicMock) -> dict:
    mock_repo.get_transaction.return_value = _txn_row("draft")
    items = _three_items()
    mock_repo.get_transaction_items.return_value = items
    mock_repo.update_transaction_status.return_value = {
        **_txn_row("completed"),
        "grand_total": Decimal("75.0000"),
        "subtotal": Decimal("75.0000"),
    }
    mock_repo.insert_bronze_pos_transaction.return_value = {
        "id": 1,
        "transaction_id": "POS-R1-1-100",
        "drug_code": "X",
        "net_amount": Decimal("0"),
        "loaded_at": datetime.now(tz=UTC),
    }
    return {"items": items}


class TestCheckout:
    @pytest.mark.asyncio
    async def test_full_checkout_cash(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
        three_item_setup: dict,
    ):
        result = await service.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
            ),
        )

        assert result.status == TransactionStatus.completed
        assert result.grand_total == Decimal("75.0000")
        assert result.change_due == Decimal("25.0000")
        assert result.payment_method == PaymentMethod.cash
        assert result.receipt_number.startswith("R")
        assert mock_inventory.record_movement.await_count == 3
        assert mock_repo.insert_bronze_pos_transaction.call_count == 3

    @pytest.mark.asyncio
    async def test_checkout_passes_decimal_not_float_to_receipt_generators(
        self,
        service: PosService,
        mock_repo: MagicMock,
        three_item_setup: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        captured: dict[str, dict] = {}

        def spy_thermal(txn, items, payment, **kwargs):
            captured["thermal"] = payment
            return b"stub-thermal"

        def spy_pdf(txn, items, payment, **kwargs):
            captured["pdf"] = payment
            return b"stub-pdf"

        monkeypatch.setattr("datapulse.pos._service_checkout.generate_thermal_receipt", spy_thermal)
        monkeypatch.setattr("datapulse.pos._service_checkout.generate_pdf_receipt", spy_pdf)

        await service.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
            ),
        )

        for label, payment in captured.items():
            assert isinstance(payment["amount_charged"], Decimal), (
                f"{label}.amount_charged is "
                f"{type(payment['amount_charged']).__name__}, expected Decimal"
            )
            assert isinstance(payment["change_due"], Decimal), (
                f"{label}.change_due is {type(payment['change_due']).__name__}, expected Decimal"
            )

    @pytest.mark.asyncio
    async def test_cash_underpayment_raises(
        self,
        service: PosService,
        mock_repo: MagicMock,
        three_item_setup: dict,
    ):
        with pytest.raises(PosError) as exc_info:
            await service.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("50"),
                ),
            )
        assert "insufficient" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_insurance_requires_insurance_no(
        self,
        service: PosService,
        mock_repo: MagicMock,
        three_item_setup: dict,
    ):
        with pytest.raises(PosError):
            await service.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.insurance,
                ),
            )

    @pytest.mark.asyncio
    async def test_checkout_rejects_already_completed(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction.return_value = _txn_row("completed")
        with pytest.raises(PosError):
            await service.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("100"),
                ),
            )

    @pytest.mark.asyncio
    async def test_checkout_rejects_empty_cart(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction.return_value = _txn_row("draft")
        mock_repo.get_transaction_items.return_value = []
        with pytest.raises(PosError):
            await service.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("100"),
                ),
            )

    @pytest.mark.asyncio
    async def test_checkout_cas_conflict_raises_and_skips_inventory(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
        three_item_setup: dict,
    ):
        mock_repo.update_transaction_status.return_value = None

        with pytest.raises(PosError, match="another request"):
            await service.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("100"),
                ),
            )

        mock_inventory.record_movement.assert_not_awaited()
        mock_repo.insert_bronze_pos_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_checkout_passes_expected_status_to_repository(
        self,
        service: PosService,
        mock_repo: MagicMock,
        three_item_setup: dict,
    ):
        await service.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
            ),
        )
        call_kwargs = mock_repo.update_transaction_status.call_args.kwargs
        assert call_kwargs["expected_status"] == TransactionStatus.draft.value

    @pytest.mark.asyncio
    async def test_checkout_unknown_transaction_raises(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction.return_value = None
        with pytest.raises(PosError):
            await service.checkout(
                transaction_id=999,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("1"),
                ),
            )

    @pytest.mark.asyncio
    async def test_bronze_id_uses_pos_prefix(
        self,
        service: PosService,
        mock_repo: MagicMock,
        three_item_setup: dict,
    ):
        await service.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
            ),
        )
        for call in mock_repo.insert_bronze_pos_transaction.call_args_list:
            assert call.kwargs["transaction_id"].startswith("POS-")

    @pytest.mark.asyncio
    async def test_movements_use_negative_quantity_delta(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
        three_item_setup: dict,
    ):
        await service.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
            ),
        )
        for call in mock_inventory.record_movement.await_args_list:
            mv: StockMovement = call.args[0]
            assert mv.quantity_delta < 0
            assert mv.movement_type == "sale"


class TestCheckoutWithVoucher:
    @pytest.fixture()
    def mock_voucher_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture()
    def service_with_voucher(
        self,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
        mock_voucher_repo: MagicMock,
    ) -> PosService:
        return PosService(
            mock_repo,
            mock_inventory,
            voucher_repo=mock_voucher_repo,
        )

    @pytest.fixture()
    def three_item_setup(self, mock_repo: MagicMock) -> dict:
        mock_repo.get_transaction.return_value = _txn_row("draft")
        items = _three_items()
        mock_repo.get_transaction_items.return_value = items
        mock_repo.update_transaction_status.return_value = {
            **_txn_row("completed"),
            "grand_total": Decimal("75.0000"),
            "subtotal": Decimal("75.0000"),
        }
        mock_repo.insert_bronze_pos_transaction.return_value = {
            "id": 1,
            "transaction_id": "POS-R1-1-100",
            "drug_code": "X",
            "net_amount": Decimal("0"),
            "loaded_at": datetime.now(tz=UTC),
        }
        return {"items": items}

    def _make_voucher(self, *, discount_type: str, value: Decimal):
        from datapulse.pos.models import VoucherResponse

        return VoucherResponse(
            id=1,
            tenant_id=1,
            code="SAVE10",
            discount_type=discount_type,
            value=value,
            max_uses=1,
            uses=0,
            status="active",
            starts_at=None,
            ends_at=None,
            min_purchase=None,
            redeemed_txn_id=None,
            created_at=datetime.now(tz=UTC),
        )

    @pytest.mark.asyncio
    async def test_amount_voucher_reduces_grand_total(
        self,
        service_with_voucher: PosService,
        mock_voucher_repo: MagicMock,
        three_item_setup: dict,
    ):
        mock_voucher_repo.get_by_code.return_value = self._make_voucher(
            discount_type="amount", value=Decimal("10")
        )
        mock_voucher_repo.lock_and_redeem.return_value = self._make_voucher(
            discount_type="amount", value=Decimal("10")
        )

        result = await service_with_voucher.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
                voucher_code="SAVE10",
            ),
        )

        assert result.grand_total == Decimal("65.0000")
        assert result.voucher_discount == Decimal("10")
        assert result.change_due == Decimal("35.0000")
        mock_voucher_repo.lock_and_redeem.assert_called_once()

    @pytest.mark.asyncio
    async def test_percent_voucher_reduces_grand_total(
        self,
        service_with_voucher: PosService,
        mock_voucher_repo: MagicMock,
        three_item_setup: dict,
    ):
        mock_voucher_repo.get_by_code.return_value = self._make_voucher(
            discount_type="percent", value=Decimal("20")
        )
        mock_voucher_repo.lock_and_redeem.return_value = self._make_voucher(
            discount_type="percent", value=Decimal("20")
        )

        result = await service_with_voucher.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
                voucher_code="PCT20",
            ),
        )

        assert result.grand_total == Decimal("60.0000")
        assert result.voucher_discount == Decimal("15.00")

    @pytest.mark.asyncio
    async def test_unknown_voucher_raises(
        self,
        service_with_voucher: PosService,
        mock_voucher_repo: MagicMock,
        three_item_setup: dict,
    ):
        mock_voucher_repo.get_by_code.return_value = None
        with pytest.raises(PosError, match=r"[Vv]oucher"):
            await service_with_voucher.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("100"),
                    voucher_code="NONEXISTENT",
                ),
            )
        mock_voucher_repo.lock_and_redeem.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_voucher_code_skips_voucher_repo(
        self,
        service_with_voucher: PosService,
        mock_voucher_repo: MagicMock,
        three_item_setup: dict,
    ):
        result = await service_with_voucher.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
            ),
        )

        assert result.grand_total == Decimal("75.0000")
        assert result.voucher_discount == Decimal("0")
        mock_voucher_repo.get_by_code.assert_not_called()
        mock_voucher_repo.lock_and_redeem.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_voucher_repo_bypasses_voucher_code(
        self,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
        three_item_setup: dict,
    ):
        service_no_voucher = PosService(mock_repo, mock_inventory)

        result = await service_no_voucher.checkout(
            transaction_id=100,
            tenant_id=1,
            request=CheckoutRequest(
                payment_method=PaymentMethod.cash,
                cash_tendered=Decimal("100"),
                voucher_code="SAVE10",
            ),
        )

        assert result.grand_total == Decimal("75.0000")
        assert result.voucher_discount == Decimal("0")

    @pytest.mark.asyncio
    async def test_voucher_cas_fails_redemption_not_called(
        self,
        service_with_voucher: PosService,
        mock_repo: MagicMock,
        mock_voucher_repo: MagicMock,
        three_item_setup: dict,
    ):
        mock_voucher_repo.get_by_code.return_value = self._make_voucher(
            discount_type="amount", value=Decimal("10")
        )
        mock_repo.update_transaction_status.return_value = None

        with pytest.raises(PosError, match="another request"):
            await service_with_voucher.checkout(
                transaction_id=100,
                tenant_id=1,
                request=CheckoutRequest(
                    payment_method=PaymentMethod.cash,
                    cash_tendered=Decimal("100"),
                    voucher_code="SAVE10",
                ),
            )
        mock_voucher_repo.lock_and_redeem.assert_not_called()

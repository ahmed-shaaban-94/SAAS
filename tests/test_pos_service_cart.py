"""Unit tests for PosService — add item, update item, remove item."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from datapulse.pos.constants import TransactionStatus
from datapulse.pos.exceptions import (
    InsufficientStockError,
    PharmacistVerificationRequiredError,
    PosError,
)
from datapulse.pos.inventory_contract import (
    BatchInfo,
    InventoryServiceProtocol,
    StockLevel,
)
from datapulse.pos.pharmacist_verifier import ALGO_SCRYPT, PharmacistVerifier, PinRecord, hash_pin
from datapulse.pos.service import PosService

pytestmark = pytest.mark.unit


@pytest.fixture()
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_inventory() -> AsyncMock:
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
    return inv


@pytest.fixture()
def service(mock_repo: MagicMock, mock_inventory: AsyncMock) -> PosService:
    return PosService(mock_repo, mock_inventory)


@pytest.fixture()
def verifier() -> PharmacistVerifier:
    _hash, _salt = hash_pin("1234")
    _stored = PinRecord(pin_hash=_hash, pin_salt=_salt, pin_hash_algo=ALGO_SCRYPT)
    return PharmacistVerifier(
        secret_key="test-secret",
        pin_lookup=lambda _uid: _stored,
    )


@pytest.fixture()
def service_with_verifier(
    mock_repo: MagicMock,
    mock_inventory: AsyncMock,
    verifier: PharmacistVerifier,
) -> PosService:
    return PosService(mock_repo, mock_inventory, verifier)


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


class TestAddItem:
    @pytest.mark.asyncio
    async def test_add_item_happy_path(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
    ):
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "DRUG001",
            "drug_name": "Paracetamol 500mg",
            "drug_brand": "Panadol",
            "drug_cluster": "Analgesic",
            "drug_category": "OTC",
            "unit_price": Decimal("12.5000"),
        }
        mock_repo.add_transaction_item.return_value = {
            "id": 1,
            "transaction_id": 100,
            "tenant_id": 1,
            "drug_code": "DRUG001",
            "drug_name": "Paracetamol 500mg",
            "batch_number": "BATCH-NEW",
            "expiry_date": date(2027, 12, 31),
            "quantity": Decimal("3"),
            "unit_price": Decimal("12.5000"),
            "discount": Decimal("0"),
            "line_total": Decimal("37.5000"),
            "is_controlled": False,
            "pharmacist_id": None,
        }

        item = await service.add_item(
            transaction_id=100,
            tenant_id=1,
            site_code="SITE01",
            drug_code="DRUG001",
            quantity=Decimal("3"),
        )

        assert item.line_total == Decimal("37.5000")
        assert item.batch_number == "BATCH-NEW"
        mock_inventory.get_stock_level.assert_awaited_once_with("DRUG001", "SITE01")
        mock_inventory.check_batch_expiry.assert_awaited_once_with("DRUG001", "SITE01")

    @pytest.mark.asyncio
    async def test_insufficient_stock_raises(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
    ):
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "DRUG001",
            "drug_name": "X",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "OTC",
            "unit_price": Decimal("10"),
        }
        mock_inventory.get_stock_level.return_value = StockLevel(
            drug_code="DRUG001",
            site_code="SITE01",
            quantity_on_hand=Decimal("3"),
            quantity_reserved=Decimal("0"),
            quantity_available=Decimal("3"),
            reorder_point=Decimal("0"),
        )

        with pytest.raises(InsufficientStockError) as exc_info:
            await service.add_item(
                transaction_id=100,
                tenant_id=1,
                site_code="SITE01",
                drug_code="DRUG001",
                quantity=Decimal("5"),
            )
        assert exc_info.value.requested == Decimal("5")
        assert exc_info.value.available == Decimal("3")

    @pytest.mark.asyncio
    async def test_controlled_substance_requires_pharmacist(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
    ):
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "MORPHINE",
            "drug_name": "Morphine",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "narcotic",
            "unit_price": Decimal("50"),
        }
        with pytest.raises(PharmacistVerificationRequiredError):
            await service.add_item(
                transaction_id=100,
                tenant_id=1,
                site_code="SITE01",
                drug_code="MORPHINE",
                quantity=Decimal("1"),
            )

    @pytest.mark.asyncio
    async def test_controlled_substance_with_valid_token_passes(
        self,
        service_with_verifier: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
        verifier: PharmacistVerifier,
    ):
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "MORPHINE",
            "drug_name": "Morphine",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "narcotic",
            "unit_price": Decimal("50"),
        }
        mock_repo.add_transaction_item.return_value = {
            "id": 2,
            "transaction_id": 100,
            "tenant_id": 1,
            "drug_code": "MORPHINE",
            "drug_name": "Morphine",
            "batch_number": "BATCH-NEW",
            "expiry_date": date(2027, 12, 31),
            "quantity": Decimal("1"),
            "unit_price": Decimal("50"),
            "discount": Decimal("0"),
            "line_total": Decimal("50"),
            "is_controlled": True,
            "pharmacist_id": "pharm-7",
        }
        token = verifier.verify_and_issue("pharm-7", "1234", "MORPHINE")

        item = await service_with_verifier.add_item(
            transaction_id=100,
            tenant_id=1,
            site_code="SITE01",
            drug_code="MORPHINE",
            quantity=Decimal("1"),
            pharmacist_id=token,
        )
        assert item.is_controlled is True
        assert item.pharmacist_id == "pharm-7"
        call_kwargs = mock_repo.add_transaction_item.call_args.kwargs
        assert call_kwargs["pharmacist_id"] == "pharm-7"

    @pytest.mark.asyncio
    async def test_controlled_substance_bare_string_is_rejected(
        self,
        service_with_verifier: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "MORPHINE",
            "drug_name": "Morphine",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "narcotic",
            "unit_price": Decimal("50"),
        }
        with pytest.raises(PharmacistVerificationRequiredError):
            await service_with_verifier.add_item(
                transaction_id=100,
                tenant_id=1,
                site_code="SITE01",
                drug_code="MORPHINE",
                quantity=Decimal("1"),
                pharmacist_id="pharm-7",
            )

    @pytest.mark.asyncio
    async def test_controlled_substance_without_verifier_configured(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "MORPHINE",
            "drug_name": "Morphine",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "narcotic",
            "unit_price": Decimal("50"),
        }
        with pytest.raises(PharmacistVerificationRequiredError):
            await service.add_item(
                transaction_id=100,
                tenant_id=1,
                site_code="SITE01",
                drug_code="MORPHINE",
                quantity=Decimal("1"),
                pharmacist_id="any-token-value",
            )

    @pytest.mark.asyncio
    async def test_controlled_substance_token_for_other_drug_rejected(
        self,
        service_with_verifier: PosService,
        mock_repo: MagicMock,
        verifier: PharmacistVerifier,
    ):
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "MORPHINE",
            "drug_name": "Morphine",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "narcotic",
            "unit_price": Decimal("50"),
        }
        wrong_token = verifier.verify_and_issue("pharm-7", "1234", "OXY-OTHER")
        with pytest.raises(PharmacistVerificationRequiredError):
            await service_with_verifier.add_item(
                transaction_id=100,
                tenant_id=1,
                site_code="SITE01",
                drug_code="MORPHINE",
                quantity=Decimal("1"),
                pharmacist_id=wrong_token,
            )

    @pytest.mark.asyncio
    async def test_unknown_drug_raises(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_product_by_code.return_value = None
        with pytest.raises(PosError):
            await service.add_item(
                transaction_id=100,
                tenant_id=1,
                site_code="SITE01",
                drug_code="UNKNOWN",
                quantity=Decimal("1"),
            )

    @pytest.mark.asyncio
    async def test_fefo_picks_earliest_expiry(
        self,
        service: PosService,
        mock_repo: MagicMock,
        mock_inventory: AsyncMock,
    ):
        mock_repo.get_product_by_code.return_value = {
            "drug_code": "DRUG001",
            "drug_name": "X",
            "drug_brand": None,
            "drug_cluster": None,
            "drug_category": "OTC",
            "unit_price": Decimal("10"),
        }
        mock_inventory.check_batch_expiry.return_value = [
            BatchInfo("LATE", date(2027, 12, 31), Decimal("100")),
            BatchInfo("EARLY", date(2026, 6, 1), Decimal("100")),
            BatchInfo("MID", date(2027, 1, 1), Decimal("100")),
        ]
        captured: dict = {}

        def _capture(**kwargs):
            captured.update(kwargs)
            return {
                "id": 1,
                "transaction_id": 100,
                "tenant_id": 1,
                "drug_code": "DRUG001",
                "drug_name": "X",
                "batch_number": kwargs["batch_number"],
                "expiry_date": kwargs["expiry_date"],
                "quantity": kwargs["quantity"],
                "unit_price": kwargs["unit_price"],
                "discount": Decimal("0"),
                "line_total": kwargs["line_total"],
                "is_controlled": False,
                "pharmacist_id": None,
            }

        mock_repo.add_transaction_item.side_effect = _capture
        await service.add_item(
            transaction_id=100,
            tenant_id=1,
            site_code="SITE01",
            drug_code="DRUG001",
            quantity=Decimal("5"),
        )
        assert captured["batch_number"] == "EARLY"


class TestUpdateRemoveItem:
    def _item_row(
        self,
        *,
        transaction_id: int = 100,
        unit_price: Decimal = Decimal("12.5"),
    ) -> dict:
        return {
            "id": 1,
            "transaction_id": transaction_id,
            "tenant_id": 1,
            "drug_code": "DRUG001",
            "drug_name": "X",
            "batch_number": None,
            "expiry_date": None,
            "quantity": Decimal("2"),
            "unit_price": unit_price,
            "discount": Decimal("0"),
            "line_total": Decimal("25.0000"),
            "is_controlled": False,
            "pharmacist_id": None,
        }

    def test_update_item_recalculates_line_total(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction_item.return_value = self._item_row()
        mock_repo.get_transaction.return_value = _txn_row("draft")
        mock_repo.update_item_quantity.return_value = {
            "id": 1,
            "transaction_id": 100,
            "tenant_id": 1,
            "drug_code": "DRUG001",
            "drug_name": "X",
            "batch_number": None,
            "expiry_date": None,
            "quantity": Decimal("4"),
            "unit_price": Decimal("12.5"),
            "discount": Decimal("0"),
            "line_total": Decimal("50.0000"),
            "is_controlled": False,
            "pharmacist_id": None,
        }
        item = service.update_item(
            1,
            tenant_id=1,
            quantity=Decimal("4"),
            unit_price=Decimal("12.5"),
        )
        assert item.quantity == Decimal("4")
        mock_repo.update_item_quantity.assert_called_once()
        kwargs = mock_repo.update_item_quantity.call_args.kwargs
        assert "line_total" not in kwargs
        assert kwargs["quantity"] == Decimal("4")
        assert kwargs["unit_price"] == Decimal("12.5")
        assert kwargs["expected_status"] == "draft"

    def test_update_item_preserves_existing_price_when_no_override(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction_item.return_value = self._item_row(unit_price=Decimal("12.5"))
        mock_repo.get_transaction.return_value = _txn_row("draft")
        mock_repo.update_item_quantity.return_value = {
            **self._item_row(unit_price=Decimal("12.5")),
            "quantity": Decimal("4"),
            "line_total": Decimal("50.0000"),
        }

        item = service.update_item(1, tenant_id=1, quantity=Decimal("4"))

        assert item.line_total == Decimal("50.0000")
        kwargs = mock_repo.update_item_quantity.call_args.kwargs
        assert kwargs["unit_price"] is None
        assert kwargs["expected_status"] == "draft"

    def test_update_item_rejects_completed_transaction(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction_item.return_value = self._item_row()
        mock_repo.get_transaction.return_value = _txn_row("completed")
        with pytest.raises(PosError, match="Only draft"):
            service.update_item(1, tenant_id=1, quantity=Decimal("4"))

    def test_update_unknown_item_raises(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction_item.return_value = None
        with pytest.raises(PosError):
            service.update_item(99, tenant_id=1, quantity=Decimal("1"))

    def test_remove_item_returns_repo_result(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction_item.return_value = self._item_row()
        mock_repo.get_transaction.return_value = _txn_row("draft")
        mock_repo.remove_item.return_value = True
        assert service.remove_item(1, tenant_id=1, transaction_id=100) is True
        mock_repo.remove_item.assert_called_once_with(
            1,
            tenant_id=1,
            transaction_id=100,
            expected_status=TransactionStatus.draft.value,
        )

    def test_remove_item_rejects_completed_transaction(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction_item.return_value = self._item_row()
        mock_repo.get_transaction.return_value = _txn_row("completed")
        with pytest.raises(PosError, match="Only draft"):
            service.remove_item(1, tenant_id=1, transaction_id=100)

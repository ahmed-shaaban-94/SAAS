"""Unit tests for PosService — product search and get/list query helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from datapulse.pos.inventory_contract import InventoryServiceProtocol
from datapulse.pos.service import PosService

pytestmark = pytest.mark.unit


@pytest.fixture()
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_inventory() -> AsyncMock:
    from datetime import date

    from datapulse.pos.inventory_contract import BatchInfo, StockLevel

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


class TestProductSearch:
    def test_search_returns_pos_results(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.search_dim_products.return_value = [
            {
                "drug_code": "DRUG001",
                "drug_name": "Paracetamol 500mg",
                "drug_brand": "Panadol",
                "drug_cluster": "Analgesic",
                "drug_category": "OTC",
                "unit_price": Decimal("12.5"),
            },
            {
                "drug_code": "DRUG002",
                "drug_name": "Morphine",
                "drug_brand": None,
                "drug_cluster": None,
                "drug_category": "narcotic",
                "unit_price": Decimal("50"),
            },
        ]
        results = service.search_products("para")
        assert len(results) == 2
        assert results[1].is_controlled is True

    @pytest.mark.asyncio
    async def test_get_stock_info_combines_inventory_calls(
        self,
        service: PosService,
        mock_inventory: AsyncMock,
    ):
        info = await service.get_stock_info("DRUG001", "SITE01")
        assert info.drug_code == "DRUG001"
        assert info.site_code == "SITE01"
        assert info.quantity_available == Decimal("100")
        assert len(info.batches) == 1
        assert info.batches[0].batch_number == "BATCH-NEW"


class TestQueries:
    def test_get_transaction_detail_returns_none_when_missing(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction.return_value = None
        assert service.get_transaction_detail(1, tenant_id=1) is None

    def test_get_transaction_detail_includes_items(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_transaction.return_value = _txn_row("completed")
        mock_repo.get_transaction_items.return_value = [
            {
                "id": 1,
                "transaction_id": 100,
                "drug_code": "X",
                "drug_name": "X",
                "quantity": Decimal("1"),
                "unit_price": Decimal("10"),
                "line_total": Decimal("10"),
                "discount": Decimal("0"),
                "batch_number": None,
                "is_controlled": False,
                "pharmacist_id": None,
            }
        ]
        detail = service.get_transaction_detail(100, tenant_id=1)
        assert detail is not None
        assert len(detail.items) == 1

    def test_list_transactions_passes_filters(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.list_transactions.return_value = [_txn_row("completed")]
        service.list_transactions(
            tenant_id=1,
            terminal_id=2,
            status="completed",
            limit=10,
            offset=0,
        )
        mock_repo.list_transactions.assert_called_once_with(
            1,
            terminal_id=2,
            status="completed",
            limit=10,
            offset=0,
        )

    def test_get_terminal_returns_none_when_missing(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ):
        mock_repo.get_terminal_session.return_value = None
        assert service.get_terminal(99, tenant_id=1) is None

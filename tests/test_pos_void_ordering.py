"""H5 — void_transaction must check existing returns BEFORE the CAS write.

Regression guard: if a transaction already has returns, the status must never
be flipped to 'voided'.  The CAS call (update_transaction_status) must not
fire when the returns-check would block the void.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from datapulse.pos.constants import TransactionStatus
from datapulse.pos.exceptions import PosError
from datapulse.pos.inventory_contract import InventoryServiceProtocol
from datapulse.pos.service import PosService

pytestmark = pytest.mark.unit


@pytest.fixture()
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def mock_inventory() -> AsyncMock:
    return AsyncMock(spec=InventoryServiceProtocol)


@pytest.fixture()
def service(mock_repo: MagicMock, mock_inventory: AsyncMock) -> PosService:
    return PosService(mock_repo, mock_inventory)


def _completed_txn_row() -> dict:
    return {
        "id": 42,
        "tenant_id": 1,
        "terminal_id": 5,
        "site_code": "SITE01",
        "status": TransactionStatus.completed.value,
        "grand_total": Decimal("100.00"),
    }


class TestVoidOrdering:
    """H5: returns-check must precede the CAS status update."""

    @pytest.mark.asyncio
    async def test_void_raises_when_transaction_has_returns(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ) -> None:
        """void_transaction raises PosError when existing returns are present."""
        mock_repo.get_transaction.return_value = _completed_txn_row()
        mock_repo.get_returned_quantities_for_transaction.return_value = [
            {"drug_code": "DRUG001", "batch_number": None, "returned_qty": Decimal("2")}
        ]

        with pytest.raises(PosError, match="existing returns"):
            await service.void_transaction(
                transaction_id=42,
                tenant_id=1,
                reason="test",
                voided_by="staff-1",
            )

    @pytest.mark.asyncio
    async def test_cas_write_not_called_when_returns_exist(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ) -> None:
        """update_transaction_status must NOT be called if existing returns block void."""
        mock_repo.get_transaction.return_value = _completed_txn_row()
        mock_repo.get_returned_quantities_for_transaction.return_value = [
            {"drug_code": "DRUG001", "batch_number": None, "returned_qty": Decimal("1")}
        ]

        with pytest.raises(PosError):
            await service.void_transaction(
                transaction_id=42,
                tenant_id=1,
                reason="test",
                voided_by="staff-1",
            )

        mock_repo.update_transaction_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_void_succeeds_when_no_returns_exist(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ) -> None:
        """void_transaction completes normally when no prior returns exist."""
        from datetime import UTC, datetime

        from datapulse.pos.models import VoidResponse

        mock_repo.get_transaction.return_value = _completed_txn_row()
        mock_repo.get_returned_quantities_for_transaction.return_value = []
        mock_repo.update_transaction_status.return_value = {
            "id": 42,
            "tenant_id": 1,
            "status": TransactionStatus.voided.value,
        }
        mock_repo.get_transaction_items.return_value = []
        mock_repo.create_void_log.return_value = {
            "id": 1,
            "transaction_id": 42,
            "tenant_id": 1,
            "voided_by": "staff-1",
            "reason": "test",
            "voided_at": datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
        }

        result = await service.void_transaction(
            transaction_id=42,
            tenant_id=1,
            reason="test",
            voided_by="staff-1",
        )

        assert isinstance(result, VoidResponse)
        mock_repo.update_transaction_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_check_called_before_cas(
        self,
        service: PosService,
        mock_repo: MagicMock,
    ) -> None:
        """Call order: get_returned_quantities_for_transaction before update_transaction_status."""
        call_log: list[str] = []

        def _track_returns(*a, **kw):
            call_log.append("check_returns")
            return []

        def _track_cas(*a, **kw):
            call_log.append("cas_update")
            return {"id": 42, "tenant_id": 1, "status": TransactionStatus.voided.value}

        from datetime import UTC, datetime

        mock_repo.get_transaction.return_value = _completed_txn_row()
        mock_repo.get_returned_quantities_for_transaction.side_effect = _track_returns
        mock_repo.update_transaction_status.side_effect = _track_cas
        mock_repo.get_transaction_items.return_value = []
        mock_repo.create_void_log.return_value = {
            "id": 1,
            "transaction_id": 42,
            "tenant_id": 1,
            "voided_by": "staff-1",
            "reason": "test",
            "voided_at": datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
        }

        await service.void_transaction(
            transaction_id=42,
            tenant_id=1,
            reason="test",
            voided_by="staff-1",
        )

        assert call_log.index("check_returns") < call_log.index("cas_update"), (
            "returns check must happen before CAS write"
        )

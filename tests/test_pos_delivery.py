"""POS delivery dispatch + rider routing unit tests (issue #628).

Covers: no-riders-available, assign-specific-rider, fee-persisted,
RiderNotFoundError, RiderUnavailableError, and service builder helpers.
All tests use a mocked PosRepository — no database required.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.pos._service_delivery import (
    _DEFAULT_ETA_MINUTES,
    DeliveryMixin,
    _build_delivery,
    _build_rider,
)
from datapulse.pos.exceptions import RiderNotFoundError, RiderUnavailableError
from datapulse.pos.models.delivery import (
    AvailableRidersResponse,
    CreateDeliveryRequest,
    DeliveryChannel,
    DeliveryResponse,
    RiderStatus,
)

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 4, 22, 10, 0, 0, tzinfo=UTC)


def _rider_row(
    *,
    id: int = 1,
    tenant_id: int = 99,
    name: str = "Ali Hassan",
    phone: str = "01012345678",
    status: str = "available",
    current_terminal_id: int | None = None,
) -> dict:
    return {
        "id": id,
        "tenant_id": tenant_id,
        "name": name,
        "phone": phone,
        "status": status,
        "current_terminal_id": current_terminal_id,
        "created_at": _NOW,
        "updated_at": _NOW,
    }


def _delivery_row(
    *,
    id: int = 10,
    tenant_id: int = 99,
    transaction_id: int = 5,
    address: str = "123 Nile St",
    landmark: str | None = "near pharmacy",
    channel: str = "phone",
    assigned_rider_id: int | None = 1,
    delivery_fee: Decimal = Decimal("15.00"),
    eta_minutes: int = 20,
    status: str = "pending",
    notes: str | None = None,
    rider_name: str | None = "Ali Hassan",
    rider_phone: str | None = "01012345678",
    rider_status: str | None = "busy",
    rider_terminal_id: int | None = None,
    rider_created_at: datetime | None = None,
    rider_updated_at: datetime | None = None,
) -> dict:
    return {
        "id": id,
        "tenant_id": tenant_id,
        "transaction_id": transaction_id,
        "address": address,
        "landmark": landmark,
        "channel": channel,
        "assigned_rider_id": assigned_rider_id,
        "delivery_fee": delivery_fee,
        "eta_minutes": eta_minutes,
        "status": status,
        "notes": notes,
        "created_at": _NOW,
        "updated_at": _NOW,
        "rider_name": rider_name,
        "rider_phone": rider_phone,
        "rider_status": rider_status,
        "rider_terminal_id": rider_terminal_id,
        "rider_created_at": rider_created_at or _NOW,
        "rider_updated_at": rider_updated_at or _NOW,
    }


class _ServiceUnderTest(DeliveryMixin):
    """Minimal concrete class that satisfies the mixin's type requirements."""

    def __init__(self, repo: MagicMock) -> None:
        self._repo = repo


# ─── _build_rider ─────────────────────────────────────────────────────────────


def test_build_rider_sets_all_fields():
    row = _rider_row()
    result = _build_rider(row)
    assert result.id == 1
    assert result.name == "Ali Hassan"
    assert result.phone == "01012345678"
    assert result.status == RiderStatus.available
    assert result.current_terminal_id is None


# ─── _build_delivery ──────────────────────────────────────────────────────────


def test_build_delivery_embeds_rider_when_present():
    row = _delivery_row()
    result = _build_delivery(row)
    assert result.id == 10
    assert result.rider is not None
    assert result.rider.name == "Ali Hassan"
    assert result.delivery_fee == Decimal("15.00")


def test_build_delivery_no_rider_when_none():
    row = _delivery_row(
        assigned_rider_id=None, rider_name=None, rider_phone=None, rider_status=None
    )
    result = _build_delivery(row)
    assert result.rider is None
    assert result.assigned_rider_id is None


# ─── list_available_riders ────────────────────────────────────────────────────


def test_list_available_riders_returns_empty_when_none():
    repo = MagicMock()
    repo.list_available_riders.return_value = []
    svc = _ServiceUnderTest(repo)

    result = svc.list_available_riders(tenant_id=99)

    assert isinstance(result, AvailableRidersResponse)
    assert result.total == 0
    assert result.riders == []
    repo.list_available_riders.assert_called_once_with(tenant_id=99)


def test_list_available_riders_returns_available():
    repo = MagicMock()
    repo.list_available_riders.return_value = [_rider_row(), _rider_row(id=2, name="Mona")]
    svc = _ServiceUnderTest(repo)

    result = svc.list_available_riders(tenant_id=99)

    assert result.total == 2
    assert result.riders[1].name == "Mona"


# ─── create_delivery ──────────────────────────────────────────────────────────


def _make_request(**overrides) -> CreateDeliveryRequest:
    defaults = {
        "transaction_id": 5,
        "address": "123 Nile St",
        "landmark": "near pharmacy",
        "channel": DeliveryChannel.phone,
        "assigned_rider_id": None,
        "delivery_fee": Decimal("15.00"),
        "eta_minutes": None,
        "notes": None,
    }
    defaults.update(overrides)
    return CreateDeliveryRequest(**defaults)


def test_create_delivery_no_rider_succeeds():
    repo = MagicMock()
    repo.create_delivery.return_value = {}
    repo.get_delivery_by_transaction.return_value = _delivery_row(
        assigned_rider_id=None, rider_name=None, rider_phone=None, rider_status=None
    )
    svc = _ServiceUnderTest(repo)

    result = svc.create_delivery(tenant_id=99, body=_make_request())

    assert isinstance(result, DeliveryResponse)
    assert result.rider is None
    repo.get_rider.assert_not_called()


def test_create_delivery_applies_default_eta_when_not_supplied():
    repo = MagicMock()
    repo.get_rider.return_value = _rider_row()
    repo.create_delivery.return_value = {}
    repo.get_delivery_by_transaction.return_value = _delivery_row()
    svc = _ServiceUnderTest(repo)

    svc.create_delivery(tenant_id=99, body=_make_request(assigned_rider_id=1, eta_minutes=None))

    _, kwargs = repo.create_delivery.call_args
    assert kwargs["eta_minutes"] == _DEFAULT_ETA_MINUTES


def test_create_delivery_uses_supplied_eta():
    repo = MagicMock()
    repo.get_rider.return_value = _rider_row()
    repo.create_delivery.return_value = {}
    repo.get_delivery_by_transaction.return_value = _delivery_row(eta_minutes=45)
    svc = _ServiceUnderTest(repo)

    svc.create_delivery(tenant_id=99, body=_make_request(assigned_rider_id=1, eta_minutes=45))

    _, kwargs = repo.create_delivery.call_args
    assert kwargs["eta_minutes"] == 45


def test_create_delivery_fee_persisted_to_transaction():
    repo = MagicMock()
    repo.get_rider.return_value = _rider_row()
    repo.create_delivery.return_value = {}
    repo.get_delivery_by_transaction.return_value = _delivery_row(delivery_fee=Decimal("25.00"))
    svc = _ServiceUnderTest(repo)

    svc.create_delivery(
        tenant_id=99,
        body=_make_request(assigned_rider_id=1, delivery_fee=Decimal("25.00")),
    )

    _, kwargs = repo.create_delivery.call_args
    assert kwargs["delivery_fee"] == Decimal("25.00")


def test_create_delivery_assigns_specific_rider_and_marks_busy():
    repo = MagicMock()
    repo.get_rider.return_value = _rider_row(status="available")
    repo.create_delivery.return_value = {}
    repo.get_delivery_by_transaction.return_value = _delivery_row()
    svc = _ServiceUnderTest(repo)

    result = svc.create_delivery(tenant_id=99, body=_make_request(assigned_rider_id=1))

    repo.get_rider.assert_called_once_with(rider_id=1, tenant_id=99)
    assert result.assigned_rider_id == 1


# ─── Error paths ──────────────────────────────────────────────────────────────


def test_rider_not_found_raises():
    repo = MagicMock()
    repo.get_rider.return_value = None
    svc = _ServiceUnderTest(repo)

    with pytest.raises(RiderNotFoundError) as exc_info:
        svc.create_delivery(tenant_id=99, body=_make_request(assigned_rider_id=42))

    assert exc_info.value.rider_id == 42


def test_rider_unavailable_raises():
    repo = MagicMock()
    repo.get_rider.return_value = _rider_row(status="busy")
    svc = _ServiceUnderTest(repo)

    with pytest.raises(RiderUnavailableError) as exc_info:
        svc.create_delivery(tenant_id=99, body=_make_request(assigned_rider_id=1))

    assert exc_info.value.current_status == "busy"


def test_rider_offline_also_raises_unavailable():
    repo = MagicMock()
    repo.get_rider.return_value = _rider_row(status="offline")
    svc = _ServiceUnderTest(repo)

    with pytest.raises(RiderUnavailableError):
        svc.create_delivery(tenant_id=99, body=_make_request(assigned_rider_id=1))

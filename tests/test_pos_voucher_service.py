"""VoucherService unit tests — mocked repository only.

Covers compute_discount arithmetic and the read-only validate() gate for
each of the expected failure modes (unknown / inactive / expired / not yet
active / max uses / min purchase).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from datapulse.pos.models import (
    VoucherResponse,
    VoucherStatus,
    VoucherType,
    VoucherValidateRequest,
)
from datapulse.pos.voucher_service import VoucherService

pytestmark = pytest.mark.unit


def _voucher(
    *,
    discount_type: VoucherType = VoucherType.amount,
    value: Decimal = Decimal("10"),
    status: VoucherStatus = VoucherStatus.active,
    max_uses: int = 1,
    uses: int = 0,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    min_purchase: Decimal | None = None,
) -> VoucherResponse:
    return VoucherResponse(
        id=1,
        tenant_id=1,
        code="SAVE10",
        discount_type=discount_type,
        value=value,
        max_uses=max_uses,
        uses=uses,
        status=status,
        starts_at=starts_at,
        ends_at=ends_at,
        min_purchase=min_purchase,
        redeemed_txn_id=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _service(voucher: VoucherResponse | None) -> VoucherService:
    repo = MagicMock()
    repo.get_by_code.return_value = voucher
    return VoucherService(repo)


# ---------------------------------------------------------------------------
# compute_discount
# ---------------------------------------------------------------------------


def test_compute_discount_amount_caps_at_subtotal() -> None:
    disc = VoucherService.compute_discount(VoucherType.amount, Decimal("50"), Decimal("20"))
    assert disc == Decimal("20.0000")


def test_compute_discount_amount_within_subtotal() -> None:
    disc = VoucherService.compute_discount(VoucherType.amount, Decimal("15"), Decimal("100"))
    assert disc == Decimal("15.0000")


def test_compute_discount_percent() -> None:
    # 10% of 200 = 20
    disc = VoucherService.compute_discount(VoucherType.percent, Decimal("10"), Decimal("200"))
    assert disc == Decimal("20.0000")


def test_compute_discount_percent_rounds_half_up() -> None:
    # 33.33% of 100 = 33.33 exactly (4dp)
    disc = VoucherService.compute_discount(VoucherType.percent, Decimal("33.33"), Decimal("100"))
    assert disc == Decimal("33.3300")


def test_compute_discount_zero_subtotal_returns_zero() -> None:
    assert VoucherService.compute_discount(
        VoucherType.amount, Decimal("10"), Decimal("0")
    ) == Decimal("0")


# ---------------------------------------------------------------------------
# validate — happy path + all failure modes
# ---------------------------------------------------------------------------


def test_validate_active_voucher_returns_details() -> None:
    service = _service(_voucher(max_uses=5, uses=2, value=Decimal("15")))
    resp = service.validate(1, VoucherValidateRequest(code="SAVE10"))
    assert resp.code == "SAVE10"
    assert resp.remaining_uses == 3
    assert resp.value == Decimal("15")
    assert resp.discount_type == VoucherType.amount


def test_validate_nonexistent_voucher_raises_404() -> None:
    service = _service(None)
    with pytest.raises(HTTPException) as exc:
        service.validate(1, VoucherValidateRequest(code="NOPE"))
    assert exc.value.status_code == 404
    assert exc.value.detail == "voucher_not_found"


@pytest.mark.parametrize(
    "status",
    [VoucherStatus.void, VoucherStatus.expired, VoucherStatus.redeemed],
)
def test_validate_inactive_voucher_raises_400(status: VoucherStatus) -> None:
    service = _service(_voucher(status=status))
    with pytest.raises(HTTPException) as exc:
        service.validate(1, VoucherValidateRequest(code="SAVE10"))
    assert exc.value.status_code == 400
    assert exc.value.detail == "voucher_inactive"


def test_validate_expired_voucher_raises_400() -> None:
    past = datetime.now(UTC) - timedelta(days=1)
    service = _service(_voucher(ends_at=past))
    with pytest.raises(HTTPException) as exc:
        service.validate(1, VoucherValidateRequest(code="SAVE10"))
    assert exc.value.status_code == 400
    assert exc.value.detail == "voucher_expired"


def test_validate_not_yet_active_voucher_raises_400() -> None:
    future = datetime.now(UTC) + timedelta(days=7)
    service = _service(_voucher(starts_at=future))
    with pytest.raises(HTTPException) as exc:
        service.validate(1, VoucherValidateRequest(code="SAVE10"))
    assert exc.value.status_code == 400
    assert exc.value.detail == "voucher_not_yet_active"


def test_validate_max_uses_reached_raises_400() -> None:
    service = _service(_voucher(max_uses=3, uses=3))
    with pytest.raises(HTTPException) as exc:
        service.validate(1, VoucherValidateRequest(code="SAVE10"))
    assert exc.value.status_code == 400
    assert exc.value.detail == "voucher_max_uses_reached"


def test_validate_min_purchase_unmet_when_cart_subtotal_provided() -> None:
    service = _service(_voucher(min_purchase=Decimal("100")))
    with pytest.raises(HTTPException) as exc:
        service.validate(
            1,
            VoucherValidateRequest(code="SAVE10", cart_subtotal=Decimal("50")),
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == "voucher_min_purchase_unmet"


def test_validate_min_purchase_met_when_cart_subtotal_sufficient() -> None:
    service = _service(_voucher(min_purchase=Decimal("50")))
    resp = service.validate(
        1,
        VoucherValidateRequest(code="SAVE10", cart_subtotal=Decimal("100")),
    )
    assert resp.min_purchase == Decimal("50")


def test_validate_no_cart_subtotal_skips_min_purchase_check() -> None:
    """min_purchase is only enforced when the client supplies cart_subtotal."""
    service = _service(_voucher(min_purchase=Decimal("500")))
    resp = service.validate(1, VoucherValidateRequest(code="SAVE10"))
    assert resp.min_purchase == Decimal("500")


# ---------------------------------------------------------------------------
# list / create — thin pass-throughs
# ---------------------------------------------------------------------------


def test_list_passes_filter_to_repository() -> None:
    repo = MagicMock()
    repo.list_for_tenant.return_value = []
    service = VoucherService(repo)
    service.list(1, status=VoucherStatus.active)
    repo.list_for_tenant.assert_called_once_with(1, status=VoucherStatus.active)

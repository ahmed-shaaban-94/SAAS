"""POS business logic — facade that composes domain mixins.

The service is the single entry-point used by API routes. It composes the
:class:`PosRepository` (raw SQL) and the
:class:`InventoryServiceProtocol` (async stock + batch + movement), and
delegates method groups to small domain mixins:

* :class:`TerminalOpsMixin`    — terminal session lifecycle
* :class:`CartOpsMixin`        — draft transaction + cart items
* :class:`CheckoutMixin`       — checkout orchestration (totals/payment/bronze)
* :class:`VoidReturnMixin`     — void + refund/return flows
* :class:`CatalogMixin`        — product search, catalog sync, stock lookup, receipts
* :class:`ShiftCashMixin`      — shifts, cash drawer events, pharmacist PIN

Design notes
------------
* All money arithmetic uses :class:`decimal.Decimal` — JSON serialisation is
  handled by the :data:`JsonDecimal` annotated type used in Pydantic models.
* Methods that touch the inventory service are ``async`` because the protocol
  is async; methods that only touch the repository remain synchronous.
* The bronze write uses a ``'POS-'`` prefixed transaction_id (C3 fix from the
  adversarial review) to prevent collision with ERP rows in ``fct_sales``.
* Receipt numbers follow ``R{YYYYMMDD}-{tenant}-{txn_id}`` — deterministic,
  human-readable, and unique per tenant per transaction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Re-exported helpers — tests import these underscore-prefixed names directly.
# New code should import from ``datapulse.pos._service_helpers`` instead.
from datapulse.pos._service_cart import CartOpsMixin
from datapulse.pos._service_catalog import CatalogMixin
from datapulse.pos._service_checkout import CheckoutMixin
from datapulse.pos._service_delivery import DeliveryMixin
from datapulse.pos._service_helpers import (
    build_receipt_number as _build_receipt_number,
)
from datapulse.pos._service_helpers import (
    is_controlled as _is_controlled,
)
from datapulse.pos._service_helpers import (
    select_fefo_batch as _select_fefo_batch,
)
from datapulse.pos._service_helpers import (
    to_decimal as _to_decimal,
)
from datapulse.pos._service_shift import ShiftCashMixin
from datapulse.pos._service_terminal import TerminalOpsMixin
from datapulse.pos._service_voidreturn import VoidReturnMixin

if TYPE_CHECKING:
    from datapulse.pos.inventory_contract import InventoryServiceProtocol
    from datapulse.pos.pharmacist_verifier import PharmacistVerifier
    from datapulse.pos.promotion_repository import PromotionRepository
    from datapulse.pos.repository import PosRepository
    from datapulse.pos.voucher_repository import VoucherRepository


__all__ = [
    "PosService",
    # Back-compat re-exports — existing tests import these names from here.
    "_build_receipt_number",
    "_is_controlled",
    "_select_fefo_batch",
    "_to_decimal",
]


class PosService(
    TerminalOpsMixin,
    CartOpsMixin,
    CheckoutMixin,
    VoidReturnMixin,
    CatalogMixin,
    ShiftCashMixin,
    DeliveryMixin,
):
    """Business logic for POS terminal + transaction lifecycle.

    Methods that touch the (async) inventory protocol are ``async``; pure-DB
    methods stay synchronous so they remain cheap to call from sync routes
    and tests.

    The class is intentionally a thin composition of domain mixins — each
    mixin owns one cohesive slice of the POS surface. The ``__init__`` here
    is the single source of truth for shared collaborators, so every mixin
    can reach its dependencies via ``self._repo``, ``self._inventory`` etc.
    without extra plumbing.
    """

    def __init__(
        self,
        repo: PosRepository,
        inventory: InventoryServiceProtocol,
        verifier: PharmacistVerifier | None = None,
        voucher_repo: VoucherRepository | None = None,
        promotion_repo: PromotionRepository | None = None,
    ) -> None:
        self._repo = repo
        self._inventory = inventory
        self._verifier = verifier
        # Optional to preserve backward compat with existing call sites.
        # When None, vouchers silently bypass the legacy checkout path
        # (canonical redemption still happens on POST /pos/transactions/commit).
        self._voucher_repo = voucher_repo
        # Promotions follow the same optional-wiring pattern as vouchers.
        self._promotion_repo = promotion_repo

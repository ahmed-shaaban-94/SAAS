"""Draft-transaction and cart-item mixin for :class:`PosService`.

Owns the draft-transaction header (create/get/list) and the line-item lifecycle
(add/update/remove). Cart-add is async because it talks to the inventory
protocol for stock checks and FEFO batch selection.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from datapulse.logging import get_logger
from datapulse.pos._service_helpers import (
    is_controlled,
    select_fefo_batch,
    to_decimal,
)
from datapulse.pos.constants import TerminalStatus
from datapulse.pos.exceptions import (
    InsufficientStockError,
    PharmacistVerificationRequiredError,
    PosError,
)
from datapulse.pos.inventory_contract import StockMovement  # noqa: F401 - re-exported for tests
from datapulse.pos.models import (
    PosCartItem,
    TransactionDetailResponse,
    TransactionResponse,
)
from datapulse.pos.terminal import assert_transactable

if TYPE_CHECKING:
    from datapulse.pos.inventory_contract import InventoryServiceProtocol
    from datapulse.pos.pharmacist_verifier import PharmacistVerifier
    from datapulse.pos.repository import PosRepository

log = get_logger(__name__)


class CartOpsMixin:
    """Mixin providing draft-transaction and cart-line CRUD.

    Requires ``self._repo``, ``self._inventory``, and ``self._verifier`` to be
    set by :meth:`PosService.__init__`.
    """

    _repo: PosRepository
    _inventory: InventoryServiceProtocol
    _verifier: PharmacistVerifier | None

    def create_transaction(
        self,
        *,
        tenant_id: int,
        terminal_id: int,
        staff_id: str,
        site_code: str,
        pharmacist_id: str | None = None,
        customer_id: str | None = None,
    ) -> TransactionResponse:
        """Open a draft transaction on an active/open terminal."""
        terminal = self._repo.get_terminal_session(terminal_id)
        if terminal is None:
            raise PosError(
                message=f"Terminal {terminal_id} does not exist",
                detail=f"terminal_id={terminal_id}",
            )
        assert_transactable(terminal_id, terminal["status"])

        # Lazily promote ``open`` -> ``active`` on first transaction
        if terminal["status"] == TerminalStatus.open.value:
            self._repo.update_terminal_status(terminal_id, TerminalStatus.active.value)

        row = self._repo.create_transaction(
            tenant_id=tenant_id,
            terminal_id=terminal_id,
            staff_id=staff_id,
            site_code=site_code,
            pharmacist_id=pharmacist_id,
            customer_id=customer_id,
        )
        return TransactionResponse.model_validate(row)

    def get_transaction_detail(self, transaction_id: int) -> TransactionDetailResponse | None:
        """Full transaction with line items hydrated."""
        header = self._repo.get_transaction(transaction_id)
        if header is None:
            return None
        item_rows = self._repo.get_transaction_items(transaction_id)
        items = [PosCartItem.model_validate(r) for r in item_rows]
        return TransactionDetailResponse.model_validate({**header, "items": items})

    def list_transactions(
        self,
        *,
        tenant_id: int,
        terminal_id: int | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TransactionResponse]:
        rows = self._repo.list_transactions(
            tenant_id,
            terminal_id=terminal_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return [TransactionResponse.model_validate(r) for r in rows]

    async def add_item(
        self,
        *,
        transaction_id: int,
        tenant_id: int,
        site_code: str,
        drug_code: str,
        quantity: Decimal,
        override_price: Decimal | None = None,
        pharmacist_id: str | None = None,
    ) -> PosCartItem:
        """Stock-checked, FEFO-batched insert of a cart line item.

        Steps:
        1. Resolve drug metadata (name, category, default unit_price).
        2. Check controlled substance: require pharmacist_id when category matches.
        3. Verify stock via :class:`InventoryServiceProtocol`.
        4. Pick FEFO batch.
        5. Compute line_total = quantity * unit_price.
        6. Persist via repository.

        Raises :class:`InsufficientStockError`, :class:`PharmacistVerificationRequiredError`.
        """
        product = self._repo.get_product_by_code(drug_code)
        if product is None:
            raise PosError(
                message=f"Drug {drug_code} not found in product catalog",
                detail=f"drug_code={drug_code}",
            )

        controlled = is_controlled(product.get("drug_category"))
        resolved_pharmacist_id: str | None = None
        if controlled:
            if not pharmacist_id:
                raise PharmacistVerificationRequiredError(
                    drug_code=drug_code,
                    drug_category=product.get("drug_category"),
                )
            if self._verifier is None:
                # Defense in depth: a controlled item must never be dispensed
                # without a server-side verifier to validate the token signature.
                raise PharmacistVerificationRequiredError(
                    drug_code=drug_code,
                    message="Pharmacist verification is not configured on this server.",
                )
            # The ``pharmacist_id`` parameter carries the signed token issued by
            # POST /pos/controlled/verify, not a raw user id. Validate signature,
            # drug-code binding, and TTL; returns the real pharmacist user id.
            resolved_pharmacist_id = self._verifier.validate_token(pharmacist_id, drug_code)

        # Inventory: stock check
        stock = await self._inventory.get_stock_level(drug_code, site_code)
        if stock.quantity_available < quantity:
            raise InsufficientStockError(
                drug_code=drug_code,
                requested=quantity,
                available=stock.quantity_available,
                site_code=site_code,
            )

        # Inventory: FEFO batch selection
        batches = await self._inventory.check_batch_expiry(drug_code, site_code)
        chosen = select_fefo_batch(batches, quantity)
        # Fall back to "no batch" so the line is still recorded for traceability.
        batch_number = chosen.batch_number if chosen else None
        expiry_date = chosen.expiry_date if chosen else None

        unit_price = (
            to_decimal(override_price)
            if override_price is not None
            else to_decimal(product.get("unit_price", 0))
        )
        line_total = (unit_price * quantity).quantize(Decimal("0.0001"))

        row = self._repo.add_transaction_item(
            transaction_id=transaction_id,
            tenant_id=tenant_id,
            drug_code=drug_code,
            drug_name=product["drug_name"],
            quantity=quantity,
            unit_price=unit_price,
            line_total=line_total,
            batch_number=batch_number,
            expiry_date=expiry_date,
            is_controlled=controlled,
            pharmacist_id=resolved_pharmacist_id,
        )
        return PosCartItem.model_validate(row)

    def update_item(
        self,
        item_id: int,
        *,
        quantity: Decimal,
        unit_price: Decimal,
        discount: Decimal | None = None,
    ) -> PosCartItem:
        """Recalculate ``line_total`` for an existing line item."""
        line_total = (unit_price * quantity).quantize(Decimal("0.0001"))
        if discount is not None:
            line_total = (line_total - to_decimal(discount)).quantize(Decimal("0.0001"))
        row = self._repo.update_item_quantity(
            item_id,
            quantity=quantity,
            line_total=line_total,
            discount=discount,
        )
        if row is None:
            raise PosError(
                message=f"Item {item_id} not found",
                detail=f"item_id={item_id}",
            )
        # ``unit_price`` is not returned by update_item_quantity; merge it in for the response.
        return PosCartItem.model_validate(
            {**row, "unit_price": unit_price, "drug_name": row.get("drug_name", "")}
        )

    def remove_item(self, item_id: int) -> bool:
        """Delete a single item from a draft transaction."""
        return self._repo.remove_item(item_id)

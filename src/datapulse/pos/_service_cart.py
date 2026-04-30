"""Draft-transaction and cart-item mixin for :class:`PosService`.

Owns the draft-transaction header (create/get/list) and the line-item lifecycle
(add/update/remove). Cart-add is async because it talks to the inventory
protocol for stock checks and FEFO batch selection.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import TYPE_CHECKING

from datapulse.logging import get_logger
from datapulse.pos._service_helpers import (
    is_controlled,
    select_fefo_batch,
    to_decimal,
)
from datapulse.pos.constants import TerminalStatus, TransactionStatus
from datapulse.pos.exceptions import (
    InsufficientStockError,
    PharmacistVerificationRequiredError,
    PosConflictError,
    PosNotFoundError,
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
        terminal = self._repo.get_terminal_session(terminal_id, tenant_id=tenant_id)
        if terminal is None:
            raise PosNotFoundError(
                "terminal_not_found",
                message=f"Terminal {terminal_id} does not exist",
            )
        assert_transactable(terminal_id, terminal["status"])

        # Lazily promote ``open`` -> ``active`` on first transaction
        if terminal["status"] == TerminalStatus.open.value:
            self._repo.update_terminal_status(
                terminal_id, TerminalStatus.active.value, tenant_id=tenant_id
            )

        row = self._repo.create_transaction(
            tenant_id=tenant_id,
            terminal_id=terminal_id,
            staff_id=staff_id,
            site_code=site_code,
            pharmacist_id=pharmacist_id,
            customer_id=customer_id,
        )
        return TransactionResponse.model_validate(row)

    def get_transaction_detail(
        self, transaction_id: int, *, tenant_id: int
    ) -> TransactionDetailResponse | None:
        """Full transaction with line items hydrated."""
        header = self._repo.get_transaction(transaction_id, tenant_id=tenant_id)
        if header is None:
            return None
        item_rows = self._repo.get_transaction_items(transaction_id, tenant_id=tenant_id)
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
        t0 = time.perf_counter()

        product = self._repo.get_product_by_code(drug_code)
        stock_check_ms = round((time.perf_counter() - t0) * 1000, 2)

        if product is None:
            raise PosNotFoundError(
                "drug_not_found",
                message=f"Drug {drug_code} not found in product catalog",
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
        t1 = time.perf_counter()
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
        batch_select_ms = round((time.perf_counter() - t1) * 1000, 2)

        # Fall back to "no batch" so the line is still recorded for traceability.
        batch_number = chosen.batch_number if chosen else None
        expiry_date = chosen.expiry_date if chosen else None

        unit_price = (
            to_decimal(override_price)
            if override_price is not None
            else to_decimal(product.get("unit_price", 0))
        )
        line_total = (unit_price * quantity).quantize(Decimal("0.0001"))

        # Capture cost_per_unit from catalog data for margin tracking.
        # Falls back to None when the product has no cost data so existing
        # records (pre-migration 119) are never blocked. A follow-up migration
        # can backfill / add NOT NULL after all rows are populated.
        raw_cost = product.get("cost_price") or product.get("cost_per_unit")
        cost_per_unit: Decimal | None = to_decimal(raw_cost) if raw_cost is not None else None

        t2 = time.perf_counter()
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
            cost_per_unit=cost_per_unit,
        )
        db_write_ms = round((time.perf_counter() - t2) * 1000, 2)
        total_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Audit H4 (2026-04-26): make the cost-data gap observable. agg_basket_margin
        # treats NULL cost as zero, which silently inflates margin KPIs whenever
        # dim_product / drug_catalog hasn't been populated. Emitted *after* the DB
        # write succeeds so the log only counts persisted gaps — a failed insert
        # never produces a phantom "missing cost" event.
        if cost_per_unit is None:
            log.warning(
                "cart_cost_price_missing",
                drug_code=drug_code,
                tenant_id=tenant_id,
                detail=(
                    "Product has no cost_price/cost_per_unit; line stored "
                    "with NULL cost — margin reports will treat it as zero "
                    "cost. Backfill dim_product or drug_catalog."
                ),
            )

        log.info(
            "cart_add_item_timing",
            tenant_id=tenant_id,
            drug_code=drug_code,
            stock_check_ms=stock_check_ms,
            batch_select_ms=batch_select_ms,
            db_write_ms=db_write_ms,
            total_ms=total_ms,
        )
        if total_ms > 500:
            log.warning(
                "cart_slow_op",
                operation="add_item",
                total_ms=total_ms,
                tenant_id=tenant_id,
            )

        return PosCartItem.model_validate(row)

    def update_item(
        self,
        item_id: int,
        *,
        tenant_id: int,
        quantity: Decimal,
        unit_price: Decimal | None = None,
        discount: Decimal | None = None,
        transaction_id: int | None = None,
    ) -> PosCartItem:
        """Update an existing line item's quantity (+ optional price/discount).

        ``unit_price=None`` means "leave the existing price alone" — the
        SQL UPDATE recomputes ``line_total`` from the persisted price, so
        a pure quantity change cannot zero the line by passing 0 here
        (Codex P1). The SQL also has a status guard: a non-draft parent
        transaction cannot have its lines mutated.

        We still issue a service-side status check first so the caller
        gets a clear ``PosError`` (vs. a silent no-op when the SQL
        WHERE clause filters everything out).
        """
        existing = self._repo.get_transaction_item(item_id, tenant_id=tenant_id)
        if existing is None:
            raise PosNotFoundError("item_not_found", message=f"Item {item_id} not found")
        existing_transaction_id = int(existing["transaction_id"])
        if transaction_id is not None and existing_transaction_id != transaction_id:
            raise PosConflictError(
                "item_transaction_mismatch",
                message=f"Item {item_id} does not belong to transaction {transaction_id}",
            )

        header = self._repo.get_transaction(existing_transaction_id, tenant_id=tenant_id)
        if header is None:
            raise PosNotFoundError(
                "transaction_not_found",
                message=f"Transaction {existing_transaction_id} not found",
            )
        if header["status"] != TransactionStatus.draft.value:
            raise PosConflictError(
                "transaction_not_draft",
                message=f"Only draft transactions can be edited (current: {header['status']}).",
            )

        t0 = time.perf_counter()
        row = self._repo.update_item_quantity(
            item_id,
            tenant_id=tenant_id,
            quantity=quantity,
            unit_price=to_decimal(unit_price) if unit_price is not None else None,
            discount=to_decimal(discount) if discount is not None else None,
            transaction_id=existing_transaction_id,
            expected_status=TransactionStatus.draft.value,
        )
        db_write_ms = round((time.perf_counter() - t0) * 1000, 2)

        if row is None:
            raise PosNotFoundError("item_not_found", message=f"Item {item_id} not found")

        log.info(
            "cart_update_item_timing",
            tenant_id=tenant_id,
            item_id=item_id,
            db_write_ms=db_write_ms,
        )
        if db_write_ms > 500:
            log.warning(
                "cart_slow_op",
                operation="update_item",
                total_ms=db_write_ms,
                tenant_id=tenant_id,
            )

        # The repo SQL returns the resulting unit_price and line_total
        # straight from the row — no client-side merge needed.
        return PosCartItem.model_validate({**row, "drug_name": row.get("drug_name", "")})

    def remove_item(
        self, item_id: int, *, tenant_id: int, transaction_id: int | None = None
    ) -> bool:
        """Delete a single item from a draft transaction."""
        existing = self._repo.get_transaction_item(item_id, tenant_id=tenant_id)
        if existing is None:
            return False
        existing_transaction_id = int(existing["transaction_id"])
        if transaction_id is not None and existing_transaction_id != transaction_id:
            return False
        header = self._repo.get_transaction(existing_transaction_id, tenant_id=tenant_id)
        if header is not None and header["status"] != TransactionStatus.draft.value:
            raise PosConflictError(
                "transaction_not_draft",
                message=f"Only draft transactions can be edited (current: {header['status']}).",
            )
        t0 = time.perf_counter()
        result = self._repo.remove_item(
            item_id,
            tenant_id=tenant_id,
            transaction_id=existing_transaction_id,
            expected_status=TransactionStatus.draft.value,
        )
        db_write_ms = round((time.perf_counter() - t0) * 1000, 2)

        log.info(
            "cart_remove_item_timing",
            tenant_id=tenant_id,
            item_id=item_id,
            db_write_ms=db_write_ms,
        )
        if db_write_ms > 500:
            log.warning(
                "cart_slow_op",
                operation="remove_item",
                total_ms=db_write_ms,
                tenant_id=tenant_id,
            )

        return result

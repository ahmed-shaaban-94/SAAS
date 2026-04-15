"""POS business logic — orchestrates terminal sessions, cart, checkout, bronze write.

The service is the single entry-point used by API routes; it composes the
:class:`PosRepository` (raw SQL) and the (mocked-until-Plan-A-merges)
:class:`InventoryServiceProtocol` (async stock + batch + movement).

Design
------
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

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from datapulse.logging import get_logger
from datapulse.pos.constants import (
    CONTROLLED_CATEGORIES,
    TerminalStatus,
    TransactionStatus,
)
from datapulse.pos.exceptions import (
    InsufficientStockError,
    PharmacistVerificationRequiredError,
    PosError,
)
from datapulse.pos.inventory_contract import (
    BatchInfo,
    InventoryServiceProtocol,
    StockMovement,
)
from datapulse.pos.models import (
    BatchSummary,
    CheckoutRequest,
    CheckoutResponse,
    PosCartItem,
    PosProductResult,
    PosStockInfo,
    TerminalSession,
    TransactionDetailResponse,
    TransactionResponse,
)
from datapulse.pos.payment import get_gateway
from datapulse.pos.receipt import generate_pdf_receipt, generate_thermal_receipt
from datapulse.pos.repository import PosRepository
from datapulse.pos.terminal import (
    assert_can_transition,
    assert_transactable,
)

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_decimal(value: Any) -> Decimal:
    """Coerce an int/float/str/Decimal/None into a Decimal (None -> 0)."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _is_controlled(category: str | None) -> bool:
    """Return True when the drug category is in the controlled-substance list."""
    if not category:
        return False
    return category.lower() in CONTROLLED_CATEGORIES


def _build_receipt_number(tenant_id: int, transaction_id: int) -> str:
    """Deterministic receipt number: ``R{YYYYMMDD}-{tenant}-{txn_id}``."""
    today = datetime.now(tz=UTC).strftime("%Y%m%d")
    return f"R{today}-{tenant_id}-{transaction_id}"


def _select_fefo_batch(
    batches: list[BatchInfo],
    requested_qty: Decimal,
) -> BatchInfo | None:
    """Pick the earliest-expiring batch whose ``quantity_available`` >= requested.

    Implements **First-Expired-First-Out** (FEFO). Batches without an expiry
    date are considered last (treated as far-future). Returns ``None`` when no
    single batch can satisfy the request — the caller should then either
    decline the line or split across batches (out of scope for B3).
    """
    far_future = date.max
    sorted_batches = sorted(
        batches,
        key=lambda b: (b.expiry_date or far_future, b.batch_number),
    )
    for batch in sorted_batches:
        if batch.quantity_available >= requested_qty:
            return batch
    return None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class PosService:
    """Business logic for POS terminal + transaction lifecycle.

    Methods that touch the (async) inventory protocol are ``async``; pure-DB
    methods stay synchronous so they remain cheap to call from sync routes
    and tests.
    """

    def __init__(
        self,
        repo: PosRepository,
        inventory: InventoryServiceProtocol,
    ) -> None:
        self._repo = repo
        self._inventory = inventory

    # ──────────────────────────────────────────────────────────────
    # Terminal lifecycle
    # ──────────────────────────────────────────────────────────────

    def open_terminal(
        self,
        *,
        tenant_id: int,
        site_code: str,
        staff_id: str,
        terminal_name: str = "Terminal-1",
        opening_cash: Decimal = Decimal("0"),
    ) -> TerminalSession:
        """Open a fresh terminal session in ``open`` state."""
        row = self._repo.create_terminal_session(
            tenant_id=tenant_id,
            site_code=site_code,
            staff_id=staff_id,
            terminal_name=terminal_name,
            opening_cash=opening_cash,
        )
        log.info("pos.terminal.opened", terminal_id=row["id"], staff_id=staff_id)
        return TerminalSession.model_validate(row)

    def _transition_terminal(
        self,
        terminal_id: int,
        target: TerminalStatus,
        *,
        closing_cash: Decimal | None = None,
    ) -> TerminalSession:
        """Validate + apply a terminal status change. Raises if illegal."""
        current = self._repo.get_terminal_session(terminal_id)
        if current is None:
            raise PosError(
                message=f"Terminal {terminal_id} does not exist",
                detail=f"terminal_id={terminal_id}",
            )
        assert_can_transition(terminal_id, current["status"], target)
        updated = self._repo.update_terminal_status(
            terminal_id, target.value, closing_cash=closing_cash
        )
        if updated is None:
            raise PosError(
                message=f"Terminal {terminal_id} update failed",
                detail=f"terminal_id={terminal_id} target={target.value}",
            )
        return TerminalSession.model_validate(updated)

    def pause_terminal(self, terminal_id: int) -> TerminalSession:
        """Move ``active`` -> ``paused``."""
        return self._transition_terminal(terminal_id, TerminalStatus.paused)

    def resume_terminal(self, terminal_id: int) -> TerminalSession:
        """Move ``paused`` -> ``active``."""
        return self._transition_terminal(terminal_id, TerminalStatus.active)

    def close_terminal(
        self,
        terminal_id: int,
        *,
        closing_cash: Decimal,
    ) -> TerminalSession:
        """Close a terminal session and record the closing cash drawer total."""
        return self._transition_terminal(
            terminal_id, TerminalStatus.closed, closing_cash=closing_cash
        )

    def list_active_terminals(self, tenant_id: int) -> list[TerminalSession]:
        """All non-closed terminals for the tenant."""
        rows = self._repo.get_active_terminals(tenant_id)
        return [TerminalSession.model_validate(r) for r in rows]

    def get_terminal(self, terminal_id: int) -> TerminalSession | None:
        row = self._repo.get_terminal_session(terminal_id)
        return TerminalSession.model_validate(row) if row else None

    # ──────────────────────────────────────────────────────────────
    # Transactions
    # ──────────────────────────────────────────────────────────────

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

    # ──────────────────────────────────────────────────────────────
    # Cart items (async — touches inventory)
    # ──────────────────────────────────────────────────────────────

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

        is_controlled = _is_controlled(product.get("drug_category"))
        if is_controlled and not pharmacist_id:
            raise PharmacistVerificationRequiredError(
                drug_code=drug_code,
                drug_category=product.get("drug_category"),
            )

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
        chosen = _select_fefo_batch(batches, quantity)
        # Fall back to "no batch" so the line is still recorded for traceability.
        batch_number = chosen.batch_number if chosen else None
        expiry_date = chosen.expiry_date if chosen else None

        unit_price = (
            _to_decimal(override_price)
            if override_price is not None
            else _to_decimal(product.get("unit_price", 0))
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
            is_controlled=is_controlled,
            pharmacist_id=pharmacist_id if is_controlled else None,
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
            line_total = (line_total - _to_decimal(discount)).quantize(Decimal("0.0001"))
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

    # ──────────────────────────────────────────────────────────────
    # Checkout (async — records inventory movements + bronze write)
    # ──────────────────────────────────────────────────────────────

    async def checkout(
        self,
        *,
        transaction_id: int,
        tenant_id: int,
        request: CheckoutRequest,
    ) -> CheckoutResponse:
        """Finalise a draft transaction: totals -> payment -> stock -> bronze.

        Payment processing is intentionally minimal in B3 — it computes
        change for cash and validates sufficient tender. Card / insurance
        / split flows are added in B4 via the :class:`PaymentGateway` ABC.
        """
        header = self._repo.get_transaction(transaction_id)
        if header is None:
            raise PosError(
                message=f"Transaction {transaction_id} not found",
                detail=f"transaction_id={transaction_id}",
            )
        if header["status"] != TransactionStatus.draft.value:
            raise PosError(
                message=f"Transaction {transaction_id} is not in draft state "
                f"(current: {header['status']}). Only draft transactions can be checked out.",
                detail=f"transaction_id={transaction_id} status={header['status']}",
            )

        items = self._repo.get_transaction_items(transaction_id)
        if not items:
            raise PosError(
                message=f"Transaction {transaction_id} has no items to check out",
                detail=f"transaction_id={transaction_id}",
            )

        # ── Totals ──────────────────────────────────────────────────
        subtotal = sum(
            (_to_decimal(i["line_total"]) for i in items),
            start=Decimal("0"),
        )
        discount_total = _to_decimal(request.transaction_discount) + sum(
            (_to_decimal(i.get("discount", 0)) for i in items),
            start=Decimal("0"),
        )
        tax_total = Decimal("0")  # Tax engine added in a later session
        grand_total = subtotal - _to_decimal(request.transaction_discount) + tax_total
        grand_total = grand_total.quantize(Decimal("0.0001"))

        # ── Payment (B4: gateway delegation) ───────────────────────
        gateway = get_gateway(request.payment_method.value)
        payment_result = gateway.process_payment(
            grand_total,
            tendered=_to_decimal(request.cash_tendered or 0),
            insurance_no=request.insurance_no,
        )
        payment_result.raise_if_failed()
        change_due = payment_result.change_due

        receipt_number = _build_receipt_number(tenant_id, transaction_id)

        updated = self._repo.update_transaction_status(
            transaction_id,
            status=TransactionStatus.completed.value,
            payment_method=request.payment_method.value,
            receipt_number=receipt_number,
            subtotal=subtotal.quantize(Decimal("0.0001")),
            discount_total=discount_total.quantize(Decimal("0.0001")),
            tax_total=tax_total,
            grand_total=grand_total,
            customer_id=request.customer_id,
        )
        if updated is None:
            raise PosError(
                message=f"Failed to finalise transaction {transaction_id}",
                detail=f"transaction_id={transaction_id}",
            )

        # ── Inventory movements + bronze write ──────────────────────
        # Use the receipt_number as the bronze.transaction_id with a
        # ``'POS-'`` prefix to prevent collision with ERP rows (C3 fix).
        bronze_txn_id = f"POS-{receipt_number}"
        now = datetime.now(tz=UTC)
        for item in items:
            await self._inventory.record_movement(
                StockMovement(
                    drug_code=item["drug_code"],
                    site_code=header["site_code"],
                    quantity_delta=-_to_decimal(item["quantity"]),
                    batch_number=item.get("batch_number"),
                    reference_id=bronze_txn_id,
                    movement_type="sale",
                ),
            )
            self._repo.insert_bronze_pos_transaction(
                tenant_id=tenant_id,
                transaction_id=bronze_txn_id,
                transaction_date=now,
                site_code=header["site_code"],
                register_id=str(header["terminal_id"]),
                cashier_id=str(header["staff_id"]),
                customer_id=request.customer_id,
                drug_code=item["drug_code"],
                batch_number=item.get("batch_number"),
                quantity=_to_decimal(item["quantity"]),
                unit_price=_to_decimal(item["unit_price"]),
                discount=_to_decimal(item.get("discount", 0)),
                net_amount=_to_decimal(item["line_total"]),
                payment_method=request.payment_method.value,
                insurance_no=request.insurance_no,
                is_return=False,
                pharmacist_id=item.get("pharmacist_id"),
            )

        # ── Receipt generation (B4) ────────────────────────────────
        payment_info = {
            "method": request.payment_method.value,
            "amount_charged": float(grand_total),
            "change_due": float(change_due),
            "insurance_no": request.insurance_no,
        }
        txn_for_receipt = {
            **header,
            "receipt_number": receipt_number,
            "grand_total": grand_total,
            "subtotal": subtotal,
            "discount_total": discount_total,
            "tax_total": tax_total,
        }
        for fmt, content in (
            ("thermal", generate_thermal_receipt(txn_for_receipt, items, payment_info)),
            ("pdf", generate_pdf_receipt(txn_for_receipt, items, payment_info)),
        ):
            self._repo.save_receipt(
                transaction_id=transaction_id,
                tenant_id=tenant_id,
                fmt=fmt,
                content=content,
            )

        log.info(
            "pos.checkout.completed",
            transaction_id=transaction_id,
            receipt_number=receipt_number,
            grand_total=str(grand_total),
            payment_method=request.payment_method.value,
        )

        return CheckoutResponse(
            transaction_id=transaction_id,
            receipt_number=receipt_number,
            grand_total=grand_total,
            payment_method=request.payment_method,
            change_due=change_due,
            status=TransactionStatus.completed,
        )

    # ──────────────────────────────────────────────────────────────
    # Product / stock lookups
    # ──────────────────────────────────────────────────────────────

    def search_products(
        self,
        query: str,
        *,
        site_code: str | None = None,
        limit: int = 20,
    ) -> list[PosProductResult]:
        """Search the product catalog. ``site_code`` reserved for future per-site stock joins.

        Stock quantity is left at 0 here; callers that need live stock should
        call :meth:`get_stock_info` for the selected drug.
        """
        _ = site_code  # reserved
        rows = self._repo.search_dim_products(query, limit=limit)
        results: list[PosProductResult] = []
        for r in rows:
            results.append(
                PosProductResult(
                    drug_code=r["drug_code"],
                    drug_name=r["drug_name"],
                    drug_brand=r.get("drug_brand"),
                    drug_cluster=r.get("drug_cluster"),
                    unit_price=_to_decimal(r.get("unit_price", 0)),
                    stock_quantity=Decimal("0"),
                    is_controlled=_is_controlled(r.get("drug_category")),
                    requires_pharmacist=_is_controlled(r.get("drug_category")),
                ),
            )
        return results

    async def get_stock_info(
        self,
        drug_code: str,
        site_code: str,
    ) -> PosStockInfo:
        """Return live stock + per-batch info for a single drug at a site."""
        stock = await self._inventory.get_stock_level(drug_code, site_code)
        batches = await self._inventory.check_batch_expiry(drug_code, site_code)
        return PosStockInfo(
            drug_code=drug_code,
            site_code=site_code,
            quantity_available=stock.quantity_available,
            batches=[
                BatchSummary(
                    batch_number=b.batch_number,
                    expiry_date=b.expiry_date,
                    quantity_available=b.quantity_available,
                )
                for b in batches
            ],
        )

    # ──────────────────────────────────────────────────────────────
    # Receipts (B4)
    # ──────────────────────────────────────────────────────────────

    def get_receipt_pdf(self, transaction_id: int, tenant_id: int) -> bytes:
        """Return stored PDF receipt bytes; regenerate on demand if missing."""
        row = self._repo.get_receipt(transaction_id, "pdf")
        if row and row.get("content"):
            return bytes(row["content"])
        return self._regenerate_receipt(transaction_id, tenant_id, "pdf")

    def get_receipt_thermal(self, transaction_id: int, tenant_id: int) -> bytes:
        """Return stored thermal ESC/POS bytes; regenerate on demand if missing."""
        row = self._repo.get_receipt(transaction_id, "thermal")
        if row and row.get("content"):
            return bytes(row["content"])
        return self._regenerate_receipt(transaction_id, tenant_id, "thermal")

    def _regenerate_receipt(self, transaction_id: int, tenant_id: int, fmt: str) -> bytes:
        """Regenerate a receipt on demand (fallback when no stored receipt exists)."""
        from fastapi import HTTPException  # local import avoids circular dependency

        header = self._repo.get_transaction(transaction_id)
        if header is None:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
        items = self._repo.get_transaction_items(transaction_id)
        payment_info = {
            "method": header.get("payment_method", "cash"),
            "amount_charged": float(_to_decimal(header.get("grand_total", 0))),
            "change_due": 0.0,
            "insurance_no": None,
        }
        content = (
            generate_pdf_receipt(header, items, payment_info)
            if fmt == "pdf"
            else generate_thermal_receipt(header, items, payment_info)
        )
        self._repo.save_receipt(
            transaction_id=transaction_id,
            tenant_id=tenant_id,
            fmt=fmt,
            content=content,
        )
        return content

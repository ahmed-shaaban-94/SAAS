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

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from datapulse.logging import get_logger
from datapulse.pos.constants import (
    CONTROLLED_CATEGORIES,
    ReturnReason,
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
    CashDrawerEventResponse,
    CatalogProductEntry,
    CatalogProductPage,
    CatalogStockEntry,
    CatalogStockPage,
    CheckoutRequest,
    CheckoutResponse,
    PharmacistVerifyResponse,
    PosCartItem,
    PosProductResult,
    PosStockInfo,
    ReturnDetailResponse,
    ReturnResponse,
    ShiftRecord,
    ShiftSummaryResponse,
    TerminalSession,
    TransactionDetailResponse,
    TransactionResponse,
    VoidResponse,
)
from datapulse.pos.payment import get_gateway
from datapulse.pos.pharmacist_verifier import TOKEN_TTL_SECONDS, PharmacistVerifier
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
        verifier: PharmacistVerifier | None = None,
    ) -> None:
        self._repo = repo
        self._inventory = inventory
        self._verifier = verifier

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
        resolved_pharmacist_id: str | None = None
        if is_controlled:
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

    def get_catalog_products(
        self,
        cursor: str | None,
        limit: int,
    ) -> CatalogProductPage:
        """Return a paginated slice of the full product catalog for offline sync.

        *cursor* is the last ``drug_code`` received; pass ``None`` for the first
        page.  When the returned ``next_cursor`` is ``None`` the catalog is
        exhausted and the desktop should reset to cursor=None on the next cycle.
        """
        rows = self._repo.list_catalog_products(cursor=cursor, limit=limit)
        now_iso = datetime.now(tz=UTC).replace(microsecond=0).isoformat()
        items = [
            CatalogProductEntry(
                drug_code=r["drug_code"],
                drug_name=r["drug_name"],
                drug_brand=r.get("drug_brand"),
                drug_cluster=r.get("drug_cluster"),
                drug_category=r.get("drug_category"),
                is_controlled=_is_controlled(r.get("drug_category")),
                requires_pharmacist=_is_controlled(r.get("drug_category")),
                unit_price=_to_decimal(r.get("unit_price", 0)),
                updated_at=now_iso,
            )
            for r in rows
        ]
        next_cursor = items[-1].drug_code if len(items) == limit else None
        return CatalogProductPage(items=items, next_cursor=next_cursor)

    def get_catalog_stock(
        self,
        site: str | None,
        cursor: str | None,
        limit: int,
    ) -> CatalogStockPage:
        """Return a paginated slice of active batches from stg_batches for offline sync.

        *cursor* is the last ``loaded_at`` ISO timestamp received; pass ``None``
        for the first page.  When the returned ``next_cursor`` is ``None`` all
        active batches have been delivered for this cycle.
        """
        rows = self._repo.list_catalog_stock(site=site, cursor=cursor, limit=limit)
        items = [
            CatalogStockEntry(
                drug_code=r["drug_code"],
                site_code=r["site_code"],
                batch_number=r["batch_number"],
                quantity=_to_decimal(r.get("current_quantity", 0)),
                expiry_date=r.get("expiry_date"),
                updated_at=(
                    r["loaded_at"].isoformat()
                    if hasattr(r["loaded_at"], "isoformat")
                    else str(r["loaded_at"])
                ),
            )
            for r in rows
        ]
        next_cursor = items[-1].updated_at if len(items) == limit else None
        return CatalogStockPage(items=items, next_cursor=next_cursor)

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

    # ──────────────────────────────────────────────────────────────
    # Void (B6a)
    # ──────────────────────────────────────────────────────────────

    async def void_transaction(
        self,
        *,
        transaction_id: int,
        tenant_id: int,
        reason: str,
        voided_by: str,
    ) -> VoidResponse:
        """Void a completed transaction — reverses inventory, writes audit log.

        Only ``completed`` transactions may be voided. Draft transactions are
        abandoned by removing all items; voiding a ``voided`` transaction raises.

        Raises :class:`PosError` for not-found or wrong-state.
        """
        header = self._repo.get_transaction(transaction_id)
        if header is None:
            raise PosError(
                message=f"Transaction {transaction_id} not found",
                detail=f"transaction_id={transaction_id}",
            )
        if header["status"] != TransactionStatus.completed.value:
            raise PosError(
                message=(
                    f"Only completed transactions can be voided (current: {header['status']})"
                ),
                detail=f"transaction_id={transaction_id} status={header['status']}",
            )

        # Reverse inventory movements first — before status update
        items = self._repo.get_transaction_items(transaction_id)
        for item in items:
            await self._inventory.record_movement(
                StockMovement(
                    drug_code=item["drug_code"],
                    site_code=header["site_code"],
                    quantity_delta=_to_decimal(item["quantity"]),  # positive = restock
                    batch_number=item.get("batch_number"),
                    reference_id=f"VOID-{transaction_id}",
                    movement_type="void",
                ),
            )

        self._repo.update_transaction_status(
            transaction_id,
            status=TransactionStatus.voided.value,
        )

        void_row = self._repo.create_void_log(
            transaction_id=transaction_id,
            tenant_id=tenant_id,
            voided_by=voided_by,
            reason=reason,
        )

        log.info(
            "pos.void.completed",
            transaction_id=transaction_id,
            voided_by=voided_by,
        )
        return VoidResponse.model_validate(void_row)

    # ──────────────────────────────────────────────────────────────
    # Returns (B6a)
    # ──────────────────────────────────────────────────────────────

    async def process_return(
        self,
        *,
        original_transaction_id: int,
        tenant_id: int,
        staff_id: str,
        items: list[PosCartItem],
        reason: ReturnReason,
        refund_method: str,
        notes: str | None = None,
    ) -> ReturnResponse:
        """Process a drug return — creates return transaction, restocks inventory.

        Steps
        -----
        1. Verify original transaction is completed.
        2. Compute refund amount from returned items.
        3. Create a ``returned``-status transaction (links back to original terminal).
        4. Insert return items into ``pos.transaction_items``.
        5. Create a ``pos.returns`` audit record.
        6. Record positive inventory movements (restock).
        7. Write bronze entries with ``is_return=True``.

        Raises :class:`PosError` for not-found, wrong-state, or empty items.
        """
        original = self._repo.get_transaction(original_transaction_id)
        if original is None:
            raise PosError(
                message=f"Transaction {original_transaction_id} not found",
                detail=f"original_transaction_id={original_transaction_id}",
            )
        if original["status"] != TransactionStatus.completed.value:
            raise PosError(
                message=(
                    f"Returns only allowed on completed transactions "
                    f"(current: {original['status']})"
                ),
                detail=(
                    f"original_transaction_id={original_transaction_id} status={original['status']}"
                ),
            )
        if not items:
            raise PosError(
                message="Return must include at least one item",
                detail=f"original_transaction_id={original_transaction_id}",
            )

        refund_amount = sum(
            (_to_decimal(item.line_total) for item in items),
            start=Decimal("0"),
        ).quantize(Decimal("0.0001"))

        # Create a return transaction on the same terminal
        terminal_id = int(original["terminal_id"])
        site_code = str(original["site_code"])
        return_txn = self._repo.create_transaction(
            tenant_id=tenant_id,
            terminal_id=terminal_id,
            staff_id=staff_id,
            site_code=site_code,
        )
        return_txn_id = int(return_txn["id"])

        now = datetime.now(tz=UTC)
        bronze_return_id = f"POS-RET-{original_transaction_id}"

        for item in items:
            self._repo.add_transaction_item(
                transaction_id=return_txn_id,
                tenant_id=tenant_id,
                drug_code=item.drug_code,
                drug_name=item.drug_name,
                quantity=_to_decimal(item.quantity),
                unit_price=_to_decimal(item.unit_price),
                line_total=_to_decimal(item.line_total),
                discount=_to_decimal(item.discount),
                batch_number=item.batch_number,
                expiry_date=item.expiry_date,
                is_controlled=item.is_controlled,
                pharmacist_id=item.pharmacist_id,
            )

            # Positive delta = restock
            await self._inventory.record_movement(
                StockMovement(
                    drug_code=item.drug_code,
                    site_code=site_code,
                    quantity_delta=_to_decimal(item.quantity),
                    batch_number=item.batch_number,
                    reference_id=f"RET-{original_transaction_id}",
                    movement_type="return",
                ),
            )

            # Bronze row with is_return=True
            self._repo.insert_bronze_pos_transaction(
                tenant_id=tenant_id,
                transaction_id=bronze_return_id,
                transaction_date=now,
                site_code=site_code,
                register_id=str(original["terminal_id"]),
                cashier_id=staff_id,
                customer_id=original.get("customer_id"),
                drug_code=item.drug_code,
                batch_number=item.batch_number,
                quantity=_to_decimal(item.quantity),
                unit_price=_to_decimal(item.unit_price),
                discount=_to_decimal(item.discount),
                net_amount=_to_decimal(item.line_total),
                payment_method=str(original.get("payment_method") or "cash"),
                is_return=True,
            )

        self._repo.update_transaction_status(
            return_txn_id,
            status=TransactionStatus.returned.value,
        )

        return_row = self._repo.create_return(
            tenant_id=tenant_id,
            original_transaction_id=original_transaction_id,
            staff_id=staff_id,
            reason=reason.value,
            refund_amount=refund_amount,
            refund_method=refund_method,
            return_transaction_id=return_txn_id,
            notes=notes,
        )

        log.info(
            "pos.return.processed",
            return_id=return_row["id"],
            original_txn_id=original_transaction_id,
            refund_amount=str(refund_amount),
            refund_method=refund_method,
        )
        return ReturnResponse.model_validate(return_row)

    def get_return(self, return_id: int) -> ReturnDetailResponse | None:
        """Return the full detail of a return record, including its items."""
        row = self._repo.get_return(return_id)
        if row is None:
            return None
        # Items come from the linked return transaction
        items: list[PosCartItem] = []
        if row.get("return_transaction_id"):
            item_rows = self._repo.get_transaction_items(int(row["return_transaction_id"]))
            items = [PosCartItem.model_validate(r) for r in item_rows]
        return ReturnDetailResponse.model_validate({**row, "items": items})

    def list_returns_for_transaction(
        self,
        original_transaction_id: int,
    ) -> list[ReturnResponse]:
        """List all return records linked to an original transaction."""
        rows = self._repo.list_returns_for_transaction(original_transaction_id)
        return [ReturnResponse.model_validate(r) for r in rows]

    def list_returns(
        self,
        tenant_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReturnResponse]:
        """List return records for the tenant, most recent first."""
        rows = self._repo.list_returns(tenant_id, limit=limit, offset=offset)
        return [ReturnResponse.model_validate(r) for r in rows]

    # ──────────────────────────────────────────────────────────────
    # Shifts (B6a)
    # ──────────────────────────────────────────────────────────────

    def start_shift(
        self,
        *,
        terminal_id: int,
        tenant_id: int,
        staff_id: str,
        opening_cash: Decimal = Decimal("0"),
    ) -> ShiftRecord:
        """Open a new cashier shift for a terminal.

        Raises :class:`PosError` if the terminal already has an open shift —
        the current shift must be closed before starting a new one.
        """
        existing = self._repo.get_current_shift(terminal_id)
        if existing is not None:
            raise PosError(
                message=(
                    f"Terminal {terminal_id} already has an open shift "
                    f"(shift_id={existing['id']}). Close it before starting a new one."
                ),
                detail=f"terminal_id={terminal_id} shift_id={existing['id']}",
            )

        now = datetime.now(tz=UTC)
        row = self._repo.create_shift_record(
            terminal_id=terminal_id,
            tenant_id=tenant_id,
            staff_id=staff_id,
            shift_date=now.date(),
            opened_at=now,
            opening_cash=opening_cash,
        )
        log.info("pos.shift.started", shift_id=row["id"], terminal_id=terminal_id)
        return ShiftRecord.model_validate(row)

    def close_shift(
        self,
        *,
        shift_id: int,
        closing_cash: Decimal,
    ) -> ShiftSummaryResponse:
        """Close a shift — computes expected cash and variance from drawer events.

        ``expected_cash`` = opening + cash_sales + floats_in - cash_refunds - pickups.
        ``variance`` = closing_cash - expected_cash (positive = over, negative = short).
        """
        from datapulse.pos.terminal import compute_expected_cash, compute_variance

        shift = self._repo.get_shift_by_id(shift_id)
        if shift is None:
            raise PosError(
                message=f"Shift {shift_id} not found",
                detail=f"shift_id={shift_id}",
            )
        if shift.get("closed_at") is not None:
            raise PosError(
                message=f"Shift {shift_id} is already closed",
                detail=f"shift_id={shift_id}",
            )

        # Aggregate cash drawer events since shift opened
        shift_opened = shift["opened_at"]
        cash_events = self._repo.get_cash_events(int(shift["terminal_id"]), limit=10000)
        events_in_shift = [e for e in cash_events if e["timestamp"] >= shift_opened]

        cash_sales = sum(
            (_to_decimal(e["amount"]) for e in events_in_shift if e["event_type"] == "sale"),
            start=Decimal("0"),
        )
        cash_refunds = sum(
            (_to_decimal(e["amount"]) for e in events_in_shift if e["event_type"] == "refund"),
            start=Decimal("0"),
        )
        floats_in = sum(
            (_to_decimal(e["amount"]) for e in events_in_shift if e["event_type"] == "float"),
            start=Decimal("0"),
        )
        pickups = sum(
            (_to_decimal(e["amount"]) for e in events_in_shift if e["event_type"] == "pickup"),
            start=Decimal("0"),
        )

        expected = compute_expected_cash(
            opening_cash=_to_decimal(shift["opening_cash"]),
            cash_sales=cash_sales,
            cash_refunds=cash_refunds,
            floats_in=floats_in,
            pickups=pickups,
        )
        variance = compute_variance(
            opening_cash=_to_decimal(shift["opening_cash"]),
            closing_cash=closing_cash,
            expected_cash=expected,
        )

        now = datetime.now(tz=UTC)
        updated = self._repo.update_shift_record(
            shift_id,
            closing_cash=closing_cash,
            expected_cash=expected,
            variance=variance,
            closed_at=now,
        )
        if updated is None:
            raise PosError(
                message=f"Failed to close shift {shift_id}",
                detail=f"shift_id={shift_id}",
            )

        summary_data = self._repo.get_shift_summary_data(
            int(shift["terminal_id"]),
            opened_at=shift_opened,
            closed_at=now,
        )

        log.info(
            "pos.shift.closed",
            shift_id=shift_id,
            closing_cash=str(closing_cash),
            expected_cash=str(expected),
            variance=str(variance),
        )
        return ShiftSummaryResponse.model_validate(
            {
                **updated,
                "transaction_count": summary_data.get("transaction_count", 0),
                "total_sales": summary_data.get("total_sales", Decimal("0")),
            }
        )

    def get_current_shift(self, terminal_id: int) -> ShiftRecord | None:
        """Return the currently open shift for a terminal (None if no open shift)."""
        row = self._repo.get_current_shift(terminal_id)
        return ShiftRecord.model_validate(row) if row else None

    def get_shift_by_id(self, shift_id: int) -> ShiftRecord | None:
        """Return a shift by its primary key (None if not found)."""
        row = self._repo.get_shift_by_id(shift_id)
        return ShiftRecord.model_validate(row) if row else None

    def list_shifts(
        self,
        tenant_id: int,
        *,
        terminal_id: int | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> list[ShiftRecord]:
        """List shift records for a tenant, most recent first."""
        rows = self._repo.list_shifts(
            tenant_id,
            terminal_id=terminal_id,
            limit=limit,
            offset=offset,
        )
        return [ShiftRecord.model_validate(r) for r in rows]

    # ──────────────────────────────────────────────────────────────
    # Cash drawer events (B6a)
    # ──────────────────────────────────────────────────────────────

    def record_cash_event(
        self,
        *,
        terminal_id: int,
        tenant_id: int,
        event_type: str,
        amount: Decimal,
        reference_id: str | None = None,
    ) -> CashDrawerEventResponse:
        """Record a mid-shift cash drawer event (float, pickup, refund, sale)."""
        row = self._repo.record_cash_event(
            terminal_id=terminal_id,
            tenant_id=tenant_id,
            event_type=event_type,
            amount=amount,
            reference_id=reference_id,
        )
        return CashDrawerEventResponse.model_validate(row)

    def get_cash_events(
        self,
        terminal_id: int,
        *,
        limit: int = 100,
    ) -> list[CashDrawerEventResponse]:
        """Return cash drawer events for a terminal, most recent first."""
        rows = self._repo.get_cash_events(terminal_id, limit=limit)
        return [CashDrawerEventResponse.model_validate(r) for r in rows]

    # ──────────────────────────────────────────────────────────────
    # Pharmacist PIN verification (B7)
    # ──────────────────────────────────────────────────────────────

    def verify_pharmacist_pin(
        self,
        *,
        pharmacist_id: str,
        credential: str,
        drug_code: str,
    ) -> PharmacistVerifyResponse:
        """Validate a pharmacist PIN and return a short-lived verification token.

        The token encodes ``pharmacist_id`` + ``drug_code`` + timestamp, signed
        with the application secret key. Pass it as ``pharmacist_id`` in a
        subsequent ``add_item`` call to authorise the controlled-substance
        dispensing without repeating the PIN check.

        Raises
        ------
        PharmacistVerificationRequiredError
            When the credential is wrong, the user has no PIN registered,
            or no ``PharmacistVerifier`` was injected (configuration error).
        """
        if self._verifier is None:
            raise PharmacistVerificationRequiredError(
                drug_code=drug_code,
                message="Pharmacist verification is not configured on this server.",
            )

        token = self._verifier.verify_and_issue(
            pharmacist_id=pharmacist_id,
            credential=credential,
            drug_code=drug_code,
        )

        expires_at = datetime.now(tz=UTC).replace(microsecond=0) + timedelta(
            seconds=TOKEN_TTL_SECONDS
        )

        return PharmacistVerifyResponse(
            token=token,
            pharmacist_id=pharmacist_id,
            drug_code=drug_code,
            expires_at=expires_at,
        )

"""Transactions + items + receipts table access.

Covers pos.transactions, pos.transaction_items, pos.receipts.

Extracted from the original 1,187-LOC ``repository.py`` facade (see #543).
Methods preserve their SQL text and parameter order byte-for-byte.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from datapulse.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

log = get_logger(__name__)


class TransactionRepoMixin:
    """Mixin for :class:`PosRepository` — requires ``self._session`` set by __init__."""

    _session: Session

    def create_transaction(
        self,
        *,
        tenant_id: int,
        terminal_id: int,
        staff_id: str,
        site_code: str,
        pharmacist_id: str | None = None,
        customer_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new draft transaction and return it."""
        row = (
            self._session.execute(
                text("""
                    INSERT INTO pos.transactions
                        (tenant_id, terminal_id, staff_id, site_code,
                         pharmacist_id, customer_id, status)
                    VALUES
                        (:tenant_id, :terminal_id, :staff_id, :site_code,
                         :pharmacist_id, :customer_id, 'draft')
                    RETURNING
                        id, tenant_id, terminal_id, staff_id, pharmacist_id,
                        customer_id, site_code, subtotal, discount_total,
                        tax_total, grand_total, payment_method, status,
                        receipt_number, created_at
                """),
                {
                    "tenant_id": tenant_id,
                    "terminal_id": terminal_id,
                    "staff_id": staff_id,
                    "site_code": site_code,
                    "pharmacist_id": pharmacist_id,
                    "customer_id": customer_id,
                },
            )
            .mappings()
            .one()
        )
        log.info("pos.transaction.created", txn_id=row["id"], tenant_id=tenant_id)
        return dict(row)

    def get_transaction(self, transaction_id: int) -> dict[str, Any] | None:
        """Return a transaction header by ID."""
        row = (
            self._session.execute(
                text("""
                    SELECT id, tenant_id, terminal_id, staff_id, pharmacist_id,
                           customer_id, site_code, subtotal, discount_total,
                           tax_total, grand_total, payment_method, status,
                           receipt_number, created_at
                    FROM   pos.transactions
                    WHERE  id = :txn_id
                """),
                {"txn_id": transaction_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def update_transaction_status(
        self,
        transaction_id: int,
        *,
        status: str,
        payment_method: str | None = None,
        receipt_number: str | None = None,
        subtotal: Decimal | None = None,
        discount_total: Decimal | None = None,
        tax_total: Decimal | None = None,
        grand_total: Decimal | None = None,
        pharmacist_id: str | None = None,
        customer_id: str | None = None,
        expected_status: str | None = None,
    ) -> dict[str, Any] | None:
        """Update transaction status and optionally recalculate financial totals.

        ``expected_status`` adds a compare-and-swap filter so the caller can
        atomically transition a row only if its current status matches. Returns
        ``None`` when the row does not exist *or* the expected-status check
        fails — both map to "race / wrong state" at the caller.
        """
        row = (
            self._session.execute(
                text("""
                    UPDATE pos.transactions
                    SET    status         = :status,
                           payment_method = COALESCE(:payment_method, payment_method),
                           receipt_number = COALESCE(:receipt_number, receipt_number),
                           subtotal       = COALESCE(:subtotal,       subtotal),
                           discount_total = COALESCE(:discount_total, discount_total),
                           tax_total      = COALESCE(:tax_total,      tax_total),
                           grand_total    = COALESCE(:grand_total,    grand_total),
                           pharmacist_id  = COALESCE(:pharmacist_id,  pharmacist_id),
                           customer_id    = COALESCE(:customer_id,    customer_id)
                    WHERE  id = :txn_id
                    AND    (:expected_status IS NULL OR status = :expected_status)
                    RETURNING
                        id, tenant_id, terminal_id, staff_id, pharmacist_id,
                        customer_id, site_code, subtotal, discount_total,
                        tax_total, grand_total, payment_method, status,
                        receipt_number, created_at
                """),
                {
                    "txn_id": transaction_id,
                    "status": status,
                    "payment_method": payment_method,
                    "receipt_number": receipt_number,
                    "subtotal": subtotal,
                    "discount_total": discount_total,
                    "tax_total": tax_total,
                    "grand_total": grand_total,
                    "pharmacist_id": pharmacist_id,
                    "customer_id": customer_id,
                    "expected_status": expected_status,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def list_transactions(
        self,
        tenant_id: int,
        *,
        terminal_id: int | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List transactions for a tenant with optional filters."""
        rows = (
            self._session.execute(
                text("""
                    SELECT id, tenant_id, terminal_id, staff_id, customer_id,
                           grand_total, payment_method, status, receipt_number, created_at
                    FROM   pos.transactions
                    WHERE  tenant_id   = :tenant_id
                    AND    (:terminal_id IS NULL OR terminal_id = :terminal_id)
                    AND    (:status     IS NULL OR status       = :status)
                    ORDER  BY created_at DESC
                    LIMIT  :limit OFFSET :offset
                """),
                {
                    "tenant_id": tenant_id,
                    "terminal_id": terminal_id,
                    "status": status,
                    "limit": limit,
                    "offset": offset,
                },
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def add_transaction_item(
        self,
        *,
        transaction_id: int,
        tenant_id: int,
        drug_code: str,
        drug_name: str,
        quantity: Decimal,
        unit_price: Decimal,
        line_total: Decimal,
        discount: Decimal = Decimal("0"),
        batch_number: str | None = None,
        expiry_date: date | None = None,
        is_controlled: bool = False,
        pharmacist_id: str | None = None,
        cost_per_unit: Decimal | None = None,
    ) -> dict[str, Any]:
        """Insert a single line item into a draft transaction."""
        row = (
            self._session.execute(
                text("""
                    INSERT INTO pos.transaction_items
                        (transaction_id, tenant_id, drug_code, drug_name,
                         quantity, unit_price, discount, line_total,
                         batch_number, expiry_date, is_controlled, pharmacist_id,
                         cost_per_unit)
                    VALUES
                        (:transaction_id, :tenant_id, :drug_code, :drug_name,
                         :quantity, :unit_price, :discount, :line_total,
                         :batch_number, :expiry_date, :is_controlled, :pharmacist_id,
                         :cost_per_unit)
                    RETURNING
                        id, transaction_id, tenant_id, drug_code, drug_name,
                        batch_number, expiry_date, quantity, unit_price,
                        discount, line_total, is_controlled, pharmacist_id,
                        cost_per_unit
                """),
                {
                    "transaction_id": transaction_id,
                    "tenant_id": tenant_id,
                    "drug_code": drug_code,
                    "drug_name": drug_name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": discount,
                    "line_total": line_total,
                    "batch_number": batch_number,
                    "expiry_date": expiry_date,
                    "is_controlled": is_controlled,
                    "pharmacist_id": pharmacist_id,
                    "cost_per_unit": cost_per_unit,
                },
            )
            .mappings()
            .one()
        )
        return dict(row)

    def get_transaction_item(self, item_id: int) -> dict[str, Any] | None:
        """Return one line item by ID."""
        row = (
            self._session.execute(
                text("""
                    SELECT id, transaction_id, tenant_id, drug_code, drug_name,
                           batch_number, expiry_date, quantity, unit_price,
                           discount, line_total, is_controlled, pharmacist_id,
                           cost_per_unit
                    FROM   pos.transaction_items
                    WHERE  id = :item_id
                """),
                {"item_id": item_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_transaction_for_update(self, transaction_id: int) -> dict[str, Any] | None:
        """Return a transaction header and lock it for the current DB transaction."""
        row = (
            self._session.execute(
                text("""
                    SELECT id, tenant_id, terminal_id, staff_id, pharmacist_id,
                           customer_id, site_code, subtotal, discount_total,
                           tax_total, grand_total, payment_method, status,
                           receipt_number, created_at
                    FROM   pos.transactions
                    WHERE  id = :txn_id
                    FOR UPDATE
                """),
                {"txn_id": transaction_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def update_item_quantity(
        self,
        item_id: int,
        *,
        quantity: Decimal,
        unit_price: Decimal | None = None,
        discount: Decimal | None = None,
        transaction_id: int | None = None,
        expected_status: str | None = None,
    ) -> dict[str, Any] | None:
        """Update quantity (and optionally unit_price + discount) for a draft line.

        ``line_total`` is recomputed in SQL from the resulting persisted
        ``unit_price`` and ``quantity`` so a quantity-only PATCH cannot
        zero an existing line by side-effect of an unsupplied override
        price (Codex P1).

        Pass ``unit_price=None`` for a pure-quantity update; the COALESCE
        keeps the existing column value. Same for ``discount``.

        Optional ``transaction_id`` / ``expected_status`` provide an atomic
        SQL-level guard so a PATCH cannot mutate a line whose parent
        transaction has left the draft state (Codex hardening).
        """
        row = (
            self._session.execute(
                text("""
                    UPDATE pos.transaction_items ti
                    SET    quantity   = :quantity,
                           unit_price = COALESCE(:unit_price, ti.unit_price),
                           discount   = COALESCE(:discount, ti.discount),
                           line_total = (COALESCE(:unit_price, ti.unit_price) * :quantity)
                                        - COALESCE(:discount, ti.discount, 0)
                    FROM   pos.transactions t
                    WHERE  ti.id = :item_id
                    AND    t.id  = ti.transaction_id
                    AND    (:transaction_id IS NULL OR ti.transaction_id = :transaction_id)
                    AND    (:expected_status IS NULL OR t.status = :expected_status)
                    RETURNING
                        ti.id, ti.transaction_id, ti.tenant_id, ti.drug_code,
                        ti.drug_name, ti.batch_number, ti.expiry_date,
                        ti.quantity, ti.unit_price, ti.discount, ti.line_total,
                        ti.is_controlled, ti.pharmacist_id
                """),
                {
                    "item_id": item_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": discount,
                    "transaction_id": transaction_id,
                    "expected_status": expected_status,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def remove_item(
        self,
        item_id: int,
        *,
        transaction_id: int | None = None,
        expected_status: str | None = None,
    ) -> bool:
        """Delete a single transaction item. Returns True if a row was deleted."""
        result = self._session.execute(
            text("""
                DELETE FROM pos.transaction_items ti
                USING pos.transactions t
                WHERE ti.id = :item_id
                AND   t.id  = ti.transaction_id
                AND   (:transaction_id IS NULL OR ti.transaction_id = :transaction_id)
                AND   (:expected_status IS NULL OR t.status = :expected_status)
            """),
            {
                "item_id": item_id,
                "transaction_id": transaction_id,
                "expected_status": expected_status,
            },
        )
        # SQLAlchemy ``Result`` for DML statements is a ``CursorResult`` exposing
        # ``rowcount``; the generic ``Result`` type doesn't, hence the ignore.
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]

    def get_transaction_items(self, transaction_id: int) -> list[dict[str, Any]]:
        """Return all line items for a transaction, ordered by insertion."""
        rows = (
            self._session.execute(
                text("""
                    SELECT id, transaction_id, tenant_id, drug_code, drug_name,
                           batch_number, expiry_date, quantity, unit_price,
                           discount, line_total, is_controlled, pharmacist_id,
                           cost_per_unit
                    FROM   pos.transaction_items
                    WHERE  transaction_id = :txn_id
                    ORDER  BY id ASC
                """),
                {"txn_id": transaction_id},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def save_receipt(
        self,
        *,
        transaction_id: int,
        tenant_id: int,
        fmt: str,
        content: bytes | None = None,
        file_path: str | None = None,
    ) -> dict[str, Any]:
        """Persist a receipt artifact (thermal bytes, PDF path, or email metadata)."""
        row = (
            self._session.execute(
                text("""
                    INSERT INTO pos.receipts
                        (transaction_id, tenant_id, format, content, file_path)
                    VALUES
                        (:transaction_id, :tenant_id, :fmt, :content, :file_path)
                    RETURNING id, transaction_id, tenant_id, format, file_path, generated_at
                """),
                {
                    "transaction_id": transaction_id,
                    "tenant_id": tenant_id,
                    "fmt": fmt,
                    "content": content,
                    "file_path": file_path,
                },
            )
            .mappings()
            .one()
        )
        return dict(row)

    def get_receipt(self, transaction_id: int, fmt: str) -> dict[str, Any] | None:
        """Retrieve the most-recent receipt of a given format for a transaction."""
        row = (
            self._session.execute(
                text("""
                    SELECT id, transaction_id, tenant_id, format, content,
                           file_path, generated_at
                    FROM   pos.receipts
                    WHERE  transaction_id = :txn_id
                    AND    format         = :fmt
                    ORDER  BY generated_at DESC
                    LIMIT  1
                """),
                {"txn_id": transaction_id, "fmt": fmt},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

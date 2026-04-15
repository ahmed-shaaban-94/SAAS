"""POS repository — raw SQL access for all pos.* tables.

Follows the Route->Service->Repository pattern established in analytics/.
All methods accept / return plain dicts (or None). The service layer is
responsible for constructing Pydantic models from these dicts.

Financial columns are stored as NUMERIC(18,4); Python receives them as Decimal.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


class PosRepository:
    """Raw SQL access for all POS tables in the ``pos`` and ``bronze`` schemas.

    Constructor takes a SQLAlchemy ``Session`` scoped to the current request.
    All queries are parameterised — no string interpolation.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ──────────────────────────────────────────────────────────────
    # Terminal sessions
    # ──────────────────────────────────────────────────────────────

    def create_terminal_session(
        self,
        *,
        tenant_id: int,
        site_code: str,
        staff_id: str,
        terminal_name: str = "Terminal-1",
        opening_cash: Decimal = Decimal("0"),
    ) -> dict[str, Any]:
        """Open a new POS terminal session and return the created row."""
        row = (
            self._session.execute(
                text("""
                    INSERT INTO pos.terminal_sessions
                        (tenant_id, site_code, staff_id, terminal_name, opening_cash, status)
                    VALUES
                        (:tenant_id, :site_code, :staff_id, :terminal_name, :opening_cash, 'open')
                    RETURNING
                        id, tenant_id, site_code, staff_id, terminal_name,
                        status, opened_at, closed_at, opening_cash, closing_cash
                """),
                {
                    "tenant_id": tenant_id,
                    "site_code": site_code,
                    "staff_id": staff_id,
                    "terminal_name": terminal_name,
                    "opening_cash": opening_cash,
                },
            )
            .mappings()
            .one()
        )
        log.info("pos.terminal_session.created", terminal_id=row["id"], tenant_id=tenant_id)
        return dict(row)

    def update_terminal_status(
        self,
        terminal_id: int,
        status: str,
        *,
        closing_cash: Decimal | None = None,
    ) -> dict[str, Any] | None:
        """Update terminal status (and optionally closing_cash). Returns updated row or None."""
        row = (
            self._session.execute(
                text("""
                    UPDATE pos.terminal_sessions
                    SET    status       = :status,
                           closing_cash = COALESCE(:closing_cash, closing_cash),
                           closed_at    = CASE WHEN :status = 'closed' THEN now() ELSE closed_at END
                    WHERE  id = :terminal_id
                    RETURNING
                        id, tenant_id, site_code, staff_id, terminal_name,
                        status, opened_at, closed_at, opening_cash, closing_cash
                """),
                {"terminal_id": terminal_id, "status": status, "closing_cash": closing_cash},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_terminal_session(self, terminal_id: int) -> dict[str, Any] | None:
        """Return a single terminal session by ID or None if not found."""
        row = (
            self._session.execute(
                text("""
                    SELECT id, tenant_id, site_code, staff_id, terminal_name,
                           status, opened_at, closed_at, opening_cash, closing_cash
                    FROM   pos.terminal_sessions
                    WHERE  id = :terminal_id
                """),
                {"terminal_id": terminal_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_active_terminals(self, tenant_id: int) -> list[dict[str, Any]]:
        """Return all non-closed terminal sessions for a tenant."""
        rows = (
            self._session.execute(
                text("""
                    SELECT id, tenant_id, site_code, staff_id, terminal_name,
                           status, opened_at, closed_at, opening_cash, closing_cash
                    FROM   pos.terminal_sessions
                    WHERE  tenant_id = :tenant_id
                    AND    status   != 'closed'
                    ORDER  BY opened_at DESC
                """),
                {"tenant_id": tenant_id},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

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
    ) -> dict[str, Any] | None:
        """Update transaction status and optionally recalculate financial totals."""
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

    # ──────────────────────────────────────────────────────────────
    # Transaction items
    # ──────────────────────────────────────────────────────────────

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
    ) -> dict[str, Any]:
        """Insert a single line item into a draft transaction."""
        row = (
            self._session.execute(
                text("""
                    INSERT INTO pos.transaction_items
                        (transaction_id, tenant_id, drug_code, drug_name,
                         quantity, unit_price, discount, line_total,
                         batch_number, expiry_date, is_controlled, pharmacist_id)
                    VALUES
                        (:transaction_id, :tenant_id, :drug_code, :drug_name,
                         :quantity, :unit_price, :discount, :line_total,
                         :batch_number, :expiry_date, :is_controlled, :pharmacist_id)
                    RETURNING
                        id, transaction_id, tenant_id, drug_code, drug_name,
                        batch_number, expiry_date, quantity, unit_price,
                        discount, line_total, is_controlled, pharmacist_id
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
                },
            )
            .mappings()
            .one()
        )
        return dict(row)

    def update_item_quantity(
        self,
        item_id: int,
        *,
        quantity: Decimal,
        line_total: Decimal,
        discount: Decimal | None = None,
    ) -> dict[str, Any] | None:
        """Update quantity and recalculate line_total for an existing item."""
        row = (
            self._session.execute(
                text("""
                    UPDATE pos.transaction_items
                    SET    quantity   = :quantity,
                           line_total = :line_total,
                           discount   = COALESCE(:discount, discount)
                    WHERE  id = :item_id
                    RETURNING
                        id, transaction_id, drug_code, quantity, unit_price,
                        discount, line_total, is_controlled
                """),
                {
                    "item_id": item_id,
                    "quantity": quantity,
                    "line_total": line_total,
                    "discount": discount,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def remove_item(self, item_id: int) -> bool:
        """Delete a single transaction item. Returns True if a row was deleted."""
        result = self._session.execute(
            text("DELETE FROM pos.transaction_items WHERE id = :item_id"),
            {"item_id": item_id},
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
                           discount, line_total, is_controlled, pharmacist_id
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

    # ──────────────────────────────────────────────────────────────
    # Receipts
    # ──────────────────────────────────────────────────────────────

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

    # ──────────────────────────────────────────────────────────────
    # Shift records
    # ──────────────────────────────────────────────────────────────

    def create_shift_record(
        self,
        *,
        terminal_id: int,
        tenant_id: int,
        staff_id: str,
        shift_date: date,
        opened_at: datetime,
        opening_cash: Decimal,
    ) -> dict[str, Any]:
        """Open a new shift record for a terminal."""
        row = (
            self._session.execute(
                text("""
                    INSERT INTO pos.shift_records
                        (terminal_id, tenant_id, staff_id, shift_date,
                         opened_at, opening_cash)
                    VALUES
                        (:terminal_id, :tenant_id, :staff_id, :shift_date,
                         :opened_at, :opening_cash)
                    RETURNING
                        id, terminal_id, tenant_id, staff_id, shift_date,
                        opened_at, closed_at, opening_cash, closing_cash,
                        expected_cash, variance
                """),
                {
                    "terminal_id": terminal_id,
                    "tenant_id": tenant_id,
                    "staff_id": staff_id,
                    "shift_date": shift_date,
                    "opened_at": opened_at,
                    "opening_cash": opening_cash,
                },
            )
            .mappings()
            .one()
        )
        log.info("pos.shift.created", shift_id=row["id"], terminal_id=terminal_id)
        return dict(row)

    def update_shift_record(
        self,
        shift_id: int,
        *,
        closing_cash: Decimal | None = None,
        expected_cash: Decimal | None = None,
        variance: Decimal | None = None,
        closed_at: datetime | None = None,
    ) -> dict[str, Any] | None:
        """Update closing values for a shift."""
        row = (
            self._session.execute(
                text("""
                    UPDATE pos.shift_records
                    SET    closing_cash  = COALESCE(:closing_cash,  closing_cash),
                           expected_cash = COALESCE(:expected_cash, expected_cash),
                           variance      = COALESCE(:variance,      variance),
                           closed_at     = COALESCE(:closed_at,     closed_at)
                    WHERE  id = :shift_id
                    RETURNING
                        id, terminal_id, tenant_id, staff_id, shift_date,
                        opened_at, closed_at, opening_cash, closing_cash,
                        expected_cash, variance
                """),
                {
                    "shift_id": shift_id,
                    "closing_cash": closing_cash,
                    "expected_cash": expected_cash,
                    "variance": variance,
                    "closed_at": closed_at,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_current_shift(self, terminal_id: int) -> dict[str, Any] | None:
        """Return the currently open (unclosed) shift for a terminal."""
        row = (
            self._session.execute(
                text("""
                    SELECT id, terminal_id, tenant_id, staff_id, shift_date,
                           opened_at, closed_at, opening_cash, closing_cash,
                           expected_cash, variance
                    FROM   pos.shift_records
                    WHERE  terminal_id = :terminal_id
                    AND    closed_at   IS NULL
                    ORDER  BY opened_at DESC
                    LIMIT  1
                """),
                {"terminal_id": terminal_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def list_shifts(
        self,
        tenant_id: int,
        *,
        terminal_id: int | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List shift records for a tenant, most recent first."""
        rows = (
            self._session.execute(
                text("""
                    SELECT id, terminal_id, tenant_id, staff_id, shift_date,
                           opened_at, closed_at, opening_cash, closing_cash,
                           expected_cash, variance
                    FROM   pos.shift_records
                    WHERE  tenant_id  = :tenant_id
                    AND    (:terminal_id IS NULL OR terminal_id = :terminal_id)
                    ORDER  BY opened_at DESC
                    LIMIT  :limit OFFSET :offset
                """),
                {
                    "tenant_id": tenant_id,
                    "terminal_id": terminal_id,
                    "limit": limit,
                    "offset": offset,
                },
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    # ──────────────────────────────────────────────────────────────
    # Cash drawer events
    # ──────────────────────────────────────────────────────────────

    def record_cash_event(
        self,
        *,
        terminal_id: int,
        tenant_id: int,
        event_type: str,
        amount: Decimal,
        reference_id: str | None = None,
    ) -> dict[str, Any]:
        """Append an immutable cash drawer event."""
        row = (
            self._session.execute(
                text("""
                    INSERT INTO pos.cash_drawer_events
                        (terminal_id, tenant_id, event_type, amount, reference_id)
                    VALUES
                        (:terminal_id, :tenant_id, :event_type, :amount, :reference_id)
                    RETURNING id, terminal_id, tenant_id, event_type, amount,
                              reference_id, timestamp
                """),
                {
                    "terminal_id": terminal_id,
                    "tenant_id": tenant_id,
                    "event_type": event_type,
                    "amount": amount,
                    "reference_id": reference_id,
                },
            )
            .mappings()
            .one()
        )
        return dict(row)

    def get_cash_events(
        self,
        terminal_id: int,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return cash drawer events for a terminal, most recent first."""
        rows = (
            self._session.execute(
                text("""
                    SELECT id, terminal_id, tenant_id, event_type, amount,
                           reference_id, timestamp
                    FROM   pos.cash_drawer_events
                    WHERE  terminal_id = :terminal_id
                    ORDER  BY timestamp DESC
                    LIMIT  :limit
                """),
                {"terminal_id": terminal_id, "limit": limit},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    # ──────────────────────────────────────────────────────────────
    # Void log
    # ──────────────────────────────────────────────────────────────

    def create_void_log(
        self,
        *,
        transaction_id: int,
        tenant_id: int,
        voided_by: str,
        reason: str,
    ) -> dict[str, Any]:
        """Append a void audit record for a transaction."""
        row = (
            self._session.execute(
                text("""
                    INSERT INTO pos.void_log
                        (transaction_id, tenant_id, voided_by, reason)
                    VALUES
                        (:transaction_id, :tenant_id, :voided_by, :reason)
                    RETURNING id, transaction_id, tenant_id, voided_by, reason, voided_at
                """),
                {
                    "transaction_id": transaction_id,
                    "tenant_id": tenant_id,
                    "voided_by": voided_by,
                    "reason": reason,
                },
            )
            .mappings()
            .one()
        )
        log.info(
            "pos.void.created",
            void_id=row["id"],
            transaction_id=transaction_id,
            voided_by=voided_by,
        )
        return dict(row)

    def get_void_log(self, transaction_id: int) -> dict[str, Any] | None:
        """Return the void record for a transaction (at most one per transaction)."""
        row = (
            self._session.execute(
                text("""
                    SELECT id, transaction_id, tenant_id, voided_by, reason, voided_at
                    FROM   pos.void_log
                    WHERE  transaction_id = :txn_id
                    LIMIT  1
                """),
                {"txn_id": transaction_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    # ──────────────────────────────────────────────────────────────
    # Returns
    # ──────────────────────────────────────────────────────────────

    def create_return(
        self,
        *,
        tenant_id: int,
        original_transaction_id: int,
        staff_id: str,
        reason: str,
        refund_amount: Decimal,
        refund_method: str,
        return_transaction_id: int | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Record a drug return, optionally linking to a return transaction."""
        row = (
            self._session.execute(
                text("""
                    INSERT INTO pos.returns
                        (tenant_id, original_transaction_id, return_transaction_id,
                         staff_id, reason, refund_amount, refund_method, notes)
                    VALUES
                        (:tenant_id, :original_transaction_id, :return_transaction_id,
                         :staff_id, :reason, :refund_amount, :refund_method, :notes)
                    RETURNING
                        id, tenant_id, original_transaction_id, return_transaction_id,
                        staff_id, reason, refund_amount, refund_method, notes, created_at
                """),
                {
                    "tenant_id": tenant_id,
                    "original_transaction_id": original_transaction_id,
                    "return_transaction_id": return_transaction_id,
                    "staff_id": staff_id,
                    "reason": reason,
                    "refund_amount": refund_amount,
                    "refund_method": refund_method,
                    "notes": notes,
                },
            )
            .mappings()
            .one()
        )
        log.info(
            "pos.return.created",
            return_id=row["id"],
            original_txn_id=original_transaction_id,
            tenant_id=tenant_id,
        )
        return dict(row)

    def get_return(self, return_id: int) -> dict[str, Any] | None:
        """Return a single return record by ID."""
        row = (
            self._session.execute(
                text("""
                    SELECT id, tenant_id, original_transaction_id, return_transaction_id,
                           staff_id, reason, refund_amount, refund_method, notes, created_at
                    FROM   pos.returns
                    WHERE  id = :return_id
                """),
                {"return_id": return_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def list_returns_for_transaction(self, original_transaction_id: int) -> list[dict[str, Any]]:
        """Return all return records linked to an original transaction."""
        rows = (
            self._session.execute(
                text("""
                    SELECT id, tenant_id, original_transaction_id, return_transaction_id,
                           staff_id, reason, refund_amount, refund_method, notes, created_at
                    FROM   pos.returns
                    WHERE  original_transaction_id = :original_txn_id
                    ORDER  BY created_at ASC
                """),
                {"original_txn_id": original_transaction_id},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    # ──────────────────────────────────────────────────────────────
    # Bronze write
    # ──────────────────────────────────────────────────────────────

    # ──────────────────────────────────────────────────────────────
    # Product search (dim_product + latest unit price from fct_sales)
    # ──────────────────────────────────────────────────────────────

    def search_dim_products(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search ``public_marts.dim_product`` by drug_code / drug_name / drug_brand.

        Tenant isolation is enforced by RLS via ``SET LOCAL app.tenant_id``.
        ``unit_price`` is the most-recent unit_price from ``public_marts.fct_sales``
        (falls back to 0 when the drug has never been sold).
        """
        pattern = f"%{query}%"
        rows = (
            self._session.execute(
                text("""
                    SELECT
                        p.drug_code,
                        p.drug_name,
                        p.drug_brand,
                        p.drug_cluster,
                        p.drug_category,
                        COALESCE(
                            (
                                SELECT f.unit_price
                                FROM   public_marts.fct_sales f
                                WHERE  f.tenant_id = p.tenant_id
                                AND    f.drug_code = p.drug_code
                                ORDER  BY f.invoice_date DESC
                                LIMIT  1
                            ),
                            0
                        ) AS unit_price
                    FROM   public_marts.dim_product p
                    WHERE  (
                           p.drug_name  ILIKE :pattern
                        OR p.drug_code  ILIKE :pattern
                        OR p.drug_brand ILIKE :pattern
                    )
                    ORDER  BY p.drug_name
                    LIMIT  :limit
                """),
                {"pattern": pattern, "limit": limit},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_product_by_code(self, drug_code: str) -> dict[str, Any] | None:
        """Return a single product by ``drug_code`` with its most-recent unit price."""
        row = (
            self._session.execute(
                text("""
                    SELECT
                        p.drug_code,
                        p.drug_name,
                        p.drug_brand,
                        p.drug_cluster,
                        p.drug_category,
                        COALESCE(
                            (
                                SELECT f.unit_price
                                FROM   public_marts.fct_sales f
                                WHERE  f.tenant_id = p.tenant_id
                                AND    f.drug_code = p.drug_code
                                ORDER  BY f.invoice_date DESC
                                LIMIT  1
                            ),
                            0
                        ) AS unit_price
                    FROM   public_marts.dim_product p
                    WHERE  p.drug_code = :drug_code
                    LIMIT  1
                """),
                {"drug_code": drug_code},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def insert_bronze_pos_transaction(
        self,
        *,
        tenant_id: int,
        transaction_id: str,
        transaction_date: datetime,
        site_code: str,
        register_id: str | None,
        cashier_id: str,
        customer_id: str | None,
        drug_code: str,
        batch_number: str | None,
        quantity: Decimal,
        unit_price: Decimal,
        net_amount: Decimal,
        payment_method: str,
        discount: Decimal = Decimal("0"),
        insurance_no: str | None = None,
        is_return: bool = False,
        pharmacist_id: str | None = None,
    ) -> dict[str, Any]:
        """Write one line to bronze.pos_transactions for pipeline ingestion.

        The ``transaction_id`` must be prefixed with ``'POS-'`` by the caller
        (service layer) to prevent collision with ERP rows in fct_sales.
        (C3 fix from adversarial review.)
        """
        row = (
            self._session.execute(
                text("""
                    INSERT INTO bronze.pos_transactions
                        (tenant_id, source_type, transaction_id, transaction_date,
                         site_code, register_id, cashier_id, customer_id,
                         drug_code, batch_number, quantity, unit_price,
                         discount, net_amount, payment_method,
                         insurance_no, is_return, pharmacist_id)
                    VALUES
                        (:tenant_id, 'pos_api', :transaction_id, :transaction_date,
                         :site_code, :register_id, :cashier_id, :customer_id,
                         :drug_code, :batch_number, :quantity, :unit_price,
                         :discount, :net_amount, :payment_method,
                         :insurance_no, :is_return, :pharmacist_id)
                    ON CONFLICT (tenant_id, transaction_id, drug_code) DO NOTHING
                    RETURNING id, transaction_id, drug_code, net_amount, loaded_at
                """),
                {
                    "tenant_id": tenant_id,
                    "transaction_id": transaction_id,
                    "transaction_date": transaction_date,
                    "site_code": site_code,
                    "register_id": register_id,
                    "cashier_id": cashier_id,
                    "customer_id": customer_id,
                    "drug_code": drug_code,
                    "batch_number": batch_number,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": discount,
                    "net_amount": net_amount,
                    "payment_method": payment_method,
                    "insurance_no": insurance_no,
                    "is_return": is_return,
                    "pharmacist_id": pharmacist_id,
                },
            )
            .mappings()
            .first()
        )
        # ON CONFLICT DO NOTHING returns no row on duplicate — that's intentional
        return dict(row) if row else {}

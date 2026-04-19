"""Atomic POS commit — ``POST /pos/transactions/commit``.

Inserts the transaction header + all line items + marks ``commit_confirmed_at``
in one SQL transaction. Designed for offline queue replay so a retried push
idempotently lands a single atomic financial write rather than the legacy
3-step draft → items → checkout flow.

When ``payload.voucher_code`` is provided, the voucher is atomically
redeemed inside the same transaction via ``SELECT ... FOR UPDATE``:

* The voucher discount is added to ``discount_total`` before computing the
  effective ``grand_total`` (so cash sufficiency is checked against the
  post-voucher total).
* ``lock_and_redeem`` sets ``redeemed_txn_id`` to the new transaction id and
  increments ``uses``; if that was the last allowed use the voucher moves to
  ``status='redeemed'``.
* Any voucher validation failure raises ``HTTPException(400)`` with a
  ``voucher_*`` detail string, rolling back the entire commit.

Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §3.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.pos.models import CommitRequest, CommitResponse
from datapulse.pos.voucher_repository import VoucherRepository
from datapulse.pos.voucher_service import VoucherService


def _next_receipt_number(session: Session, tenant_id: int) -> str:
    """Generate a receipt number of the form ``R-YYYYMMDD-NNNNNN`` per-tenant per-day."""
    now = datetime.now(UTC)
    seq = (
        session.execute(
            text(
                """SELECT count(*) + 1 FROM pos.transactions
                    WHERE tenant_id = :tid
                      AND created_at >= date_trunc('day', now())"""
            ),
            {"tid": tenant_id},
        ).scalar()
        or 1
    )
    return f"R-{now.strftime('%Y%m%d')}-{int(seq):06d}"


def atomic_commit(
    session: Session,
    *,
    tenant_id: int,
    payload: CommitRequest,
) -> CommitResponse:
    """Insert the transaction + items + set ``commit_confirmed_at`` atomically.

    Raises ``HTTPException(400)`` if a cash payment tenders less than the
    effective grand total, or if a supplied voucher code cannot be redeemed.
    """
    # ------------------------------------------------------------------
    # Voucher pre-flight — read without locking. We re-select with
    # FOR UPDATE inside lock_and_redeem once we have a transaction_id.
    # ------------------------------------------------------------------
    voucher_repo = VoucherRepository(session) if payload.voucher_code else None
    voucher_discount = Decimal("0")
    if payload.voucher_code:
        assert voucher_repo is not None  # for type checkers
        preview = voucher_repo.get_by_code(tenant_id, payload.voucher_code)
        if preview is None:
            raise HTTPException(status_code=400, detail="voucher_not_found")
        voucher_discount = VoucherService.compute_discount(
            preview.discount_type,
            preview.value,
            Decimal(str(payload.subtotal)),
        )

    # Apply voucher discount on top of the client-declared discount_total.
    base_discount = Decimal(str(payload.discount_total))
    effective_discount = base_discount + voucher_discount
    effective_grand = (
        Decimal(str(payload.subtotal)) - effective_discount + Decimal(str(payload.tax_total))
    )
    if effective_grand < Decimal("0"):
        effective_grand = Decimal("0")

    if payload.payment_method.value == "cash":
        tendered = payload.cash_tendered or Decimal("0")
        if tendered < effective_grand:
            raise HTTPException(status_code=400, detail="cash_tendered < grand_total")
        change_due = tendered - effective_grand
    else:
        change_due = Decimal("0")

    receipt = _next_receipt_number(session, tenant_id)
    now = datetime.now(UTC)

    txn_row = session.execute(
        text(
            """
            INSERT INTO pos.transactions
                (tenant_id, terminal_id, staff_id, customer_id, site_code,
                 subtotal, discount_total, tax_total, grand_total,
                 payment_method, status, receipt_number,
                 shift_id, created_at, commit_confirmed_at)
            VALUES
                (:tid, :term, :staff, :cust, :site,
                 :sub, :disc, :tax, :grand,
                 :pm, 'completed', :rec, :shift, :now, :now)
            RETURNING id
            """
        ),
        {
            "tid": tenant_id,
            "term": payload.terminal_id,
            "staff": payload.staff_id,
            "cust": payload.customer_id,
            "site": payload.site_code,
            "sub": payload.subtotal,
            "disc": effective_discount,
            "tax": payload.tax_total,
            "grand": effective_grand,
            "pm": payload.payment_method.value,
            "rec": receipt,
            "shift": payload.shift_id,
            "now": now,
        },
    ).first()
    if txn_row is None:  # pragma: no cover — INSERT RETURNING always yields a row
        raise HTTPException(status_code=500, detail="commit_insert_no_rowid")
    transaction_id = int(txn_row[0])

    for item in payload.items:
        session.execute(
            text(
                """
                INSERT INTO pos.transaction_items
                    (tenant_id, transaction_id, drug_code, drug_name,
                     batch_number, expiry_date, quantity, unit_price,
                     discount, line_total, is_controlled, pharmacist_id)
                VALUES
                    (:tid, :txn, :dc, :dn, :bn, :exp, :qty, :up, :disc, :lt, :ic, :ph)
                """
            ),
            {
                "tid": tenant_id,
                "txn": transaction_id,
                "dc": item.drug_code,
                "dn": item.drug_name,
                "bn": item.batch_number,
                "exp": item.expiry_date,
                "qty": item.quantity,
                "up": item.unit_price,
                "disc": item.discount,
                "lt": item.line_total,
                "ic": item.is_controlled,
                "ph": item.pharmacist_id,
            },
        )

    # ------------------------------------------------------------------
    # Redeem voucher now that we have a transaction_id. Any validation
    # failure here raises HTTPException(400) which the FastAPI handler
    # turns into a rollback of the entire session.
    # ------------------------------------------------------------------
    if payload.voucher_code:
        assert voucher_repo is not None
        voucher_repo.lock_and_redeem(
            tenant_id,
            payload.voucher_code,
            transaction_id,
            now,
            cart_subtotal=Decimal(str(payload.subtotal)),
        )

    return CommitResponse(
        transaction_id=transaction_id,
        receipt_number=receipt,
        commit_confirmed_at=now,
        change_due=change_due,
        voucher_discount=voucher_discount,
    )

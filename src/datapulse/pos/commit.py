"""Atomic POS commit — ``POST /pos/transactions/commit``.

Inserts the transaction header + all line items + marks ``commit_confirmed_at``
in one SQL transaction. Designed for offline queue replay so a retried push
idempotently lands a single atomic financial write rather than the legacy
3-step draft → items → checkout flow.

Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §3.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.pos.models import CommitRequest, CommitResponse


def _next_receipt_number(session: Session, tenant_id: int) -> str:
    """Generate a receipt number of the form ``R-YYYYMMDD-NNNNNN`` per-tenant per-day."""
    now = datetime.now(timezone.utc)
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
    grand total.
    """
    if payload.payment_method.value == "cash":
        tendered = payload.cash_tendered or Decimal("0")
        if tendered < payload.grand_total:
            raise HTTPException(status_code=400, detail="cash_tendered < grand_total")
        change_due = tendered - payload.grand_total
    else:
        change_due = Decimal("0")

    receipt = _next_receipt_number(session, tenant_id)
    now = datetime.now(timezone.utc)

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
            "disc": payload.discount_total,
            "tax": payload.tax_total,
            "grand": payload.grand_total,
            "pm": payload.payment_method.value,
            "rec": receipt,
            "shift": payload.shift_id,
            "now": now,
        },
    ).first()
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

    return CommitResponse(
        transaction_id=transaction_id,
        receipt_number=receipt,
        commit_confirmed_at=now,
        change_due=change_due,
    )

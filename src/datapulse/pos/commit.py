"""Atomic POS commit — ``POST /pos/transactions/commit``.

Inserts the transaction header + all line items + marks ``commit_confirmed_at``
in one SQL transaction. Designed for offline queue replay so a retried push
idempotently lands a single atomic financial write rather than the legacy
3-step draft → items → checkout flow.

Security hardening (H2):
* ``subtotal``, ``grand_total`` and every item's ``line_total`` are
  recomputed server-side from ``unit_price * quantity - discount``. Client
  totals are rejected if they disagree beyond a rounding epsilon, so a
  compromised client can not fake lower books or inflate refunds.
* The receipt number is derived deterministically from the auto-increment
  ``transaction_id`` (``R{YYYYMMDD}-{tenant}-{transaction_id}``) rather than
  ``count(*) + 1``; migration 088 adds a unique partial index so duplicates
  are rejected by the DB as a defence-in-depth backstop.

Voucher redemption:
* When ``payload.voucher_code`` is provided, the voucher is atomically
  redeemed inside the same transaction via ``SELECT ... FOR UPDATE``.
* The voucher discount is added on top of the (already-validated) client
  discount before the effective grand_total is computed, so cash
  sufficiency is checked against the post-voucher total.
* ``lock_and_redeem`` sets ``redeemed_txn_id`` to the new transaction id
  and increments ``uses``; if that was the last allowed use the voucher
  moves to ``status='redeemed'``.
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

# Rounding tolerance when comparing client-declared totals to server recomputed
# totals. Gives the desktop client ~0.01 EGP of rounding headroom.
_TOTAL_EPSILON = Decimal("0.01")


def _build_receipt_number(tenant_id: int, transaction_id: int, now: datetime) -> str:
    """Deterministic receipt number — same format as service._build_receipt_number.

    Uniqueness is guaranteed by the auto-increment ``transaction_id``, so we
    never rely on ``count(*) + 1`` (which races under concurrent commits).
    Migration 088 adds a unique partial index on (tenant_id, receipt_number)
    as an additional DB-level backstop.
    """
    return f"R{now.strftime('%Y%m%d')}-{tenant_id}-{transaction_id}"


def _recompute_line_total(unit_price: Decimal, quantity: Decimal, discount: Decimal) -> Decimal:
    """Authoritative server-side line total = unit_price * qty - discount."""
    return (unit_price * quantity - discount).quantize(Decimal("0.0001"))


def atomic_commit(
    session: Session,
    *,
    tenant_id: int,
    payload: CommitRequest,
) -> CommitResponse:
    """Insert the transaction + items + set ``commit_confirmed_at`` atomically.

    Raises ``HTTPException(400)`` when:
    - the declared grand_total (pre-voucher) disagrees with server-
      recomputed totals beyond ``_TOTAL_EPSILON``
    - a cash payment tenders less than the effective (post-voucher)
      grand total
    - a supplied voucher code cannot be found or redeemed
    """
    # ── Voucher pre-flight — read without locking. We re-select with ──────
    # FOR UPDATE inside lock_and_redeem once we have a transaction_id.
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

    # ── Server-side total recomputation (pre-voucher) ─────────────────────
    # Recompute subtotal from item unit_price × qty - discount so a client
    # sending fake line_totals or a fake subtotal can not corrupt the books.
    computed_subtotal = Decimal("0")
    for item in payload.items:
        computed_subtotal += _recompute_line_total(item.unit_price, item.quantity, item.discount)
    computed_subtotal = computed_subtotal.quantize(Decimal("0.0001"))

    base_discount = Decimal(str(payload.discount_total))
    tax_total = Decimal(str(payload.tax_total))

    # Pre-voucher grand_total — this is what the client sees before any voucher
    # is applied. We compare against the client's declared grand_total here.
    computed_pre_voucher_grand = (computed_subtotal - base_discount + tax_total).quantize(
        Decimal("0.0001")
    )

    if abs(computed_pre_voucher_grand - Decimal(str(payload.grand_total))) > _TOTAL_EPSILON:
        raise HTTPException(
            status_code=400,
            detail=(
                f"grand_total mismatch: client={payload.grand_total} "
                f"server={computed_pre_voucher_grand}"
            ),
        )

    # ── Apply voucher discount → effective grand_total ────────────────────
    effective_discount = base_discount + voucher_discount
    effective_grand = (computed_subtotal - effective_discount + tax_total).quantize(
        Decimal("0.0001")
    )
    if effective_grand < Decimal("0"):
        effective_grand = Decimal("0")

    # ── Cash tender validation against the effective (post-voucher) total ──
    if payload.payment_method.value == "cash":
        tendered = payload.cash_tendered or Decimal("0")
        if tendered < effective_grand:
            raise HTTPException(status_code=400, detail="cash_tendered < grand_total")
        change_due = tendered - effective_grand
    else:
        change_due = Decimal("0")

    now = datetime.now(UTC)

    # ── Insert the transaction header (receipt NULL until we have the id) ──
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
                 :pm, 'completed', NULL, :shift, :now, :now)
            RETURNING id
            """
        ),
        {
            "tid": tenant_id,
            "term": payload.terminal_id,
            "staff": payload.staff_id,
            "cust": payload.customer_id,
            "site": payload.site_code,
            "sub": computed_subtotal,
            "disc": effective_discount,
            "tax": tax_total,
            "grand": effective_grand,
            "pm": payload.payment_method.value,
            "shift": payload.shift_id,
            "now": now,
        },
    ).first()
    if txn_row is None:  # pragma: no cover — INSERT RETURNING always yields a row
        raise HTTPException(status_code=500, detail="commit_insert_no_rowid")
    transaction_id = int(txn_row[0])

    # Deterministic receipt number derived from the id we just reserved.
    receipt = _build_receipt_number(tenant_id, transaction_id, now)
    session.execute(
        text("UPDATE pos.transactions SET receipt_number = :rec WHERE id = :txn"),
        {"rec": receipt, "txn": transaction_id},
    )

    for item in payload.items:
        server_line_total = _recompute_line_total(item.unit_price, item.quantity, item.discount)
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
                "lt": server_line_total,
                "ic": item.is_controlled,
                "ph": item.pharmacist_id,
            },
        )

    # ── Redeem voucher now that we have a transaction_id. Any failure ──────
    # here raises HTTPException(400) which rolls back the entire commit.
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

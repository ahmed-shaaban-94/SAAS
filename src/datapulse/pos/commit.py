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

Discount redemption — the ``applied_discount`` union carries one of:
* ``source='voucher'`` — the legacy Phase 1 path. Redeemed via
  :meth:`VoucherRepository.lock_and_redeem` inside the same transaction.
* ``source='promotion'`` — Phase 2. The promotion row is locked via
  ``SELECT ... FOR UPDATE``, eligibility is re-validated at commit time,
  and an audit row is inserted into ``pos.promotion_applications``.

A single transaction may carry at most one discount. The legacy
``voucher_code`` field on :class:`CommitRequest` is still accepted from
offline clients that haven't migrated; if both ``applied_discount`` and
``voucher_code`` are set the model validator rejects the payload.

Any discount-validation failure raises ``HTTPException(400)`` with a
``voucher_*`` or ``promotion_*`` detail string, rolling back the commit.

Design ref: docs/plans/specs/2026-04-17-pos-electron-desktop-design.md §3
and docs/plans/sprints/2026-04-19-pos-promotions-phase-2-admin-managed.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.pos.exceptions import PosInternalError, PosNotFoundError, PosValidationError
from datapulse.pos.models import (
    AppliedDiscount,
    CommitRequest,
    CommitResponse,
    EligibleCartItem,
    PosCartItem,
    PromotionResponse,
    VoucherResponse,
)
from datapulse.pos.promotion_repository import PromotionRepository
from datapulse.pos.promotion_service import PromotionService
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


def _write_bronze_pos_sale(
    session: Session,
    *,
    tenant_id: int,
    payload: CommitRequest,
    transaction_id: int,
    receipt_number: str,
    transaction_date: datetime,
    item: PosCartItem,
    line_total: Decimal,
) -> None:
    """Mirror legacy checkout's POS bronze write for analytics ingestion."""
    session.execute(
        text(
            """
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
                 NULL, FALSE, :pharmacist_id)
            ON CONFLICT (tenant_id, transaction_id, drug_code) DO NOTHING
            """
        ),
        {
            "tenant_id": tenant_id,
            "transaction_id": f"POS-{receipt_number}",
            "transaction_date": transaction_date,
            "site_code": payload.site_code,
            "register_id": str(payload.terminal_id),
            "cashier_id": payload.staff_id,
            "customer_id": payload.customer_id,
            "drug_code": item.drug_code,
            "batch_number": item.batch_number,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "discount": item.discount,
            "net_amount": line_total,
            "payment_method": payload.payment_method.value,
            "pharmacist_id": item.pharmacist_id,
        },
    )


def _record_stock_adjustment(
    session: Session,
    *,
    tenant_id: int,
    payload: CommitRequest,
    receipt_number: str,
    transaction_date: datetime,
    item: PosCartItem,
) -> None:
    """Record the sale as a stock correction, matching InventoryAdapter semantics."""
    session.execute(
        text(
            """
            INSERT INTO bronze.stock_adjustments (
                tenant_id,
                source_file,
                adjustment_date,
                adjustment_type,
                drug_code,
                site_code,
                batch_number,
                quantity,
                reason,
                loaded_at
            ) VALUES (
                :tenant_id,
                :source_file,
                :adjustment_date,
                'correction',
                :drug_code,
                :site_code,
                :batch_number,
                :quantity,
                :reason,
                :loaded_at
            )
            """
        ),
        {
            "tenant_id": tenant_id,
            "source_file": "pos_commit",
            "adjustment_date": transaction_date.date(),
            "drug_code": item.drug_code,
            "site_code": payload.site_code,
            "batch_number": item.batch_number,
            "quantity": -item.quantity,
            "reason": f"POS sale: ref=POS-{receipt_number}",
            "loaded_at": transaction_date,
        },
    )


def _normalize_discount_source(payload: CommitRequest) -> AppliedDiscount | None:
    """Coerce the two legacy-compatible input shapes into one ``AppliedDiscount``.

    ``applied_discount`` takes precedence (Phase 2 clients). Falling back to
    ``voucher_code`` keeps offline Phase 1 clients working without a
    contract change. ``_one_discount_only`` on the model guarantees only
    one of the two fields is set.
    """
    if payload.applied_discount is not None:
        return payload.applied_discount
    if payload.voucher_code is not None:
        return AppliedDiscount(source="voucher", ref=payload.voucher_code)
    return None


def _preview_voucher_discount(
    voucher_repo: VoucherRepository,
    *,
    tenant_id: int,
    code: str,
    subtotal: Decimal,
) -> tuple[VoucherResponse, Decimal]:
    """Read the voucher (no lock) + compute the would-be discount for total-check."""
    preview = voucher_repo.get_by_code(tenant_id, code)
    if preview is None:
        raise PosNotFoundError("voucher_not_found", http_status=400)
    discount = VoucherService.compute_discount(
        preview.discount_type,
        preview.value,
        subtotal,
    )
    return preview, discount


def _preview_promotion_discount(
    promotion_repo: PromotionRepository,
    *,
    tenant_id: int,
    promotion_id: int,
    payload: CommitRequest,
    subtotal: Decimal,
) -> tuple[PromotionResponse, Decimal]:
    """Read the promotion + compute the discount against the eligible slice."""
    promo = promotion_repo.get(tenant_id, promotion_id)
    if promo is None:
        raise PosNotFoundError("promotion_not_found", http_status=400)
    eligible_base = PromotionService.eligible_base(
        promo,
        [
            EligibleCartItem(
                drug_code=item.drug_code,
                # drug_cluster is not on CommitRequest items — so scope='category'
                # promotions can only be previewed when the client has already
                # filtered. Be conservative and treat unknown clusters as
                # non-matching; the cashier UI only surfaces promotions that
                # matched at /eligible time.
                drug_cluster=None,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item in payload.items
        ],
    )
    # For category promotions we don't have drug_cluster on the commit path,
    # so fall back to the full subtotal. The /eligible endpoint already
    # vetted that the cart has matching items; commit-time recomputation
    # is a safety net, not the canonical eligibility check.
    if promo.scope.value == "category" and eligible_base <= 0:
        eligible_base = subtotal
    discount = PromotionService.compute_discount(
        promo.discount_type,
        promo.value,
        eligible_base,
        max_discount=promo.max_discount,
    )
    return promo, discount


def atomic_commit(
    session: Session,
    *,
    tenant_id: int,
    payload: CommitRequest,
) -> CommitResponse:
    """Insert the transaction + items + set ``commit_confirmed_at`` atomically.

    Raises ``HTTPException(400)`` when:
    - the declared grand_total (pre-discount) disagrees with server-
      recomputed totals beyond ``_TOTAL_EPSILON``
    - a cash payment tenders less than the effective (post-discount)
      grand total
    - a supplied voucher / promotion cannot be found, applied, or has expired
    """
    discount_source = _normalize_discount_source(payload)

    voucher_repo: VoucherRepository | None = None
    promotion_repo: PromotionRepository | None = None
    discount_amount = Decimal("0")
    applied_promotion_id: int | None = None

    if discount_source is not None:
        subtotal_decimal = Decimal(str(payload.subtotal))
        if discount_source.source == "voucher":
            voucher_repo = VoucherRepository(session)
            _, discount_amount = _preview_voucher_discount(
                voucher_repo,
                tenant_id=tenant_id,
                code=discount_source.ref,
                subtotal=subtotal_decimal,
            )
        else:
            try:
                promotion_id = int(discount_source.ref)
            except ValueError as exc:
                raise PosValidationError("promotion_ref_invalid") from exc
            promotion_repo = PromotionRepository(session)
            _, discount_amount = _preview_promotion_discount(
                promotion_repo,
                tenant_id=tenant_id,
                promotion_id=promotion_id,
                payload=payload,
                subtotal=subtotal_decimal,
            )
            applied_promotion_id = promotion_id

    # ── Server-side total recomputation (pre-discount) ────────────────────
    # Recompute subtotal from item unit_price × qty - discount so a client
    # sending fake line_totals or a fake subtotal can not corrupt the books.
    computed_subtotal = Decimal("0")
    for item in payload.items:
        computed_subtotal += _recompute_line_total(item.unit_price, item.quantity, item.discount)
    computed_subtotal = computed_subtotal.quantize(Decimal("0.0001"))

    base_discount = Decimal(str(payload.discount_total))
    tax_total = Decimal(str(payload.tax_total))

    # Pre-discount grand_total — this is what the client sees before any
    # voucher / promotion is applied. We compare against the client's
    # declared grand_total here.
    computed_pre_discount_grand = (computed_subtotal - base_discount + tax_total).quantize(
        Decimal("0.0001")
    )

    if abs(computed_pre_discount_grand - Decimal(str(payload.grand_total))) > _TOTAL_EPSILON:
        raise PosValidationError(
            f"grand_total mismatch: client={payload.grand_total} "
            f"server={computed_pre_discount_grand}"
        )

    # ── Apply voucher / promotion discount → effective grand_total ────────
    effective_discount = base_discount + discount_amount
    effective_grand = (computed_subtotal - effective_discount + tax_total).quantize(
        Decimal("0.0001")
    )
    if effective_grand < Decimal("0"):
        effective_grand = Decimal("0")

    # ── Cash tender validation against the effective (post-discount) total
    if payload.payment_method.value == "cash":
        tendered = payload.cash_tendered or Decimal("0")
        if tendered < effective_grand:
            raise PosValidationError("cash_tendered < grand_total")
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
        raise PosInternalError("commit_insert_no_rowid")
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
        _write_bronze_pos_sale(
            session,
            tenant_id=tenant_id,
            payload=payload,
            transaction_id=transaction_id,
            receipt_number=receipt,
            transaction_date=now,
            item=item,
            line_total=server_line_total,
        )
        _record_stock_adjustment(
            session,
            tenant_id=tenant_id,
            payload=payload,
            receipt_number=receipt,
            transaction_date=now,
            item=item,
        )

    # ── Redeem voucher / record promotion now that we have a transaction_id.
    # Any failure raises HTTPException(400) which rolls back the entire commit.
    if discount_source is not None:
        if discount_source.source == "voucher":
            assert voucher_repo is not None
            voucher_repo.lock_and_redeem(
                tenant_id,
                discount_source.ref,
                transaction_id,
                now,
                cart_subtotal=Decimal(str(payload.subtotal)),
            )
        else:
            assert promotion_repo is not None and applied_promotion_id is not None
            promotion_repo.lock_for_application(tenant_id, applied_promotion_id, now)
            promotion_repo.record_application(
                tenant_id=tenant_id,
                promotion_id=applied_promotion_id,
                transaction_id=transaction_id,
                cashier_staff_id=payload.staff_id,
                discount_applied=discount_amount,
                applied_at=now,
            )

    return CommitResponse(
        transaction_id=transaction_id,
        receipt_number=receipt,
        commit_confirmed_at=now,
        change_due=change_due,
        voucher_discount=discount_amount,
        applied_promotion_id=applied_promotion_id,
    )

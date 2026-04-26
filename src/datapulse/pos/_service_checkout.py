"""Checkout mixin for :class:`PosService`.

Owns the full checkout orchestration: totals, voucher/promotion preview,
payment, compare-and-swap status update, post-CAS redemption, inventory
movements, bronze write, and receipt persistence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from datapulse.logging import get_logger
from datapulse.pos._service_helpers import build_receipt_number, to_decimal
from datapulse.pos.constants import TransactionStatus
from datapulse.pos.exceptions import PosError
from datapulse.pos.inventory_contract import StockMovement
from datapulse.pos.models import CheckoutRequest, CheckoutResponse
from datapulse.pos.payment import PaymentGateway, get_gateway
from datapulse.pos.promotion_service import PromotionService
from datapulse.pos.receipt import generate_pdf_receipt, generate_thermal_receipt
from datapulse.pos.voucher_service import VoucherService

if TYPE_CHECKING:
    from datapulse.pos.inventory_contract import InventoryServiceProtocol
    from datapulse.pos.promotion_repository import PromotionRepository
    from datapulse.pos.repository import PosRepository
    from datapulse.pos.voucher_repository import VoucherRepository

log = get_logger(__name__)


class CheckoutMixin:
    """Mixin providing the ``checkout`` orchestration method.

    Requires ``self._repo``, ``self._inventory``, ``self._voucher_repo``, and
    ``self._promotion_repo`` to be set by :meth:`PosService.__init__`.
    """

    _repo: PosRepository
    _inventory: InventoryServiceProtocol
    _voucher_repo: VoucherRepository | None
    _promotion_repo: PromotionRepository | None
    _card_gateway: PaymentGateway | None

    async def checkout(
        self,
        *,
        transaction_id: int,
        tenant_id: int,
        request: CheckoutRequest,
    ) -> CheckoutResponse:
        """Finalise a draft transaction: totals -> payment -> stock -> bronze.

        Payment processing is gateway-delegated (see :mod:`datapulse.pos.payment`).
        """
        header = self._repo.get_transaction(transaction_id, tenant_id=tenant_id)
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

        items = self._repo.get_transaction_items(transaction_id, tenant_id=tenant_id)
        if not items:
            raise PosError(
                message=f"Transaction {transaction_id} has no items to check out",
                detail=f"transaction_id={transaction_id}",
            )

        # ── Totals ──────────────────────────────────────────────────
        subtotal = sum(
            (to_decimal(i["line_total"]) for i in items),
            start=Decimal("0"),
        )
        discount_total = to_decimal(request.transaction_discount) + sum(
            (to_decimal(i.get("discount", 0)) for i in items),
            start=Decimal("0"),
        )
        tax_total = Decimal("0")  # Tax engine added in a later session
        grand_total = subtotal - to_decimal(request.transaction_discount) + tax_total

        # ── Cart-level discount preview (voucher OR promotion) ──────
        # Validation-only preview here; actual redemption fires after the
        # status CAS succeeds to avoid "redeemed but CAS failed" ghosts.
        voucher_discount = Decimal("0")
        voucher_code: str | None = None
        promotion_id: int | None = None
        promotion_applied = False
        voucher_applied = False

        # Normalise legacy voucher_code into the applied_discount shape.
        discount_source: str | None = None
        discount_ref: str | None = None
        if request.applied_discount is not None:
            discount_source = request.applied_discount.source
            discount_ref = request.applied_discount.ref
        elif request.voucher_code:
            discount_source = "voucher"
            discount_ref = request.voucher_code

        if discount_source == "voucher" and discount_ref and self._voucher_repo is not None:
            voucher_code = discount_ref
            voucher = self._voucher_repo.get_by_code(tenant_id, voucher_code)
            if voucher is None:
                raise PosError(
                    message=f"Voucher '{voucher_code}' not found",
                    detail="voucher_not_found",
                )
            voucher_discount = VoucherService.compute_discount(
                voucher.discount_type, to_decimal(voucher.value), subtotal
            )
            discount_total += voucher_discount
            grand_total -= voucher_discount
            voucher_applied = True
        elif discount_source == "promotion" and discount_ref and self._promotion_repo is not None:
            try:
                promotion_id = int(discount_ref)
            except ValueError as e:
                raise PosError(
                    message=f"Invalid promotion ref: {discount_ref!r}",
                    detail="promotion_ref_invalid",
                ) from e
            promo = self._promotion_repo.get(tenant_id, promotion_id)
            if promo is None:
                raise PosError(
                    message=f"Promotion {promotion_id} not found",
                    detail="promotion_not_found",
                )
            # Preview discount — scope='category' isn't resolvable here
            # because cart items lack drug_cluster on the draft rows; the
            # /eligible endpoint (which does have cluster) gates this UI,
            # so we fall back to subtotal as the eligible base. Items-scope
            # matches on drug_code.
            if promo.scope.value == "items":
                base = sum(
                    (
                        to_decimal(i["line_total"])
                        for i in items
                        if i["drug_code"] in promo.scope_items
                    ),
                    start=Decimal("0"),
                )
            else:
                base = subtotal
            if promo.min_purchase is not None and base < to_decimal(promo.min_purchase):
                raise PosError(
                    message="Cart does not meet the minimum purchase for this promotion",
                    detail="promotion_min_purchase_not_met",
                )
            voucher_discount = PromotionService.compute_discount(
                promo.discount_type,
                to_decimal(promo.value),
                base,
                max_discount=to_decimal(promo.max_discount) if promo.max_discount else None,
            )
            discount_total += voucher_discount
            grand_total -= voucher_discount
            promotion_applied = True

        grand_total = grand_total.quantize(Decimal("0.0001"))

        # ── Payment (B4: gateway delegation) ───────────────────────
        # Use the injected card gateway when present (Paymob, #738);
        # otherwise fall back to get_gateway() which returns CardGateway stub.
        _method = request.payment_method.value
        if _method == "card" and self._card_gateway is not None:
            gateway: PaymentGateway = self._card_gateway
        else:
            gateway = get_gateway(_method)
        payment_result = gateway.process_payment(
            grand_total,
            tendered=to_decimal(request.cash_tendered or 0),
            insurance_no=request.insurance_no,
        )
        payment_result.raise_if_failed()
        change_due = payment_result.change_due

        receipt_number = build_receipt_number(tenant_id, transaction_id)

        # Compare-and-swap: only claim the draft if nobody else has already
        # finalised it. Closes the race between the pre-check above and this
        # UPDATE — two concurrent /checkout calls against the same draft
        # will have exactly one succeed; the loser gets a PosError and no
        # inventory movements fire.
        updated = self._repo.update_transaction_status(
            transaction_id,
            tenant_id=tenant_id,
            status=TransactionStatus.completed.value,
            payment_method=request.payment_method.value,
            receipt_number=receipt_number,
            subtotal=subtotal.quantize(Decimal("0.0001")),
            discount_total=discount_total.quantize(Decimal("0.0001")),
            tax_total=tax_total,
            grand_total=grand_total,
            customer_id=request.customer_id,
            expected_status=TransactionStatus.draft.value,
        )
        if updated is None:
            raise PosError(
                message=(
                    f"Transaction {transaction_id} could not be finalised — "
                    "another request may have completed it first."
                ),
                detail=f"transaction_id={transaction_id} cas_failed=true",
            )

        # ── Voucher / promotion redemption (atomic, post-CAS) ───────
        # Race note: between preview and this call another commit path
        # could have taken the last use; lock_and_redeem catches that
        # via SELECT FOR UPDATE and raises HTTPException. Session rollback
        # on an unhandled raise will also revert the status CAS.
        now_utc = datetime.now(tz=UTC)
        if voucher_applied and self._voucher_repo is not None and voucher_code is not None:
            self._voucher_repo.lock_and_redeem(
                tenant_id=tenant_id,
                code=voucher_code,
                txn_id=transaction_id,
                now=now_utc,
            )
        if promotion_applied and self._promotion_repo is not None and promotion_id is not None:
            self._promotion_repo.lock_for_application(tenant_id, promotion_id, now_utc)
            self._promotion_repo.record_application(
                tenant_id=tenant_id,
                promotion_id=promotion_id,
                transaction_id=transaction_id,
                cashier_staff_id=str(header["staff_id"]),
                discount_applied=voucher_discount,
                applied_at=now_utc,
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
                    quantity_delta=-to_decimal(item["quantity"]),
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
                quantity=to_decimal(item["quantity"]),
                unit_price=to_decimal(item["unit_price"]),
                discount=to_decimal(item.get("discount", 0)),
                net_amount=to_decimal(item["line_total"]),
                payment_method=request.payment_method.value,
                insurance_no=request.insurance_no,
                is_return=False,
                pharmacist_id=item.get("pharmacist_id"),
            )

        # ── Receipt generation (B4) ────────────────────────────────
        payment_info = {
            "method": request.payment_method.value,
            "amount_charged": grand_total,
            "change_due": change_due,
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
            voucher_discount=voucher_discount,
            applied_promotion_id=promotion_id if promotion_applied else None,
        )

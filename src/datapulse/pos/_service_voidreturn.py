"""Void + return mixin for :class:`PosService`.

Owns the reverse-flow operations: void an entire completed transaction, or
process a partial (or full) return with per-line over-return checks and
refund recomputation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from datapulse.logging import get_logger
from datapulse.pos._service_helpers import to_decimal
from datapulse.pos.constants import ReturnReason, TransactionStatus
from datapulse.pos.exceptions import PosError
from datapulse.pos.inventory_contract import StockMovement
from datapulse.pos.models import (
    PosCartItem,
    ReturnDetailResponse,
    ReturnResponse,
    VoidResponse,
)

if TYPE_CHECKING:
    from datapulse.pos.inventory_contract import InventoryServiceProtocol
    from datapulse.pos.repository import PosRepository

log = get_logger(__name__)


class VoidReturnMixin:
    """Mixin providing void + return processing.

    Requires ``self._repo`` and ``self._inventory`` to be set by
    :meth:`PosService.__init__`.
    """

    _repo: PosRepository
    _inventory: InventoryServiceProtocol

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
                    quantity_delta=to_decimal(item["quantity"]),  # positive = restock
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

        Client-supplied items carry only ``(drug_code, batch_number, quantity)``
        as trusted input. Everything else — ``unit_price``, ``line_total``,
        ``discount`` — is recomputed from the original transaction so the
        refund amount can not be inflated. The sum of all prior returns plus
        this one must not exceed the originally-sold quantity per line,
        closing the double-refund path.

        Raises :class:`PosError` for not-found, wrong-state, empty items,
        non-matching lines, or quantity over-return.
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

        # ── Authoritative original lines, keyed by (drug_code, batch_number) ──
        original_items = self._repo.get_transaction_items(original_transaction_id)
        orig_index: dict[tuple[str, str], dict[str, Any]] = {
            (oi["drug_code"], oi.get("batch_number") or ""): oi for oi in original_items
        }

        # ── Sum of already-returned quantities per line ───────────────────────
        prior_returns = self._repo.get_returned_quantities_for_transaction(original_transaction_id)
        returned_index: dict[tuple[str, str], Decimal] = {
            (r["drug_code"], r.get("batch_number") or ""): to_decimal(r["returned_qty"])
            for r in prior_returns
        }

        # ── Validate each request line + accumulate same-request deltas ───────
        in_this_request: dict[tuple[str, str], Decimal] = {}
        for item in items:
            key = (item.drug_code, item.batch_number or "")
            if key not in orig_index:
                raise PosError(
                    message=(
                        f"Return item {item.drug_code!r} "
                        f"(batch {item.batch_number!r}) is not on the original transaction."
                    ),
                    detail=f"original_transaction_id={original_transaction_id}",
                )
            requested_cumulative = in_this_request.get(key, Decimal("0")) + to_decimal(
                item.quantity
            )
            already = returned_index.get(key, Decimal("0"))
            original_qty = to_decimal(orig_index[key]["quantity"])
            remaining = original_qty - already
            if requested_cumulative > remaining:
                raise PosError(
                    message=(
                        f"Return quantity {requested_cumulative} for drug "
                        f"{item.drug_code!r} exceeds returnable {remaining} "
                        f"(sold: {original_qty}, already returned: {already})."
                    ),
                    detail=(
                        f"original_transaction_id={original_transaction_id} "
                        f"drug_code={item.drug_code} batch_number={item.batch_number}"
                    ),
                )
            in_this_request[key] = requested_cumulative

        # ── Server-side refund computation ─────────────────────────────────────
        # Pro-rate the original line's discount by returned fraction so the
        # refund never exceeds what the customer actually paid for the units.
        def _compute_line(
            orig: dict[str, Any], return_qty: Decimal
        ) -> tuple[Decimal, Decimal, Decimal]:
            unit_price = to_decimal(orig["unit_price"])
            original_discount = to_decimal(orig.get("discount", 0))
            original_qty = to_decimal(orig["quantity"])
            if original_qty > 0:
                discount_portion = (original_discount * return_qty / original_qty).quantize(
                    Decimal("0.0001")
                )
            else:
                discount_portion = Decimal("0")
            line_total = (unit_price * return_qty - discount_portion).quantize(Decimal("0.0001"))
            return unit_price, line_total, discount_portion

        # ── Create the return transaction skeleton ─────────────────────────────
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
        refund_amount = Decimal("0")

        for item in items:
            key = (item.drug_code, item.batch_number or "")
            orig = orig_index[key]
            return_qty = to_decimal(item.quantity)
            unit_price, line_total, discount_portion = _compute_line(orig, return_qty)
            refund_amount += line_total

            self._repo.add_transaction_item(
                transaction_id=return_txn_id,
                tenant_id=tenant_id,
                drug_code=item.drug_code,
                drug_name=orig["drug_name"],
                quantity=return_qty,
                unit_price=unit_price,
                line_total=line_total,
                discount=discount_portion,
                batch_number=orig.get("batch_number"),
                expiry_date=orig.get("expiry_date"),
                is_controlled=bool(orig.get("is_controlled", False)),
                pharmacist_id=orig.get("pharmacist_id"),
            )

            await self._inventory.record_movement(
                StockMovement(
                    drug_code=item.drug_code,
                    site_code=site_code,
                    quantity_delta=return_qty,  # positive = restock
                    batch_number=orig.get("batch_number"),
                    reference_id=f"RET-{original_transaction_id}",
                    movement_type="return",
                ),
            )

            self._repo.insert_bronze_pos_transaction(
                tenant_id=tenant_id,
                transaction_id=bronze_return_id,
                transaction_date=now,
                site_code=site_code,
                register_id=str(original["terminal_id"]),
                cashier_id=staff_id,
                customer_id=original.get("customer_id"),
                drug_code=item.drug_code,
                batch_number=orig.get("batch_number"),
                quantity=return_qty,
                unit_price=unit_price,
                discount=discount_portion,
                net_amount=line_total,
                payment_method=str(original.get("payment_method") or "cash"),
                is_return=True,
            )

        refund_amount = refund_amount.quantize(Decimal("0.0001"))

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

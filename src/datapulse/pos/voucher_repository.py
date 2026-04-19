"""Voucher repository — raw SQL access for pos.vouchers.

Phase 1 of the POS discount system. Concurrency-safe redemption uses
``SELECT ... FOR UPDATE`` to prevent double-redemption when the same voucher
is submitted by two concurrent checkouts. ``lock_and_redeem`` expects the
caller to already be inside a transaction; commit / rollback is owned by
the caller (typically :func:`datapulse.pos.commit.atomic_commit`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from datapulse.logging import get_logger
from datapulse.pos.models import (
    VoucherCreate,
    VoucherResponse,
    VoucherStatus,
    VoucherType,
)

log = get_logger(__name__)


def _row_to_response(row: dict) -> VoucherResponse:
    """Coerce a database row dict into a frozen :class:`VoucherResponse`."""
    return VoucherResponse(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        code=str(row["code"]),
        discount_type=VoucherType(row["discount_type"]),
        value=Decimal(str(row["value"])),
        max_uses=int(row["max_uses"]),
        uses=int(row["uses"]),
        status=VoucherStatus(row["status"]),
        starts_at=row.get("starts_at"),
        ends_at=row.get("ends_at"),
        min_purchase=(
            Decimal(str(row["min_purchase"])) if row.get("min_purchase") is not None else None
        ),
        redeemed_txn_id=(
            int(row["redeemed_txn_id"]) if row.get("redeemed_txn_id") is not None else None
        ),
        created_at=row["created_at"],
    )


class VoucherRepository:
    """Raw SQL access for the ``pos.vouchers`` table.

    All queries are tenant-scoped and parameterised. ``lock_and_redeem``
    atomically validates + redeems a voucher inside the caller's transaction.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def create(self, tenant_id: int, payload: VoucherCreate) -> VoucherResponse:
        """Insert a new voucher.  Raises 409 on duplicate (tenant_id, code)."""
        try:
            row = (
                self._session.execute(
                    text(
                        """
                        INSERT INTO pos.vouchers
                            (tenant_id, code, discount_type, value,
                             max_uses, starts_at, ends_at, min_purchase)
                        VALUES
                            (:tid, :code, :dtype, :val,
                             :mu, :starts_at, :ends_at, :min_p)
                        RETURNING
                            id, tenant_id, code, discount_type, value,
                            max_uses, uses, status, starts_at, ends_at,
                            min_purchase, redeemed_txn_id, created_at
                        """
                    ),
                    {
                        "tid": tenant_id,
                        "code": payload.code,
                        "dtype": payload.discount_type.value,
                        "val": payload.value,
                        "mu": payload.max_uses,
                        "starts_at": payload.starts_at,
                        "ends_at": payload.ends_at,
                        "min_p": payload.min_purchase,
                    },
                )
                .mappings()
                .first()
            )
        except IntegrityError as exc:
            # Unique violation on (tenant_id, code).
            self._session.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"voucher_code_already_exists:{payload.code}",
            ) from exc
        if row is None:  # pragma: no cover — INSERT RETURNING always yields a row
            raise HTTPException(status_code=500, detail="voucher_insert_no_row")
        return _row_to_response(dict(row))

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def list_for_tenant(
        self,
        tenant_id: int,
        *,
        status: VoucherStatus | None = None,
    ) -> list[VoucherResponse]:
        """Return all vouchers for a tenant, newest first, optionally filtered by status."""
        params: dict = {"tid": tenant_id}
        status_filter = ""
        if status is not None:
            status_filter = " AND status = :status"
            params["status"] = status.value
        rows = (
            self._session.execute(
                text(
                    f"""
                    SELECT
                        id, tenant_id, code, discount_type, value,
                        max_uses, uses, status, starts_at, ends_at,
                        min_purchase, redeemed_txn_id, created_at
                      FROM pos.vouchers
                     WHERE tenant_id = :tid{status_filter}
                  ORDER BY created_at DESC
                    """
                ),
                params,
            )
            .mappings()
            .all()
        )
        return [_row_to_response(dict(r)) for r in rows]

    def get_by_code(self, tenant_id: int, code: str) -> VoucherResponse | None:
        """Fetch a single voucher by (tenant_id, code) or None."""
        row = (
            self._session.execute(
                text(
                    """
                    SELECT
                        id, tenant_id, code, discount_type, value,
                        max_uses, uses, status, starts_at, ends_at,
                        min_purchase, redeemed_txn_id, created_at
                      FROM pos.vouchers
                     WHERE tenant_id = :tid
                       AND code = :code
                    """
                ),
                {"tid": tenant_id, "code": code},
            )
            .mappings()
            .first()
        )
        return _row_to_response(dict(row)) if row else None

    # ------------------------------------------------------------------
    # Atomic redemption
    # ------------------------------------------------------------------

    def lock_and_redeem(
        self,
        tenant_id: int,
        code: str,
        txn_id: int,
        now: datetime,
        *,
        cart_subtotal: Decimal | None = None,
    ) -> VoucherResponse:
        """Atomically validate + redeem a voucher inside the caller's transaction.

        Uses ``SELECT ... FOR UPDATE`` to serialise concurrent redemption
        attempts for the same (tenant_id, code). Must be called inside an
        existing transaction — the row-lock releases when the caller commits.

        Raises :class:`fastapi.HTTPException(400)` on any validation failure
        with one of these precise detail strings:

        * ``voucher_not_found``
        * ``voucher_inactive``
        * ``voucher_expired``
        * ``voucher_not_yet_active``
        * ``voucher_max_uses_reached``
        * ``voucher_min_purchase_unmet``

        Returns the updated :class:`VoucherResponse`.
        """
        row = (
            self._session.execute(
                text(
                    """
                    SELECT
                        id, tenant_id, code, discount_type, value,
                        max_uses, uses, status, starts_at, ends_at,
                        min_purchase, redeemed_txn_id, created_at
                      FROM pos.vouchers
                     WHERE tenant_id = :tid
                       AND code = :code
                       FOR UPDATE
                    """
                ),
                {"tid": tenant_id, "code": code},
            )
            .mappings()
            .first()
        )
        if row is None:
            raise HTTPException(status_code=400, detail="voucher_not_found")

        current = _row_to_response(dict(row))
        now_aware = now if now.tzinfo is not None else now.replace(tzinfo=UTC)

        if current.status != VoucherStatus.active:
            raise HTTPException(status_code=400, detail="voucher_inactive")
        if current.starts_at is not None and now_aware < current.starts_at:
            raise HTTPException(status_code=400, detail="voucher_not_yet_active")
        if current.ends_at is not None and now_aware > current.ends_at:
            raise HTTPException(status_code=400, detail="voucher_expired")
        if current.uses >= current.max_uses:
            raise HTTPException(status_code=400, detail="voucher_max_uses_reached")
        if (
            current.min_purchase is not None
            and cart_subtotal is not None
            and cart_subtotal < current.min_purchase
        ):
            raise HTTPException(status_code=400, detail="voucher_min_purchase_unmet")

        new_uses = current.uses + 1
        new_status = (
            VoucherStatus.redeemed.value
            if new_uses >= current.max_uses
            else VoucherStatus.active.value
        )
        updated = (
            self._session.execute(
                text(
                    """
                    UPDATE pos.vouchers
                       SET uses = uses + 1,
                           redeemed_txn_id = :txn,
                           updated_at = :now,
                           status = :new_status
                     WHERE id = :id
                     RETURNING
                        id, tenant_id, code, discount_type, value,
                        max_uses, uses, status, starts_at, ends_at,
                        min_purchase, redeemed_txn_id, created_at
                    """
                ),
                {
                    "txn": txn_id,
                    "now": now_aware,
                    "new_status": new_status,
                    "id": current.id,
                },
            )
            .mappings()
            .first()
        )
        if updated is None:  # pragma: no cover — UPDATE RETURNING always yields a row
            raise HTTPException(status_code=500, detail="voucher_redeem_no_row")
        return _row_to_response(dict(updated))

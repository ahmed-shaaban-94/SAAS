"""Void log + returns table access (pos.void_log / pos.returns + joins).

Extracted from the original 1,187-LOC ``repository.py`` facade (see #543).
Methods preserve their SQL text and parameter order byte-for-byte.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from datapulse.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

log = get_logger(__name__)


class VoidReturnRepoMixin:
    """Mixin for :class:`PosRepository` — requires ``self._session`` set by __init__."""

    _session: Session

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

    def get_void_log(self, transaction_id: int, *, tenant_id: int) -> dict[str, Any] | None:
        """Return the void record for a transaction (at most one per transaction)."""
        row = (
            self._session.execute(
                text("""
                    SELECT id, transaction_id, tenant_id, voided_by, reason, voided_at
                    FROM   pos.void_log
                    WHERE  transaction_id = :txn_id
                    AND    tenant_id      = :tenant_id
                    LIMIT  1
                """),
                {"txn_id": transaction_id, "tenant_id": tenant_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def list_returns(
        self,
        tenant_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List return records for a tenant, most recent first."""
        rows = (
            self._session.execute(
                text("""
                    SELECT id, tenant_id, original_transaction_id, return_transaction_id,
                           staff_id, reason, refund_amount, refund_method, notes, created_at
                    FROM   pos.returns
                    WHERE  tenant_id = :tenant_id
                    ORDER  BY created_at DESC
                    LIMIT  :limit OFFSET :offset
                """),
                {
                    "tenant_id": tenant_id,
                    "limit": limit,
                    "offset": offset,
                },
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

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

    def get_return(self, return_id: int, *, tenant_id: int) -> dict[str, Any] | None:
        """Return a single return record by ID, scoped to the given tenant."""
        row = (
            self._session.execute(
                text("""
                    SELECT id, tenant_id, original_transaction_id, return_transaction_id,
                           staff_id, reason, refund_amount, refund_method, notes, created_at
                    FROM   pos.returns
                    WHERE  id        = :return_id
                    AND    tenant_id = :tenant_id
                """),
                {"return_id": return_id, "tenant_id": tenant_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def list_returns_for_transaction(
        self, original_transaction_id: int, *, tenant_id: int
    ) -> list[dict[str, Any]]:
        """Return all return records linked to an original transaction."""
        rows = (
            self._session.execute(
                text("""
                    SELECT id, tenant_id, original_transaction_id, return_transaction_id,
                           staff_id, reason, refund_amount, refund_method, notes, created_at
                    FROM   pos.returns
                    WHERE  original_transaction_id = :original_txn_id
                    AND    tenant_id               = :tenant_id
                    ORDER  BY created_at ASC
                """),
                {"original_txn_id": original_transaction_id, "tenant_id": tenant_id},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_returned_quantities_for_transaction(
        self,
        original_transaction_id: int,
        *,
        tenant_id: int,
    ) -> list[dict[str, Any]]:
        """Sum already-returned quantities by ``(drug_code, batch_number)``.

        Joins :code:`pos.returns` -> :code:`pos.transaction_items` via
        ``return_transaction_id`` so the service can enforce that the sum of
        all prior returns + the current request does not exceed the original
        sold quantity per line. Prevents the unlimited-refund path.
        """
        rows = (
            self._session.execute(
                text("""
                    SELECT ti.drug_code,
                           ti.batch_number,
                           SUM(ti.quantity) AS returned_qty
                    FROM   pos.returns r
                    JOIN   pos.transaction_items ti
                       ON  ti.transaction_id = r.return_transaction_id
                    WHERE  r.original_transaction_id = :original_txn_id
                    AND    r.tenant_id               = :tenant_id
                    GROUP  BY ti.drug_code, ti.batch_number
                """),
                {"original_txn_id": original_transaction_id, "tenant_id": tenant_id},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

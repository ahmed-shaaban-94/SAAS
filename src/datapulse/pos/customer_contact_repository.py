"""Repository for POS customer contact lookups (phone → customer_key)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class CustomerContactRepository:
    """Data-access layer for ``pos.customer_contact``.

    Joins against ``public_marts.dim_customer`` to resolve phone → customer
    in a single query. All SQL is parameterized.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_phone(self, phone_e164: str) -> dict | None:
        """Return contact + name row for ``phone_e164``, or ``None`` if unknown."""
        row = (
            self._session.execute(
                text("""
                    SELECT
                        cc.customer_key,
                        cc.phone_e164,
                        c.customer_name
                    FROM   pos.customer_contact cc
                    JOIN   public_marts.dim_customer c
                           ON c.tenant_id    = cc.tenant_id
                          AND c.customer_key = cc.customer_key
                    WHERE  cc.phone_e164 = :phone
                    LIMIT  1
                """),
                {"phone": phone_e164},
            )
            .mappings()
            .first()
        )
        return dict(row) if row is not None else None

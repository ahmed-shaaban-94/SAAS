"""Terminal-session table access (pos.terminal_sessions).

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


class TerminalRepoMixin:
    """Mixin for :class:`PosRepository` — requires ``self._session`` set by __init__."""

    _session: Session

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

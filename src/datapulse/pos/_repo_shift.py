"""Shifts + cash drawer events table access.

Covers pos.shift_records and pos.cash_drawer_events.

Extracted from the original 1,187-LOC ``repository.py`` facade (see #543).
Methods preserve their SQL text and parameter order byte-for-byte.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from datapulse.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

log = get_logger(__name__)


class ShiftRepoMixin:
    """Mixin for :class:`PosRepository` — requires ``self._session`` set by __init__."""

    _session: Session

    def create_shift_record(
        self,
        *,
        terminal_id: int,
        tenant_id: int,
        staff_id: str,
        shift_date: date,
        opened_at: datetime,
        opening_cash: Decimal,
    ) -> dict[str, Any]:
        """Open a new shift record for a terminal."""
        row = (
            self._session.execute(
                text("""
                    INSERT INTO pos.shift_records
                        (terminal_id, tenant_id, staff_id, shift_date,
                         opened_at, opening_cash)
                    VALUES
                        (:terminal_id, :tenant_id, :staff_id, :shift_date,
                         :opened_at, :opening_cash)
                    RETURNING
                        id, terminal_id, tenant_id, staff_id, shift_date,
                        opened_at, closed_at, opening_cash, closing_cash,
                        expected_cash, variance
                """),
                {
                    "terminal_id": terminal_id,
                    "tenant_id": tenant_id,
                    "staff_id": staff_id,
                    "shift_date": shift_date,
                    "opened_at": opened_at,
                    "opening_cash": opening_cash,
                },
            )
            .mappings()
            .one()
        )
        log.info("pos.shift.created", shift_id=row["id"], terminal_id=terminal_id)
        return dict(row)

    def update_shift_record(
        self,
        shift_id: int,
        *,
        closing_cash: Decimal | None = None,
        expected_cash: Decimal | None = None,
        variance: Decimal | None = None,
        closed_at: datetime | None = None,
    ) -> dict[str, Any] | None:
        """Update closing values for a shift."""
        row = (
            self._session.execute(
                text("""
                    UPDATE pos.shift_records
                    SET    closing_cash  = COALESCE(:closing_cash,  closing_cash),
                           expected_cash = COALESCE(:expected_cash, expected_cash),
                           variance      = COALESCE(:variance,      variance),
                           closed_at     = COALESCE(:closed_at,     closed_at)
                    WHERE  id = :shift_id
                    RETURNING
                        id, terminal_id, tenant_id, staff_id, shift_date,
                        opened_at, closed_at, opening_cash, closing_cash,
                        expected_cash, variance
                """),
                {
                    "shift_id": shift_id,
                    "closing_cash": closing_cash,
                    "expected_cash": expected_cash,
                    "variance": variance,
                    "closed_at": closed_at,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_current_shift(self, terminal_id: int) -> dict[str, Any] | None:
        """Return the currently open (unclosed) shift for a terminal."""
        row = (
            self._session.execute(
                text("""
                    SELECT id, terminal_id, tenant_id, staff_id, shift_date,
                           opened_at, closed_at, opening_cash, closing_cash,
                           expected_cash, variance
                    FROM   pos.shift_records
                    WHERE  terminal_id = :terminal_id
                    AND    closed_at   IS NULL
                    ORDER  BY opened_at DESC
                    LIMIT  1
                """),
                {"terminal_id": terminal_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def list_shifts(
        self,
        tenant_id: int,
        *,
        terminal_id: int | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List shift records for a tenant, most recent first."""
        rows = (
            self._session.execute(
                text("""
                    SELECT id, terminal_id, tenant_id, staff_id, shift_date,
                           opened_at, closed_at, opening_cash, closing_cash,
                           expected_cash, variance
                    FROM   pos.shift_records
                    WHERE  tenant_id  = :tenant_id
                    AND    (:terminal_id IS NULL OR terminal_id = :terminal_id)
                    ORDER  BY opened_at DESC
                    LIMIT  :limit OFFSET :offset
                """),
                {
                    "tenant_id": tenant_id,
                    "terminal_id": terminal_id,
                    "limit": limit,
                    "offset": offset,
                },
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_shift_by_id(self, shift_id: int) -> dict[str, Any] | None:
        """Return a single shift record by ID."""
        row = (
            self._session.execute(
                text("""
                    SELECT id, terminal_id, tenant_id, staff_id, shift_date,
                           opened_at, closed_at, opening_cash, closing_cash,
                           expected_cash, variance
                    FROM   pos.shift_records
                    WHERE  id = :shift_id
                """),
                {"shift_id": shift_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_shift_summary_data(
        self,
        terminal_id: int,
        *,
        opened_at: datetime,
        closed_at: datetime,
    ) -> dict[str, Any]:
        """Return transaction count + total completed sales for a shift time window."""
        row = (
            self._session.execute(
                text("""
                    SELECT
                        COUNT(*)::INT                                        AS transaction_count,
                        COALESCE(SUM(grand_total) FILTER (WHERE status = 'completed'), 0)
                                                                             AS total_sales
                    FROM pos.transactions
                    WHERE terminal_id = :terminal_id
                    AND   created_at >= :opened_at
                    AND   created_at <= :closed_at
                """),
                {
                    "terminal_id": terminal_id,
                    "opened_at": opened_at,
                    "closed_at": closed_at,
                },
            )
            .mappings()
            .first()
        )
        if row:
            return dict(row)
        return {"transaction_count": 0, "total_sales": Decimal("0")}

    def record_cash_event(
        self,
        *,
        terminal_id: int,
        tenant_id: int,
        event_type: str,
        amount: Decimal,
        reference_id: str | None = None,
    ) -> dict[str, Any]:
        """Append an immutable cash drawer event."""
        row = (
            self._session.execute(
                text("""
                    INSERT INTO pos.cash_drawer_events
                        (terminal_id, tenant_id, event_type, amount, reference_id)
                    VALUES
                        (:terminal_id, :tenant_id, :event_type, :amount, :reference_id)
                    RETURNING id, terminal_id, tenant_id, event_type, amount,
                              reference_id, timestamp
                """),
                {
                    "terminal_id": terminal_id,
                    "tenant_id": tenant_id,
                    "event_type": event_type,
                    "amount": amount,
                    "reference_id": reference_id,
                },
            )
            .mappings()
            .one()
        )
        return dict(row)

    def get_cash_events(
        self,
        terminal_id: int,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return cash drawer events for a terminal, most recent first."""
        rows = (
            self._session.execute(
                text("""
                    SELECT id, terminal_id, tenant_id, event_type, amount,
                           reference_id, timestamp
                    FROM   pos.cash_drawer_events
                    WHERE  terminal_id = :terminal_id
                    ORDER  BY timestamp DESC
                    LIMIT  :limit
                """),
                {"terminal_id": terminal_id, "limit": limit},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_active_shift_for_staff(
        self,
        tenant_id: int,
        staff_id: str,
    ) -> dict[str, Any] | None:
        """Return the staff's currently-open shift, if any (#627).

        A staff can have at most one open shift across all terminals (enforced
        by convention, not by a DB constraint — the terminal-level unique
        index on open sessions is the primary gate). Returns the most recent
        open row; callers that need a stricter guarantee should check
        ``terminal_sessions`` instead.
        """
        row = (
            self._session.execute(
                text("""
                    SELECT id, terminal_id, tenant_id, staff_id, shift_date,
                           opened_at, closed_at, opening_cash, closing_cash,
                           expected_cash, variance
                    FROM   pos.shift_records
                    WHERE  tenant_id = :tenant_id
                    AND    staff_id  = :staff_id
                    AND    closed_at IS NULL
                    ORDER  BY opened_at DESC
                    LIMIT  1
                """),
                {"tenant_id": tenant_id, "staff_id": staff_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_shift_commission_summary(
        self,
        shift_id: int,
    ) -> dict[str, Any]:
        """Return ``commission_earned`` + live sales totals for a shift (#627).

        Sums ``line_total * commission_rate`` across completed transactions
        in the shift, falling back to 0 for drugs without a catalog meta row
        (LEFT JOIN). Returns deterministic zeros for a shift with no items
        so the terminal's status-strip pill renders correctly on empty shifts.
        """
        row = (
            self._session.execute(
                text("""
                    SELECT
                        COALESCE(
                            SUM(ti.line_total * COALESCE(m.commission_rate, 0)),
                            0
                        ) AS commission_earned_egp,
                        COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'completed')
                            AS transactions_so_far,
                        COALESCE(
                            SUM(t.grand_total) FILTER (WHERE t.status = 'completed'),
                            0
                        ) AS sales_so_far_egp
                    FROM        pos.transactions t
                    LEFT  JOIN  pos.transaction_items ti
                                ON ti.transaction_id = t.id
                    LEFT  JOIN  pos.product_catalog_meta m
                                ON m.tenant_id = t.tenant_id
                               AND m.drug_code = ti.drug_code
                    WHERE       t.shift_id = :shift_id
                """),
                {"shift_id": shift_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            return {
                "commission_earned_egp": Decimal("0"),
                "transactions_so_far": 0,
                "sales_so_far_egp": Decimal("0"),
            }
        return dict(row)

    def get_terminal_daily_target(
        self,
        terminal_id: int,
    ) -> Decimal | None:
        """Return ``daily_sales_target_egp`` for a terminal, ``None`` if unset (#627).

        Joins ``pos.terminal_sessions`` → ``pos.terminal_config`` via the
        stable ``terminal_name`` key. Returns ``None`` for terminals without
        a config row OR with an explicit NULL target — both cases mean "no
        target" to the UI, which then hides the trophy bar.
        """
        row = (
            self._session.execute(
                text("""
                    SELECT tc.daily_sales_target_egp
                    FROM        pos.terminal_sessions ts
                    LEFT  JOIN  pos.terminal_config   tc
                                ON tc.tenant_id     = ts.tenant_id
                               AND tc.terminal_name = ts.terminal_name
                    WHERE  ts.id = :terminal_id
                    LIMIT  1
                """),
                {"terminal_id": terminal_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        value = row.get("daily_sales_target_egp")
        return Decimal(str(value)) if value is not None else None

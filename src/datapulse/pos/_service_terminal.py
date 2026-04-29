"""Terminal-lifecycle mixin for :class:`PosService`.

Owns the open/pause/resume/close terminal state machine and terminal lookups.
No inventory, no cart, no money — pure terminal CRUD + state transitions.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from datapulse.logging import get_logger
from datapulse.pos.constants import TerminalStatus
from datapulse.pos.exceptions import PosError
from datapulse.pos.models import TerminalSession
from datapulse.pos.terminal import assert_can_transition

if TYPE_CHECKING:
    from datapulse.pos.repository import PosRepository

log = get_logger(__name__)


class TerminalOpsMixin:
    """Mixin providing terminal-session lifecycle methods.

    Requires ``self._repo`` to be set by :meth:`PosService.__init__`.
    """

    _repo: PosRepository

    def open_terminal(
        self,
        *,
        tenant_id: int,
        site_code: str,
        staff_id: str,
        terminal_name: str = "Terminal-1",
        opening_cash: Decimal = Decimal("0"),
    ) -> TerminalSession:
        """Open a fresh terminal session in ``open`` state.

        Idempotent: if an active (non-closed) session already exists for
        ``(tenant_id, terminal_name)``, return it instead of attempting a
        new INSERT. Without this, the partial-unique index
        ``uq_pos_terminal_active`` raises IntegrityError on the second
        open — surfacing as a 500 to the cashier whenever the previous
        session was not closed cleanly (browser refresh, app crash, power
        loss). See incident 2026-04-29.
        """
        existing = next(
            (
                t
                for t in self._repo.get_active_terminals(tenant_id)
                if t["terminal_name"] == terminal_name
            ),
            None,
        )
        if existing is not None:
            log.info(
                "pos.terminal.resumed",
                terminal_id=existing["id"],
                staff_id=staff_id,
                prior_staff_id=existing["staff_id"],
            )
            return TerminalSession.model_validate(existing)

        row = self._repo.create_terminal_session(
            tenant_id=tenant_id,
            site_code=site_code,
            staff_id=staff_id,
            terminal_name=terminal_name,
            opening_cash=opening_cash,
        )
        log.info("pos.terminal.opened", terminal_id=row["id"], staff_id=staff_id)
        return TerminalSession.model_validate(row)

    def _transition_terminal(
        self,
        terminal_id: int,
        target: TerminalStatus,
        *,
        tenant_id: int,
        closing_cash: Decimal | None = None,
    ) -> TerminalSession:
        """Validate + apply a terminal status change. Raises if illegal."""
        current = self._repo.get_terminal_session(terminal_id, tenant_id=tenant_id)
        if current is None:
            raise PosError(
                message=f"Terminal {terminal_id} does not exist",
                detail=f"terminal_id={terminal_id}",
            )
        assert_can_transition(terminal_id, current["status"], target)
        updated = self._repo.update_terminal_status(
            terminal_id, target.value, tenant_id=tenant_id, closing_cash=closing_cash
        )
        if updated is None:
            raise PosError(
                message=f"Terminal {terminal_id} update failed",
                detail=f"terminal_id={terminal_id} target={target.value}",
            )
        return TerminalSession.model_validate(updated)

    def pause_terminal(self, terminal_id: int, *, tenant_id: int) -> TerminalSession:
        """Move ``active`` -> ``paused``."""
        return self._transition_terminal(terminal_id, TerminalStatus.paused, tenant_id=tenant_id)

    def resume_terminal(self, terminal_id: int, *, tenant_id: int) -> TerminalSession:
        """Move ``paused`` -> ``active``."""
        return self._transition_terminal(terminal_id, TerminalStatus.active, tenant_id=tenant_id)

    def close_terminal(
        self,
        terminal_id: int,
        *,
        tenant_id: int,
        closing_cash: Decimal,
    ) -> TerminalSession:
        """Close a terminal session and record the closing cash drawer total."""
        return self._transition_terminal(
            terminal_id, TerminalStatus.closed, tenant_id=tenant_id, closing_cash=closing_cash
        )

    def list_active_terminals(self, tenant_id: int) -> list[TerminalSession]:
        """All non-closed terminals for the tenant."""
        rows = self._repo.get_active_terminals(tenant_id)
        return [TerminalSession.model_validate(r) for r in rows]

    def get_terminal(self, terminal_id: int, *, tenant_id: int) -> TerminalSession | None:
        row = self._repo.get_terminal_session(terminal_id, tenant_id=tenant_id)
        return TerminalSession.model_validate(row) if row else None

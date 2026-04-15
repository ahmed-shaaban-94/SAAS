"""Terminal session lifecycle helpers for the POS module.

Centralises the state-transition rules and cash reconciliation logic so the
service layer stays declarative. Terminal states form a small finite-state
machine::

              ┌─── pause ───┐
              v             |
    open ──> active <──── paused
      └────┬─────┘           |
           v                 v
          closed <───────────┘  (close allowed from any non-closed state)

* ``open``   — fresh session, no transactions yet
* ``active`` — at least one transaction started, drawer in use
* ``paused`` — operator stepped away; no transactions allowed
* ``closed`` — shift ended, cash reconciled; immutable thereafter

The helpers only encode rules — the service layer is responsible for
applying them via the repository.
"""

from __future__ import annotations

from decimal import Decimal

from datapulse.pos.constants import TerminalStatus
from datapulse.pos.exceptions import TerminalNotActiveError

# ---------------------------------------------------------------------------
# Allowed transitions
# ---------------------------------------------------------------------------

# (current, next) -> allowed
_ALLOWED_TRANSITIONS: frozenset[tuple[TerminalStatus, TerminalStatus]] = frozenset(
    {
        # Opening
        (TerminalStatus.open, TerminalStatus.active),
        (TerminalStatus.open, TerminalStatus.closed),  # close without activity
        # Active operation
        (TerminalStatus.active, TerminalStatus.paused),
        (TerminalStatus.active, TerminalStatus.closed),
        # Resume
        (TerminalStatus.paused, TerminalStatus.active),
        (TerminalStatus.paused, TerminalStatus.closed),
    }
)

# States in which transactions may be added / checked out
_TRANSACTABLE_STATES: frozenset[TerminalStatus] = frozenset(
    {TerminalStatus.open, TerminalStatus.active}
)


# ---------------------------------------------------------------------------
# Transition validation
# ---------------------------------------------------------------------------


def can_transition(
    current: TerminalStatus | str,
    target: TerminalStatus | str,
) -> bool:
    """Return True when ``current -> target`` is a legal transition."""
    try:
        cur = TerminalStatus(current)
        tgt = TerminalStatus(target)
    except ValueError:
        return False
    if cur == tgt:
        return False  # no-op is not a transition
    return (cur, tgt) in _ALLOWED_TRANSITIONS


def assert_can_transition(
    terminal_id: int,
    current: TerminalStatus | str,
    target: TerminalStatus | str,
) -> None:
    """Raise :class:`TerminalNotActiveError` when a transition is illegal.

    The error message exposes the *current* state (stable identifier for UI
    handling) rather than the attempted target.
    """
    if not can_transition(current, target):
        raise TerminalNotActiveError(
            terminal_id=terminal_id,
            current_status=str(current),
        )


def assert_transactable(terminal_id: int, current: TerminalStatus | str) -> None:
    """Raise when a transaction is attempted on a terminal that cannot transact.

    Only ``open`` and ``active`` terminals may accept new cart items / checkouts.
    ``paused`` blocks further activity until explicitly resumed.
    """
    try:
        cur = TerminalStatus(current)
    except ValueError as exc:
        raise TerminalNotActiveError(
            terminal_id=terminal_id, current_status=str(current)
        ) from exc
    if cur not in _TRANSACTABLE_STATES:
        raise TerminalNotActiveError(
            terminal_id=terminal_id, current_status=str(cur),
        )


# ---------------------------------------------------------------------------
# Cash reconciliation
# ---------------------------------------------------------------------------


def compute_variance(
    opening_cash: Decimal,
    closing_cash: Decimal,
    expected_cash: Decimal,
) -> Decimal:
    """Return ``closing_cash - expected_cash`` (positive = over, negative = short).

    ``expected_cash`` is typically ``opening_cash + net_cash_flow`` where
    ``net_cash_flow`` aggregates cash-drawer events for the shift. The
    explicit arg keeps this pure and unit-testable.
    """
    # ``opening_cash`` is not used in the arithmetic but is kept in the signature
    # so callers reading the function read the full picture of the shift.
    _ = opening_cash
    return Decimal(closing_cash) - Decimal(expected_cash)


def compute_expected_cash(
    opening_cash: Decimal,
    cash_sales: Decimal,
    cash_refunds: Decimal = Decimal("0"),
    floats_in: Decimal = Decimal("0"),
    pickups: Decimal = Decimal("0"),
) -> Decimal:
    """Expected drawer total at close-of-shift given the shift's cash events.

    ``opening_cash`` + ``cash_sales`` + ``floats_in`` - ``cash_refunds`` - ``pickups``
    """
    return (
        Decimal(opening_cash)
        + Decimal(cash_sales)
        + Decimal(floats_in)
        - Decimal(cash_refunds)
        - Decimal(pickups)
    )

"""Business exception hierarchy for the POS module.

All POS exceptions inherit from ``PosError -> DataPulseError``.
The FastAPI exception handlers in ``api/app.py`` map each class to an
appropriate HTTP status code and a safe, user-facing message.

Usage::

    from datapulse.pos.exceptions import InsufficientStockError
    raise InsufficientStockError("DRUG001", requested=5, available=3)
"""

from __future__ import annotations

from decimal import Decimal

from datapulse.core.exceptions import DataPulseError


class PosError(DataPulseError):
    """Base class for all POS-specific business exceptions.

    Maps to HTTP 400 Bad Request unless a more specific handler is registered.
    """


class InsufficientStockError(PosError):
    """Raised when a drug's available stock is less than the requested quantity.

    Maps to HTTP 409 Conflict (business constraint violation).
    """

    def __init__(
        self,
        drug_code: str,
        requested: Decimal,
        available: Decimal,
        site_code: str | None = None,
    ) -> None:
        site_hint = f" at {site_code}" if site_code else ""
        super().__init__(
            message=f"Insufficient stock for {drug_code}{site_hint}: "
            f"requested {requested}, available {available}",
            detail=f"drug_code={drug_code} requested={requested} available={available}",
        )
        self.drug_code = drug_code
        self.requested = requested
        self.available = available
        self.site_code = site_code


class TerminalNotActiveError(PosError):
    """Raised when a POS operation is attempted on a non-active terminal.

    Maps to HTTP 409 Conflict.
    """

    def __init__(self, terminal_id: int, current_status: str) -> None:
        super().__init__(
            message=f"Terminal {terminal_id} is not active (status: {current_status}). "
            "Open or resume the terminal before processing transactions.",
            detail=f"terminal_id={terminal_id} status={current_status}",
        )
        self.terminal_id = terminal_id
        self.current_status = current_status


class PharmacistVerificationRequiredError(PosError):
    """Raised when a controlled-substance drug requires pharmacist sign-off.

    Maps to HTTP 403 Forbidden (authorization step needed, not missing auth).
    """

    def __init__(
        self,
        drug_code: str,
        drug_category: str | None = None,
        message: str | None = None,
    ) -> None:
        if message is None:
            category_hint = f" (category: {drug_category})" if drug_category else ""
            message = (
                f"Drug {drug_code}{category_hint} is a controlled substance. "
                "Pharmacist verification is required before dispensing."
            )
        super().__init__(
            message=message,
            detail=f"drug_code={drug_code} category={drug_category}",
        )
        self.drug_code = drug_code
        self.drug_category = drug_category


class VoidNotAllowedError(PosError):
    """Raised when attempting to void a transaction that cannot be voided.

    Maps to HTTP 409 Conflict.
    Common cases: already voided, returned, or older than the void window.
    """

    def __init__(self, transaction_id: int, reason: str) -> None:
        super().__init__(
            message=f"Cannot void transaction {transaction_id}: {reason}",
            detail=f"transaction_id={transaction_id} reason={reason}",
        )
        self.transaction_id = transaction_id


class ShiftNotOpenError(PosError):
    """Raised when a transaction is attempted without an open shift.

    Maps to HTTP 409 Conflict.
    """

    def __init__(self, terminal_id: int) -> None:
        super().__init__(
            message=f"No open shift for terminal {terminal_id}. "
            "Start a shift before processing transactions.",
            detail=f"terminal_id={terminal_id}",
        )
        self.terminal_id = terminal_id

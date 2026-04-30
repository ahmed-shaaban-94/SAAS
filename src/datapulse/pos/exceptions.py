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


class RiderNotFoundError(PosError):
    """Raised when a rider lookup returns no row for the given tenant.

    Maps to HTTP 404 Not Found.
    """

    def __init__(self, rider_id: int) -> None:
        super().__init__(
            message=f"Rider {rider_id} not found",
            detail=f"rider_id={rider_id}",
        )
        self.rider_id = rider_id


class RiderUnavailableError(PosError):
    """Raised when a rider is not in 'available' status at dispatch time.

    Maps to HTTP 409 Conflict.
    """

    def __init__(self, rider_id: int, current_status: str) -> None:
        super().__init__(
            message=f"Rider {rider_id} is not available (status: {current_status})",
            detail=f"rider_id={rider_id} status={current_status}",
        )
        self.rider_id = rider_id
        self.current_status = current_status


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


class InvalidPhoneError(PosError):
    """Raised when a caller-supplied phone fails E.164 normalization (#629).

    Maps to HTTP 400 via the generic ``DataPulseError`` handler.
    """

    def __init__(self, message: str = "Invalid phone number.") -> None:
        super().__init__(message=message, detail="phone_normalize_failed")


class WhatsAppDisabledError(PosError):
    """Raised when a WhatsApp endpoint is hit but the feature is off (#629).

    Maps to HTTP 503 via a dedicated handler so the UI can fall back to
    "Print instead" per the issue acceptance criteria.
    """

    def __init__(self) -> None:
        super().__init__(
            message="WhatsApp receipt delivery is not enabled on this deployment.",
            detail="whatsapp_feature_disabled",
        )


class WhatsAppDeliveryFailedError(PosError):
    """Raised when the WhatsApp provider fails after the retry budget (#629).

    Maps to HTTP 502 via a dedicated handler. The detail carries a
    provider-supplied reason so support can triage without leaking the
    raw phone number.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(
            message=f"Failed to send WhatsApp receipt: {reason}",
            detail=f"whatsapp_provider_error reason={reason}",
        )
        self.reason = reason


# ---------------------------------------------------------------------------
# Layer-boundary domain exceptions (#679)
# The exceptions below replace ``HTTPException`` raises in repo/service layers.
# ``api/app.py`` registers handlers that map each class to the correct HTTP
# status code and preserves the legacy machine-readable ``detail`` strings.
# ---------------------------------------------------------------------------


class PosNotFoundError(PosError):
    """Raised when a POS resource is not found.

    Maps to HTTP 404 Not Found by default, or HTTP 400 for legacy paths that
    historically used 400 (e.g. voucher redemption in commit flow).

    ``code`` is the machine-readable detail string clients key off
    (e.g. ``"voucher_not_found"``, ``"promotion_not_found"``).
    """

    def __init__(self, code: str, *, http_status: int = 404, message: str | None = None) -> None:
        super().__init__(message=message or code, detail=code)
        self.code = code
        self.http_status = http_status


class PosConflictError(PosError):
    """Raised when a POS operation conflicts with current state.

    Maps to HTTP 409 Conflict.

    ``code`` is the machine-readable detail string
    (e.g. ``"voucher_code_already_exists:X"``, ``"provisional_work_pending"``).
    """

    def __init__(self, code: str, *, message: str | None = None) -> None:
        super().__init__(message=message or code, detail=code)
        self.code = code


class PosValidationError(PosError):
    """Raised when POS input fails business validation.

    Maps to HTTP 400 Bad Request.

    ``code`` is the machine-readable detail string
    (e.g. ``"voucher_inactive"``, ``"promotion_expired"``).
    """

    def __init__(self, code: str, *, message: str | None = None) -> None:
        super().__init__(message=message or code, detail=code)
        self.code = code


class PosInternalError(PosError):
    """Raised for unexpected DB-level invariant violations (INSERT RETURNING no row, etc.).

    Maps to HTTP 500 Internal Server Error.
    """

    def __init__(self, code: str, *, message: str | None = None) -> None:
        super().__init__(message=message or code, detail=code)
        self.code = code

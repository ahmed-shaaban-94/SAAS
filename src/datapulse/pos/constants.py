"""Constants and enumerations for the POS module.

Using str-based enums so values serialize naturally in Pydantic models
and appear as readable strings in API responses and database columns.
"""

from __future__ import annotations

from enum import StrEnum


class TransactionStatus(StrEnum):
    """Lifecycle states of a POS transaction."""

    draft = "draft"
    completed = "completed"
    voided = "voided"
    returned = "returned"


class TerminalStatus(StrEnum):
    """Lifecycle states of a POS terminal session."""

    open = "open"
    active = "active"
    paused = "paused"
    closed = "closed"


class PaymentMethod(StrEnum):
    """Accepted payment methods at checkout."""

    cash = "cash"
    card = "card"
    insurance = "insurance"
    mixed = "mixed"


class CashDrawerEventType(StrEnum):
    """Types of cash drawer movements recorded during a shift."""

    sale = "sale"
    refund = "refund"
    float = "float"  # opening float added to drawer
    pickup = "pickup"  # cash removed from drawer mid-shift


class ReturnReason(StrEnum):
    """Allowed reasons for a drug return."""

    defective = "defective"
    wrong_drug = "wrong_drug"
    expired = "expired"
    customer_request = "customer_request"


class ReceiptFormat(StrEnum):
    """Output formats for a receipt."""

    thermal = "thermal"  # ESC/POS byte stream for thermal printers
    pdf = "pdf"  # PDF binary for email / archiving
    email = "email"  # Metadata row for email delivery tracking


# Controlled-substance drug categories that require pharmacist verification.
# Configurable at the application level; stored as a frozenset for O(1) lookup.
CONTROLLED_CATEGORIES: frozenset[str] = frozenset(
    {
        "narcotic",
        "psychotropic",
        "controlled",
        "schedule_ii",
        "schedule_iii",
        "schedule_iv",
        "schedule_v",
    }
)

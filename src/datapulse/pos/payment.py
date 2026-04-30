"""Payment gateway abstraction for the POS module.

Design:
- ``PaymentGateway`` ABC — single method ``process_payment``.
- ``CashGateway`` — validates tendered >= amount, calculates change.
- ``ExternalCardTerminalGateway`` (in ``external_terminal_gateway``) —
  records a card payment already approved on a physical terminal.
  Card never enters our software (PCI scope shrinks to SAQ-B).
- ``InsuranceGateway`` — fails closed until a real insurer API is wired.
- ``SplitPaymentProcessor`` — orchestrates two gateways for mixed payments.

All financial arithmetic uses ``Decimal`` to prevent floating-point drift.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from datapulse.pos.exceptions import PosValidationError

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PaymentResult:
    """Outcome of a payment processing attempt."""

    success: bool
    method: str
    amount_charged: Decimal
    change_due: Decimal = Decimal("0")
    authorization_code: str | None = None
    message: str = ""

    def raise_if_failed(self) -> None:
        """Raise ``PosError`` with the failure message if not successful."""
        if not self.success:
            raise PosValidationError(
                "payment_failed",
                message=self.message or f"Payment failed for method {self.method}",
            )


# ---------------------------------------------------------------------------
# ABC
# ---------------------------------------------------------------------------


class PaymentGateway(ABC):
    """Abstract base for all POS payment gateways."""

    @abstractmethod
    def process_payment(
        self,
        amount: Decimal,
        *,
        tendered: Decimal | None = None,
        insurance_no: str | None = None,
        card_token: str | None = None,
        **kwargs,
    ) -> PaymentResult:
        """Process a payment for the given ``amount``.

        Returns a ``PaymentResult`` regardless of success/failure.
        Implementations must NOT raise exceptions for expected failure
        cases (e.g., insufficient cash) — use ``PaymentResult(success=False)``.
        """


# ---------------------------------------------------------------------------
# Cash gateway
# ---------------------------------------------------------------------------


class CashGateway(PaymentGateway):
    """Cash payment processing — validates tendered >= amount."""

    def process_payment(
        self,
        amount: Decimal,
        *,
        tendered: Decimal | None = None,
        insurance_no: str | None = None,
        card_token: str | None = None,
        **kwargs,
    ) -> PaymentResult:
        if tendered is None:
            # When tendered is not provided, assume exact payment
            tendered = amount

        tendered = tendered.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        amount = amount.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        if tendered < amount:
            return PaymentResult(
                success=False,
                method="cash",
                amount_charged=Decimal("0"),
                message=f"Insufficient cash: tendered {tendered}, required {amount}",
            )

        change = (tendered - amount).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return PaymentResult(
            success=True,
            method="cash",
            amount_charged=amount,
            change_due=change,
            message="Cash payment accepted",
        )


# ---------------------------------------------------------------------------
# Insurance gateway (stub)
# ---------------------------------------------------------------------------


class InsuranceGateway(PaymentGateway):
    """Insurance payment — fails closed until a real insurer-API is wired.

    The original stub returned ``success=True`` for any non-empty insurance
    number, which let a cashier complete any-value sale with an arbitrary
    string. For pilot we fail closed: cashier must use cash or card. A live
    insurer integration (authorization call + claim persistence) replaces
    this.
    """

    def process_payment(
        self,
        amount: Decimal,
        *,
        tendered: Decimal | None = None,
        insurance_no: str | None = None,
        card_token: str | None = None,
        **kwargs,
    ) -> PaymentResult:
        return PaymentResult(
            success=False,
            method="insurance",
            amount_charged=Decimal("0"),
            message=(
                "Insurance payment gateway not yet configured. "
                "Use cash or card, or capture the claim manually."
            ),
        )


# ---------------------------------------------------------------------------
# Split payment processor
# ---------------------------------------------------------------------------


@dataclass
class SplitPaymentResult:
    """Result of a split (mixed) payment operation."""

    success: bool
    parts: list[PaymentResult] = field(default_factory=list)
    total_charged: Decimal = Decimal("0")
    total_change: Decimal = Decimal("0")
    message: str = ""


class SplitPaymentProcessor:
    """Handles mixed payment methods (e.g., partial cash + partial insurance).

    Usage::

        processor = SplitPaymentProcessor()
        result = processor.process(
            grand_total=Decimal("135.50"),
            splits=[
                {"method": "cash",      "amount": Decimal("100.00"), "tendered": Decimal("100.00")},
                {"method": "insurance", "amount": Decimal("35.50"),  "insurance_no": "INS-123"},
            ],
        )
    """

    def __init__(self) -> None:
        # Per-instance dict so two SplitPaymentProcessor objects never share state.
        # ``card`` deliberately omitted: card payments via external terminal
        # require a single approval code per transaction, which doesn't
        # compose with split semantics. Mixing card with cash should be
        # done by ringing two separate transactions.
        self._GATEWAYS: dict[str, PaymentGateway] = {
            "cash": CashGateway(),
            "insurance": InsuranceGateway(),
        }

    def process(
        self,
        grand_total: Decimal,
        splits: list[dict],
    ) -> SplitPaymentResult:
        """Process a list of payment splits whose amounts sum to ``grand_total``.

        Args:
            grand_total: Total amount to be collected.
            splits:      List of dicts with keys: ``method``, ``amount``,
                         and any gateway-specific keys (``tendered``, ``insurance_no``).

        Returns:
            ``SplitPaymentResult`` — check ``.success`` before finalising.
        """
        # Validate split totals
        split_total = sum(
            (Decimal(str(s.get("amount", 0))) for s in splits),
            start=Decimal("0"),
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        expected = grand_total.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        if split_total != expected:
            return SplitPaymentResult(
                success=False,
                message=f"Split amounts {split_total} do not equal grand total {expected}",
            )

        parts: list[PaymentResult] = []
        for split in splits:
            method = split.get("method", "cash")
            gateway = self._GATEWAYS.get(method, CashGateway())
            result = gateway.process_payment(
                Decimal(str(split.get("amount", 0))),
                tendered=split.get("tendered"),
                insurance_no=split.get("insurance_no"),
                card_token=split.get("card_token"),
            )
            parts.append(result)
            if not result.success:
                return SplitPaymentResult(
                    success=False,
                    parts=parts,
                    message=f"Payment failed for {method}: {result.message}",
                )

        total_charged = sum((p.amount_charged for p in parts), start=Decimal("0"))
        total_change = sum((p.change_due for p in parts), start=Decimal("0"))
        return SplitPaymentResult(
            success=True,
            parts=parts,
            total_charged=total_charged,
            total_change=total_change,
        )


# ---------------------------------------------------------------------------
# Gateway factory
# ---------------------------------------------------------------------------


def get_gateway(method: str) -> PaymentGateway:
    """Return the appropriate gateway for the given payment method string."""
    # Imported here to avoid a circular import — external_terminal_gateway
    # imports from this module.
    from datapulse.pos.external_terminal_gateway import ExternalCardTerminalGateway

    gateways: dict[str, PaymentGateway] = {
        "cash": CashGateway(),
        "card": ExternalCardTerminalGateway(),
        "insurance": InsuranceGateway(),
    }
    return gateways.get(method, CashGateway())

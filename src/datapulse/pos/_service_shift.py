"""Shift + cash-drawer + pharmacist-PIN mixin for :class:`PosService`.

Owns the cashier-shift lifecycle (open, close-with-variance, listing), the
mid-shift cash-drawer events, and pharmacist PIN verification that issues a
short-lived token for controlled-substance dispensing.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from datapulse.logging import get_logger
from datapulse.pos._service_helpers import to_decimal
from datapulse.pos.exceptions import PharmacistVerificationRequiredError, PosError
from datapulse.pos.models import (
    CashDrawerEventResponse,
    PharmacistVerifyResponse,
    ShiftRecord,
    ShiftSummaryResponse,
)
from datapulse.pos.pharmacist_verifier import TOKEN_TTL_SECONDS

if TYPE_CHECKING:
    from datapulse.pos.pharmacist_verifier import PharmacistVerifier
    from datapulse.pos.repository import PosRepository

log = get_logger(__name__)


class ShiftCashMixin:
    """Mixin providing shift, cash-drawer, and pharmacist-PIN verification.

    Requires ``self._repo`` and ``self._verifier`` to be set by
    :meth:`PosService.__init__`.
    """

    _repo: PosRepository
    _verifier: PharmacistVerifier | None

    def start_shift(
        self,
        *,
        terminal_id: int,
        tenant_id: int,
        staff_id: str,
        opening_cash: Decimal = Decimal("0"),
    ) -> ShiftRecord:
        """Open a new cashier shift for a terminal.

        Raises :class:`PosError` if the terminal already has an open shift —
        the current shift must be closed before starting a new one.
        """
        existing = self._repo.get_current_shift(terminal_id)
        if existing is not None:
            raise PosError(
                message=(
                    f"Terminal {terminal_id} already has an open shift "
                    f"(shift_id={existing['id']}). Close it before starting a new one."
                ),
                detail=f"terminal_id={terminal_id} shift_id={existing['id']}",
            )

        now = datetime.now(tz=UTC)
        row = self._repo.create_shift_record(
            terminal_id=terminal_id,
            tenant_id=tenant_id,
            staff_id=staff_id,
            shift_date=now.date(),
            opened_at=now,
            opening_cash=opening_cash,
        )
        log.info("pos.shift.started", shift_id=row["id"], terminal_id=terminal_id)
        return ShiftRecord.model_validate(row)

    def close_shift(
        self,
        *,
        shift_id: int,
        closing_cash: Decimal,
    ) -> ShiftSummaryResponse:
        """Close a shift — computes expected cash and variance from drawer events.

        ``expected_cash`` = opening + cash_sales + floats_in - cash_refunds - pickups.
        ``variance`` = closing_cash - expected_cash (positive = over, negative = short).
        """
        from datapulse.pos.terminal import compute_expected_cash, compute_variance

        shift = self._repo.get_shift_by_id(shift_id)
        if shift is None:
            raise PosError(
                message=f"Shift {shift_id} not found",
                detail=f"shift_id={shift_id}",
            )
        if shift.get("closed_at") is not None:
            raise PosError(
                message=f"Shift {shift_id} is already closed",
                detail=f"shift_id={shift_id}",
            )

        # Aggregate cash drawer events since shift opened
        shift_opened = shift["opened_at"]
        cash_events = self._repo.get_cash_events(int(shift["terminal_id"]), limit=10000)
        events_in_shift = [e for e in cash_events if e["timestamp"] >= shift_opened]

        cash_sales = sum(
            (to_decimal(e["amount"]) for e in events_in_shift if e["event_type"] == "sale"),
            start=Decimal("0"),
        )
        cash_refunds = sum(
            (to_decimal(e["amount"]) for e in events_in_shift if e["event_type"] == "refund"),
            start=Decimal("0"),
        )
        floats_in = sum(
            (to_decimal(e["amount"]) for e in events_in_shift if e["event_type"] == "float"),
            start=Decimal("0"),
        )
        pickups = sum(
            (to_decimal(e["amount"]) for e in events_in_shift if e["event_type"] == "pickup"),
            start=Decimal("0"),
        )

        expected = compute_expected_cash(
            opening_cash=to_decimal(shift["opening_cash"]),
            cash_sales=cash_sales,
            cash_refunds=cash_refunds,
            floats_in=floats_in,
            pickups=pickups,
        )
        variance = compute_variance(
            opening_cash=to_decimal(shift["opening_cash"]),
            closing_cash=closing_cash,
            expected_cash=expected,
        )

        now = datetime.now(tz=UTC)
        updated = self._repo.update_shift_record(
            shift_id,
            closing_cash=closing_cash,
            expected_cash=expected,
            variance=variance,
            closed_at=now,
        )
        if updated is None:
            raise PosError(
                message=f"Failed to close shift {shift_id}",
                detail=f"shift_id={shift_id}",
            )

        summary_data = self._repo.get_shift_summary_data(
            int(shift["terminal_id"]),
            opened_at=shift_opened,
            closed_at=now,
        )

        log.info(
            "pos.shift.closed",
            shift_id=shift_id,
            closing_cash=str(closing_cash),
            expected_cash=str(expected),
            variance=str(variance),
        )
        return ShiftSummaryResponse.model_validate(
            {
                **updated,
                "transaction_count": summary_data.get("transaction_count", 0),
                "total_sales": summary_data.get("total_sales", Decimal("0")),
            }
        )

    def get_current_shift(self, terminal_id: int) -> ShiftRecord | None:
        """Return the currently open shift for a terminal (None if no open shift)."""
        row = self._repo.get_current_shift(terminal_id)
        return ShiftRecord.model_validate(row) if row else None

    def get_shift_by_id(self, shift_id: int) -> ShiftRecord | None:
        """Return a shift by its primary key (None if not found)."""
        row = self._repo.get_shift_by_id(shift_id)
        return ShiftRecord.model_validate(row) if row else None

    def list_shifts(
        self,
        tenant_id: int,
        *,
        terminal_id: int | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> list[ShiftRecord]:
        """List shift records for a tenant, most recent first."""
        rows = self._repo.list_shifts(
            tenant_id,
            terminal_id=terminal_id,
            limit=limit,
            offset=offset,
        )
        return [ShiftRecord.model_validate(r) for r in rows]

    def record_cash_event(
        self,
        *,
        terminal_id: int,
        tenant_id: int,
        event_type: str,
        amount: Decimal,
        reference_id: str | None = None,
    ) -> CashDrawerEventResponse:
        """Record a mid-shift cash drawer event (float, pickup, refund, sale)."""
        row = self._repo.record_cash_event(
            terminal_id=terminal_id,
            tenant_id=tenant_id,
            event_type=event_type,
            amount=amount,
            reference_id=reference_id,
        )
        return CashDrawerEventResponse.model_validate(row)

    def get_cash_events(
        self,
        terminal_id: int,
        *,
        limit: int = 100,
    ) -> list[CashDrawerEventResponse]:
        """Return cash drawer events for a terminal, most recent first."""
        rows = self._repo.get_cash_events(terminal_id, limit=limit)
        return [CashDrawerEventResponse.model_validate(r) for r in rows]

    def verify_pharmacist_pin(
        self,
        *,
        pharmacist_id: str,
        credential: str,
        drug_code: str,
    ) -> PharmacistVerifyResponse:
        """Validate a pharmacist PIN and return a short-lived verification token.

        The token encodes ``pharmacist_id`` + ``drug_code`` + timestamp, signed
        with the application secret key. Pass it as ``pharmacist_id`` in a
        subsequent ``add_item`` call to authorise the controlled-substance
        dispensing without repeating the PIN check.

        Raises
        ------
        PharmacistVerificationRequiredError
            When the credential is wrong, the user has no PIN registered,
            or no ``PharmacistVerifier`` was injected (configuration error).
        """
        if self._verifier is None:
            raise PharmacistVerificationRequiredError(
                drug_code=drug_code,
                message="Pharmacist verification is not configured on this server.",
            )

        token = self._verifier.verify_and_issue(
            pharmacist_id=pharmacist_id,
            credential=credential,
            drug_code=drug_code,
        )

        expires_at = datetime.now(tz=UTC).replace(microsecond=0) + timedelta(
            seconds=TOKEN_TTL_SECONDS
        )

        return PharmacistVerifyResponse(
            token=token,
            pharmacist_id=pharmacist_id,
            drug_code=drug_code,
            expires_at=expires_at,
        )

"""POS customer lookup models — phone-keyed customer + churn signal (#624)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from datapulse.types import JsonDecimal


class LateRefillItem(BaseModel):
    """One overdue-refill line shown on the churn alert card."""

    model_config = ConfigDict(frozen=True)

    drug_name: str
    days_late: int


class PosCustomerChurn(BaseModel):
    """Per-customer churn signal returned by the POS customer lookup."""

    model_config = ConfigDict(frozen=True)

    risk: bool
    last_refill_due: date | None = None
    late_refills: list[LateRefillItem] = Field(default_factory=list)


class PosCustomerLookup(BaseModel):
    """Result of ``GET /pos/customers/by-phone/{phone}``.

    ``loyalty_points`` / ``loyalty_tier`` / ``outstanding_credit_egp`` are part
    of the frontend contract but are stubbed to neutral defaults (``0`` /
    ``None``) until the loyalty + credit tables land. Keeping them in the
    response shape means the UI can ship against the final contract today
    and light up additional fields without an API change (#624).
    """

    model_config = ConfigDict(frozen=True)

    customer_key: int
    customer_name: str
    phone: str
    loyalty_points: int = 0
    loyalty_tier: str | None = None
    vip_since: date | None = None
    outstanding_credit_egp: JsonDecimal
    churn: PosCustomerChurn

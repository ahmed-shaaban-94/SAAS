"""POS customer lookup — phone → customer + churn signal (#624).

Kept separate from :class:`PosService` to avoid bloating the already-composed
POS service surface. The lookup joins three sources:

* ``pos.customer_contact``         — phone → customer_key (POS-owned)
* ``public_marts.dim_customer``    — customer_key → customer_name (dbt)
* ``public_marts.feat_churn_prediction`` via :class:`ChurnRepositoryProtocol` — churn signal

Loyalty + credit fields are stubbed until those tables land; see the
`PosCustomerLookup` model for the contract.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Protocol

from datapulse.logging import get_logger
from datapulse.pos.models.customer import (
    LateRefillItem,
    PosCustomerChurn,
    PosCustomerLookup,
)
from datapulse.pos.phone import normalize_egyptian_phone

if TYPE_CHECKING:
    from datapulse.pos.customer_contact_repository import CustomerContactRepository

log = get_logger(__name__)

# A customer is "at risk" when their churn probability exceeds this threshold.
# Kept as a module constant (not a setting) because the frontend treats the
# `risk` boolean as the single source of truth; flipping the threshold later
# only requires changing one literal here.
_CHURN_RISK_THRESHOLD = 0.60


class ChurnRepositoryProtocol(Protocol):
    """Minimal interface the POS service needs from the churn data source.

    Defines only what is actually consumed here so the POS module does not
    take a hard dependency on the full analytics.ChurnRepository surface.
    """

    def get_by_customer_key(self, customer_key: int) -> dict | None: ...


class CustomerLookupService:
    """Service for the ``GET /pos/customers/by-phone/{phone}`` endpoint."""

    def __init__(
        self,
        contact_repo: CustomerContactRepository,
        churn_repo: ChurnRepositoryProtocol,
    ) -> None:
        self._contact_repo = contact_repo
        self._churn_repo = churn_repo

    def lookup_by_phone(self, raw_phone: str) -> PosCustomerLookup | None:
        """Return the customer matching ``raw_phone``, or ``None`` when unknown.

        ``raw_phone`` may be in any of the three Egyptian mobile shapes;
        normalisation happens here so callers don't have to pre-canonicalise.
        Returns ``None`` for invalid phone shapes as well as for canonical
        phones with no customer on file — the route layer turns both into 404.
        """
        phone_e164 = normalize_egyptian_phone(raw_phone)
        if phone_e164 is None:
            return None

        row = self._contact_repo.find_by_phone(phone_e164)
        if row is None:
            return None

        churn = self._build_churn_signal(int(row["customer_key"]))
        return PosCustomerLookup(
            customer_key=int(row["customer_key"]),
            customer_name=row["customer_name"],
            phone=row["phone_e164"],
            loyalty_points=0,
            loyalty_tier=None,
            vip_since=None,
            outstanding_credit_egp=Decimal("0"),
            churn=churn,
        )

    def _build_churn_signal(self, customer_key: int) -> PosCustomerChurn:
        """Assemble the churn sub-payload for a customer.

        The late-refill heuristic (``last_purchase_date + typical_cycle_days``)
        is noted in the issue as a follow-up; for now we surface the risk
        boolean from ``feat_churn_prediction`` and leave ``late_refills``
        empty so the UI reserves the red alert card for true risk cases.
        """
        churn_row = self._churn_repo.get_by_customer_key(customer_key)
        if churn_row is None:
            return PosCustomerChurn(risk=False, last_refill_due=None, late_refills=[])

        probability = churn_row.get("churn_probability", 0)
        at_risk = float(probability) >= _CHURN_RISK_THRESHOLD

        late_refills: list[LateRefillItem] = []
        return PosCustomerChurn(
            risk=at_risk,
            last_refill_due=None,
            late_refills=late_refills,
        )

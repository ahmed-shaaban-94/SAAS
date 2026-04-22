"""Business logic layer for reseller management."""

from __future__ import annotations

from decimal import Decimal

from datapulse.logging import get_logger
from datapulse.reseller.models import (
    CommissionResponse,
    PayoutResponse,
    ResellerCreate,
    ResellerDashboard,
    ResellerResponse,
    ResellerTenantResponse,
)
from datapulse.reseller.repository import ResellerRepository

log = get_logger(__name__)

_ZERO = Decimal("0")


class ResellerService:
    """Orchestrates reseller operations."""

    def __init__(self, repo: ResellerRepository) -> None:
        self._repo = repo

    def create_reseller(self, data: ResellerCreate) -> ResellerResponse:
        """Create a new reseller partner."""
        log.info("service_create_reseller", name=data.name)
        return self._repo.create_reseller(data)

    def get_reseller(self, reseller_id: int) -> ResellerResponse:
        """Get a reseller by ID."""
        reseller = self._repo.get_reseller(reseller_id)
        if reseller is None:
            raise ValueError(f"Reseller {reseller_id} not found")
        return reseller

    def list_resellers(self) -> list[ResellerResponse]:
        """List all resellers."""
        return self._repo.list_resellers()

    def get_dashboard(self, reseller_id: int) -> ResellerDashboard:
        """Build reseller dashboard overview."""
        log.info("get_reseller_dashboard", reseller_id=reseller_id)
        reseller = self.get_reseller(reseller_id)
        tenants = self._repo.get_reseller_tenants(reseller_id)
        commissions = self._repo.get_commissions(reseller_id)
        pending = self._repo.get_pending_payout_total(reseller_id)

        total_mrr = sum((c.mrr_amount for c in commissions), _ZERO)
        total_comm = sum((c.commission_amount for c in commissions), _ZERO)

        return ResellerDashboard(
            reseller=reseller,
            tenants=tenants,
            total_mrr=total_mrr,
            total_commissions=total_comm,
            pending_payout=pending,
        )

    def get_tenants(self, reseller_id: int) -> list[ResellerTenantResponse]:
        """Get tenants under a reseller."""
        return self._repo.get_reseller_tenants(reseller_id)

    def get_commissions(self, reseller_id: int) -> list[CommissionResponse]:
        """Get commission history."""
        return self._repo.get_commissions(reseller_id)

    def get_payouts(self, reseller_id: int) -> list[PayoutResponse]:
        """Get payout history."""
        return self._repo.get_payouts(reseller_id)

    def tenant_belongs_to_reseller(self, tenant_id: int, reseller_id: int) -> bool:
        """Check whether the given tenant is linked to the given reseller."""
        return self._repo.tenant_belongs_to_reseller(tenant_id, reseller_id)

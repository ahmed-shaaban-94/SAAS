"""Repository for reseller management — raw SQL via SQLAlchemy text()."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger
from datapulse.reseller.models import (
    CommissionResponse,
    PayoutResponse,
    ResellerCreate,
    ResellerResponse,
    ResellerTenantResponse,
)

log = get_logger(__name__)

_ZERO = Decimal("0")


class ResellerRepository:
    """Data-access layer for reseller operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_reseller(self, data: ResellerCreate) -> ResellerResponse:
        """Create a new reseller partner."""
        log.info("create_reseller", name=data.name)
        row = (
            self._session.execute(
                text("""
                INSERT INTO public.resellers (name, contact_email, contact_name, commission_pct)
                VALUES (:name, :email, :cname, :cpct)
                RETURNING reseller_id, name, contact_email, contact_name, commission_pct,
                          stripe_connect_id, is_active, created_at, updated_at
            """),
                {
                    "name": data.name,
                    "email": data.contact_email,
                    "cname": data.contact_name,
                    "cpct": data.commission_pct,
                },
            )
            .mappings()
            .fetchone()
        )
        assert row is not None, "INSERT ... RETURNING must return a row"
        return ResellerResponse(**dict(row), tenant_count=0)

    def get_reseller(self, reseller_id: int) -> ResellerResponse | None:
        """Get a reseller by ID with tenant count."""
        row = (
            self._session.execute(
                text("""
                SELECT r.reseller_id, r.name, r.contact_email, r.contact_name,
                       r.commission_pct, r.stripe_connect_id, r.is_active,
                       r.created_at, r.updated_at,
                       COUNT(t.tenant_id) AS tenant_count
                FROM public.resellers r
                LEFT JOIN bronze.tenants t ON t.reseller_id = r.reseller_id
                WHERE r.reseller_id = :rid
                GROUP BY r.reseller_id
            """),
                {"rid": reseller_id},
            )
            .mappings()
            .fetchone()
        )
        if row is None:
            return None
        return ResellerResponse(**row)

    def list_resellers(self) -> list[ResellerResponse]:
        """List all resellers."""
        rows = (
            self._session.execute(
                text("""
                SELECT r.reseller_id, r.name, r.contact_email, r.contact_name,
                       r.commission_pct, r.stripe_connect_id, r.is_active,
                       r.created_at, r.updated_at,
                       COUNT(t.tenant_id) AS tenant_count
                FROM public.resellers r
                LEFT JOIN bronze.tenants t ON t.reseller_id = r.reseller_id
                GROUP BY r.reseller_id
                ORDER BY r.name
            """),
            )
            .mappings()
            .fetchall()
        )
        return [ResellerResponse(**r) for r in rows]

    def get_reseller_tenants(self, reseller_id: int) -> list[ResellerTenantResponse]:
        """Get all tenants under a reseller."""
        rows = (
            self._session.execute(
                text("""
                SELECT t.tenant_id, t.tenant_name, t.plan
                FROM bronze.tenants t
                WHERE t.reseller_id = :rid
                ORDER BY t.tenant_name
            """),
                {"rid": reseller_id},
            )
            .mappings()
            .fetchall()
        )
        return [ResellerTenantResponse(**r) for r in rows]

    def get_commissions(self, reseller_id: int) -> list[CommissionResponse]:
        """Get commission history for a reseller."""
        rows = (
            self._session.execute(
                text("""
                SELECT rc.id, rc.reseller_id, rc.tenant_id,
                       COALESCE(t.tenant_name, '') AS tenant_name,
                       rc.period, rc.mrr_amount, rc.commission_amount,
                       rc.commission_pct, rc.status
                FROM public.reseller_commissions rc
                LEFT JOIN bronze.tenants t ON t.tenant_id = rc.tenant_id
                WHERE rc.reseller_id = :rid
                ORDER BY rc.period DESC, rc.tenant_id
            """),
                {"rid": reseller_id},
            )
            .mappings()
            .fetchall()
        )
        return [CommissionResponse(**r) for r in rows]

    def get_payouts(self, reseller_id: int) -> list[PayoutResponse]:
        """Get payout history for a reseller."""
        rows = (
            self._session.execute(
                text("""
                SELECT id, reseller_id, amount, currency, stripe_transfer_id,
                       status, period_from, period_to, created_at
                FROM public.reseller_payouts
                WHERE reseller_id = :rid
                ORDER BY created_at DESC
            """),
                {"rid": reseller_id},
            )
            .mappings()
            .fetchall()
        )
        return [PayoutResponse(**r) for r in rows]

    def tenant_belongs_to_reseller(self, tenant_id: int, reseller_id: int) -> bool:
        """Return True if the given tenant is associated with this reseller."""
        row = self._session.execute(
            text(
                "SELECT 1 FROM bronze.tenants WHERE tenant_id = :tid AND reseller_id = :rid"
            ),
            {"tid": tenant_id, "rid": reseller_id},
        ).fetchone()
        return row is not None

    def get_pending_payout_total(self, reseller_id: int) -> Decimal:
        """Get total pending commission amount."""
        row = self._session.execute(
            text("""
                SELECT COALESCE(SUM(commission_amount), 0) AS total
                FROM public.reseller_commissions
                WHERE reseller_id = :rid AND status = 'pending'
            """),
            {"rid": reseller_id},
        ).fetchone()
        return Decimal(str(row[0])) if row else _ZERO

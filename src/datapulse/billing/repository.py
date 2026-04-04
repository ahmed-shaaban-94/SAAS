"""SQLAlchemy CRUD for subscriptions and usage_metrics tables."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = structlog.get_logger()


class BillingRepository:
    """Data access for billing-related tables."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Tenant billing columns ──────────────────────────────────

    def get_tenant_plan(self, tenant_id: int) -> str:
        row = self._session.execute(
            text("SELECT plan FROM bronze.tenants WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        ).fetchone()
        return row[0] if row else "starter"

    def get_stripe_customer_id(self, tenant_id: int) -> str | None:
        row = self._session.execute(
            text("SELECT stripe_customer_id FROM bronze.tenants WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        ).fetchone()
        return row[0] if row else None

    def set_stripe_customer_id(self, tenant_id: int, customer_id: str) -> None:
        self._session.execute(
            text(
                "UPDATE bronze.tenants SET stripe_customer_id = :cid WHERE tenant_id = :tid"
            ),
            {"cid": customer_id, "tid": tenant_id},
        )

    def update_tenant_plan(self, tenant_id: int, plan: str) -> None:
        self._session.execute(
            text("UPDATE bronze.tenants SET plan = :plan WHERE tenant_id = :tid"),
            {"plan": plan, "tid": tenant_id},
        )
        logger.info("tenant_plan_updated", tenant_id=tenant_id, plan=plan)

    def get_tenant_by_stripe_customer(self, stripe_customer_id: str) -> int | None:
        row = self._session.execute(
            text(
                "SELECT tenant_id FROM bronze.tenants WHERE stripe_customer_id = :cid"
            ),
            {"cid": stripe_customer_id},
        ).fetchone()
        return row[0] if row else None

    # ── Subscriptions ───────────────────────────────────────────

    def upsert_subscription(
        self,
        *,
        tenant_id: int,
        stripe_subscription_id: str,
        stripe_price_id: str,
        status: str,
        current_period_start: datetime | None = None,
        current_period_end: datetime | None = None,
        cancel_at_period_end: bool = False,
    ) -> None:
        now = datetime.now(UTC)
        existing = self._session.execute(
            text(
                "SELECT id FROM public.subscriptions "
                "WHERE stripe_subscription_id = :sid"
            ),
            {"sid": stripe_subscription_id},
        ).fetchone()

        if existing:
            self._session.execute(
                text(
                    "UPDATE public.subscriptions SET "
                    "stripe_price_id = :price, status = :status, "
                    "current_period_start = :ps, current_period_end = :pe, "
                    "cancel_at_period_end = :cap, updated_at = :now "
                    "WHERE stripe_subscription_id = :sid"
                ),
                {
                    "price": stripe_price_id,
                    "status": status,
                    "ps": current_period_start,
                    "pe": current_period_end,
                    "cap": cancel_at_period_end,
                    "now": now,
                    "sid": stripe_subscription_id,
                },
            )
        else:
            self._session.execute(
                text(
                    "INSERT INTO public.subscriptions "
                    "(tenant_id, stripe_subscription_id, stripe_price_id, status, "
                    "current_period_start, current_period_end, cancel_at_period_end, "
                    "created_at, updated_at) "
                    "VALUES (:tid, :sid, :price, :status, :ps, :pe, :cap, :now, :now)"
                ),
                {
                    "tid": tenant_id,
                    "sid": stripe_subscription_id,
                    "price": stripe_price_id,
                    "status": status,
                    "ps": current_period_start,
                    "pe": current_period_end,
                    "cap": cancel_at_period_end,
                    "now": now,
                },
            )

    def get_active_subscription(self, tenant_id: int) -> dict | None:
        row = self._session.execute(
            text(
                "SELECT stripe_subscription_id, stripe_price_id, status, "
                "current_period_start, current_period_end, cancel_at_period_end "
                "FROM public.subscriptions "
                "WHERE tenant_id = :tid AND status IN ('active', 'trialing', 'past_due') "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": tenant_id},
        ).fetchone()
        if not row:
            return None
        return {
            "stripe_subscription_id": row[0],
            "stripe_price_id": row[1],
            "status": row[2],
            "current_period_start": row[3],
            "current_period_end": row[4],
            "cancel_at_period_end": row[5],
        }

    # ── Usage metrics ───────────────────────────────────────────

    def get_usage(self, tenant_id: int) -> dict:
        row = self._session.execute(
            text(
                "SELECT data_sources_count, total_rows FROM public.usage_metrics "
                "WHERE tenant_id = :tid"
            ),
            {"tid": tenant_id},
        ).fetchone()
        if not row:
            return {"data_sources_count": 0, "total_rows": 0}
        return {"data_sources_count": row[0], "total_rows": row[1]}

    def upsert_usage(
        self,
        tenant_id: int,
        *,
        data_sources_count: int | None = None,
        total_rows: int | None = None,
    ) -> None:
        now = datetime.now(UTC)
        existing = self._session.execute(
            text("SELECT id FROM public.usage_metrics WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        ).fetchone()

        if existing:
            updates = []
            params: dict = {"tid": tenant_id, "now": now}
            if data_sources_count is not None:
                updates.append("data_sources_count = :dsc")
                params["dsc"] = data_sources_count
            if total_rows is not None:
                updates.append("total_rows = :tr")
                params["tr"] = total_rows
            updates.append("updated_at = :now")
            self._session.execute(
                text(
                    f"UPDATE public.usage_metrics SET {', '.join(updates)}"
                    " WHERE tenant_id = :tid"
                ),
                params,
            )
        else:
            self._session.execute(
                text(
                    "INSERT INTO public.usage_metrics"
                    " (tenant_id, data_sources_count, total_rows, updated_at)"
                    " VALUES (:tid, :dsc, :tr, :now)"
                ),
                {
                    "tid": tenant_id,
                    "dsc": data_sources_count or 0,
                    "tr": total_rows or 0,
                    "now": now,
                },
            )

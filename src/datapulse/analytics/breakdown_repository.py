"""Repository for billing method and customer type breakdowns.

Queries ``agg_sales_daily`` (billing_way grain) and ``agg_sales_monthly``
(walk_in_count, insurance_count columns) to power Phase 2 charts.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.models import (
    AnalyticsFilter,
    BillingBreakdown,
    BillingBreakdownItem,
    CustomerTypeBreakdown,
    CustomerTypeBreakdownItem,
)
from datapulse.analytics.queries import SITE_DATE_ONLY, build_where
from datapulse.logging import get_logger

log = get_logger(__name__)

_ZERO = Decimal("0")


class BreakdownRepository:
    """Billing + customer-type breakdown queries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_billing_breakdown(self, filters: AnalyticsFilter) -> BillingBreakdown:
        """Return billing group distribution with returns netted against sales.

        Groups by ``dim_billing.billing_group`` (Cash, Credit, Delivery, etc.)
        instead of individual billing_way.  Net amounts already carry the sign
        (negative for returns), so SUM() naturally subtracts them.  Transaction
        counts use ``SUM(txn) - 2*SUM(ret)`` to net return invoices out.
        """
        log.info("get_billing_breakdown", filters=filters.model_dump())
        where, params = build_where(
            filters, date_column="date_key", supported_fields=SITE_DATE_ONLY
        )

        stmt = text(f"""
            SELECT db.billing_group,
                   -- Subtract 2x returns: reverses original sale + adds return txn
                   SUM(a.transaction_count) - 2 * SUM(a.return_count) AS transaction_count,
                   SUM(a.total_sales) AS total_sales
            FROM public_marts.agg_sales_daily a
            JOIN public_marts.dim_billing db ON a.billing_way = db.billing_way
            WHERE {where}
            GROUP BY db.billing_group
            ORDER BY total_sales DESC
        """)
        rows = self._session.execute(stmt, params).fetchall()

        if not rows:
            return BillingBreakdown(items=[], total_transactions=0, total_net_amount=_ZERO)

        raw = [(str(r[0]), int(r[1]), Decimal(str(r[2]))) for r in rows]
        grand_total = sum((v for _, _, v in raw), _ZERO)
        if grand_total <= 0:
            grand_total = Decimal("1")  # fallback: net-negative period
        total_txn = sum(c for _, c, _ in raw)

        items = [
            BillingBreakdownItem(
                billing_group=name,
                transaction_count=count,
                total_net_amount=amount,
                pct_of_total=(amount / grand_total * 100).quantize(Decimal("0.01")),
            )
            for name, count, amount in raw
        ]

        return BillingBreakdown(
            items=items,
            total_transactions=total_txn,
            total_net_amount=grand_total,
        )

    def get_customer_type_breakdown(self, filters: AnalyticsFilter) -> CustomerTypeBreakdown:
        """Return walk-in vs insurance vs other distribution by month."""
        log.info("get_customer_type_breakdown", filters=filters.model_dump())
        where, params = build_where(filters, use_year_month=True, supported_fields=SITE_DATE_ONLY)

        stmt = text(f"""
            SELECT LPAD(year::text, 4, '0') || '-'
                   || LPAD(month::text, 2, '0') AS period,
                   SUM(walk_in_count)     AS walk_in_count,
                   SUM(insurance_count)   AS insurance_count,
                   SUM(transaction_count) AS total_count
            FROM public_marts.agg_sales_monthly
            WHERE {where}
            GROUP BY year, month
            ORDER BY year, month
        """)
        rows = self._session.execute(stmt, params).fetchall()

        items = [
            CustomerTypeBreakdownItem(
                period=str(r[0]),
                walk_in_count=int(r[1]),
                insurance_count=int(r[2]),
                other_count=max(int(r[3]) - int(r[1]) - int(r[2]), 0),
                total_count=int(r[3]),
            )
            for r in rows
        ]

        return CustomerTypeBreakdown(items=items)

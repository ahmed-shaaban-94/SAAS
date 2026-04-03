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
        """Return billing method distribution with returns subtracted from their parent group.

        Return billing types (e.g. 'Cash Return') are mapped back to
        their parent type ('Cash') and their amounts/counts are subtracted
        so the pie chart shows a clean net-of-returns picture.
        """
        log.info("get_billing_breakdown", filters=filters.model_dump())
        where, params = build_where(
            filters, date_column="date_key", supported_fields=SITE_DATE_ONLY
        )

        # Map return billing_ways to parent, then aggregate net amounts.
        # Returns have positive net_amount in fct_sales, so we subtract them.
        stmt = text(f"""
            WITH raw AS (
                SELECT
                    CASE
                        WHEN billing_way LIKE '%% Return' THEN REPLACE(billing_way, ' Return', '')
                        ELSE billing_way
                    END AS base_billing_way,
                    CASE WHEN billing_way LIKE '%% Return' THEN TRUE ELSE FALSE END AS is_return_type,
                    SUM(transaction_count) AS txn_count,
                    SUM(return_count)      AS ret_count,
                    SUM(total_net_amount)  AS net_amount
                FROM public_marts.agg_sales_daily
                WHERE {where}
                GROUP BY 1, 2
            )
            SELECT
                base_billing_way,
                SUM(CASE WHEN NOT is_return_type THEN txn_count ELSE 0 END)
                  - SUM(CASE WHEN is_return_type THEN txn_count ELSE 0 END) AS transaction_count,
                SUM(CASE WHEN NOT is_return_type THEN net_amount ELSE 0 END)
                  - SUM(CASE WHEN is_return_type THEN net_amount ELSE 0 END) AS total_net_amount
            FROM raw
            GROUP BY base_billing_way
            HAVING SUM(CASE WHEN NOT is_return_type THEN net_amount ELSE 0 END)
                     - SUM(CASE WHEN is_return_type THEN net_amount ELSE 0 END) > 0
            ORDER BY total_net_amount DESC
        """)
        rows = self._session.execute(stmt, params).fetchall()

        if not rows:
            return BillingBreakdown(items=[], total_transactions=0, total_net_amount=_ZERO)

        raw = [(str(r[0]), int(r[1]), Decimal(str(r[2]))) for r in rows]
        grand_total = sum(v for _, _, v in raw) or Decimal("1")
        total_txn = sum(c for _, c, _ in raw)

        items = [
            BillingBreakdownItem(
                billing_way=name,
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
                other_count=int(r[3]) - int(r[1]) - int(r[2]),
                total_count=int(r[3]),
            )
            for r in rows
        ]

        return CustomerTypeBreakdown(items=items)

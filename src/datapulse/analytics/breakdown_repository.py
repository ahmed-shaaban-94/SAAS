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
    ChannelsBreakdown,
    ChannelShare,
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

    def get_channels_breakdown(self, filters: AnalyticsFilter) -> ChannelsBreakdown:
        """Tenant-aggregate revenue distribution across sales channels (#505).

        The raw data does not capture a true sales-channel dimension —
        ``wholesale`` and ``online`` segments will be zero-valued with
        ``source='unavailable'`` until upstream ingestion lands.
        ``retail`` and ``institution`` are derived from
        ``fct_sales.is_walk_in`` / ``has_insurance`` flags:

            retail walk-in = is_walk_in
            institution    = has_insurance AND NOT is_walk_in
            (other revenue is folded back into retail walk-in so the
             known donut sums to the total — wholesale/online stay 0.)
        """
        log.info("get_channels_breakdown", filters=filters.model_dump())

        # fct_sales has all standard dimension columns via joined dims,
        # but only supports site/date-only at the fact level.
        where, params = build_where(
            filters, date_column="date_key", supported_fields=SITE_DATE_ONLY
        )

        stmt = text(f"""
            SELECT
                COALESCE(SUM(
                    f.sales * (CASE WHEN f.is_walk_in THEN 1 ELSE 0 END)
                ), 0) AS retail_egp,
                COALESCE(SUM(
                    f.sales * (
                        CASE
                            WHEN f.has_insurance AND NOT f.is_walk_in THEN 1
                            ELSE 0
                        END
                    )
                ), 0) AS institution_egp,
                COALESCE(SUM(f.sales), 0) AS total_egp
            FROM public_marts.fct_sales f
            WHERE {where}
              AND NOT f.is_return
        """)  # noqa: S608

        row = self._session.execute(stmt, params).mappings().fetchone()
        retail = Decimal(str(row["retail_egp"])) if row else _ZERO
        institution = Decimal(str(row["institution_egp"])) if row else _ZERO
        total = Decimal(str(row["total_egp"])) if row else _ZERO

        # Fold "other" revenue (neither walk-in nor insurance) back into
        # retail walk-in so the three known segments cover the tenant
        # total without exposing an "unknown" bucket to end users.
        other = total - retail - institution
        if other > _ZERO:
            retail = retail + other

        def _pct(value: Decimal) -> Decimal:
            if total == _ZERO:
                return _ZERO
            return (value / total * 100).quantize(Decimal("0.01"))

        items = [
            ChannelShare(
                channel="retail",
                label="Retail walk-in",
                value_egp=retail,
                pct_of_total=_pct(retail),
                source="derived",
            ),
            ChannelShare(
                channel="wholesale",
                label="Wholesale",
                value_egp=_ZERO,
                pct_of_total=_ZERO,
                source="unavailable",
            ),
            ChannelShare(
                channel="institution",
                label="Institution",
                value_egp=institution,
                pct_of_total=_pct(institution),
                source="derived",
            ),
            ChannelShare(
                channel="online",
                label="Online",
                value_egp=_ZERO,
                pct_of_total=_ZERO,
                source="unavailable",
            ),
        ]

        coverage = "partial"  # wholesale + online always unavailable for now
        return ChannelsBreakdown(items=items, total_egp=total, data_coverage=coverage)

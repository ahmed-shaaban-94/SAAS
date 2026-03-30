"""Read-only repository for entity detail queries (product, customer, staff).

Extracted from ``AnalyticsRepository`` to keep individual modules under the
400-line convention.  Follows the same pattern: takes a SQLAlchemy session
in ``__init__`` and uses parameterized ``text()`` queries.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.models import (
    CustomerAnalytics,
    ProductPerformance,
    StaffPerformance,
)
from datapulse.logging import get_logger

log = get_logger(__name__)


class DetailRepository:
    """Detail queries for individual products, customers, and staff."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_product_detail(self, product_key: int) -> ProductPerformance | None:
        """Return detailed performance for a single product."""
        log.info("get_product_detail", product_key=product_key)

        stmt = text("""
            SELECT
                a.product_key,
                p.drug_code,
                p.drug_name,
                p.drug_brand,
                p.drug_category,
                SUM(a.total_quantity)        AS total_quantity,
                SUM(a.total_sales)           AS total_sales,
                SUM(a.total_net_amount)      AS total_net_amount,
                COALESCE(
                    SUM(a.return_count)::NUMERIC
                    / NULLIF(SUM(a.transaction_count), 0), 0
                )                            AS return_rate,
                -- NOTE: SUM(unique_customers) across monthly aggregates is an
                -- approximation — customers active in multiple months are counted
                -- multiple times. A precise COUNT(DISTINCT) is not possible from
                -- pre-aggregated data without access to the fact table.
                SUM(a.unique_customers)      AS unique_customers
            FROM public_marts.agg_sales_by_product a
            INNER JOIN public_marts.dim_product p
                ON a.product_key = p.product_key
            WHERE a.product_key = :product_key
            GROUP BY a.product_key, p.drug_code, p.drug_name,
                     p.drug_brand, p.drug_category
        """)
        row = self._session.execute(stmt, {"product_key": product_key}).fetchone()
        if row is None:
            return None

        return ProductPerformance(
            product_key=int(row[0]),
            drug_code=str(row[1]),
            drug_name=str(row[2]),
            drug_brand=str(row[3]),
            drug_category=str(row[4]),
            total_quantity=Decimal(str(row[5])),
            total_sales=Decimal(str(row[6])),
            total_net_amount=Decimal(str(row[7])),
            return_rate=Decimal(str(row[8])),
            unique_customers=int(row[9]),
        )

    def get_customer_detail(self, customer_key: int) -> CustomerAnalytics | None:
        """Return detailed analytics for a single customer."""
        log.info("get_customer_detail", customer_key=customer_key)

        stmt = text("""
            SELECT
                a.customer_key,
                c.customer_id,
                c.customer_name,
                SUM(a.total_quantity)        AS total_quantity,
                SUM(a.total_net_amount)      AS total_net_amount,
                SUM(a.transaction_count)     AS transaction_count,
                -- NOTE: SUM of unique counts across months is an approximation;
                -- entities active in multiple months are counted more than once.
                SUM(a.unique_products)       AS unique_products,
                SUM(a.return_count)          AS return_count
            FROM public_marts.agg_sales_by_customer a
            INNER JOIN public_marts.dim_customer c
                ON a.customer_key = c.customer_key
            WHERE a.customer_key = :customer_key
            GROUP BY a.customer_key, c.customer_id, c.customer_name
        """)
        row = self._session.execute(stmt, {"customer_key": customer_key}).fetchone()
        if row is None:
            return None

        return CustomerAnalytics(
            customer_key=int(row[0]),
            customer_id=str(row[1]),
            customer_name=str(row[2]),
            total_quantity=Decimal(str(row[3])),
            total_net_amount=Decimal(str(row[4])),
            transaction_count=int(row[5]),
            unique_products=int(row[6]),
            return_count=int(row[7]),
        )

    def get_staff_detail(self, staff_key: int) -> StaffPerformance | None:
        """Return detailed performance for a single staff member."""
        log.info("get_staff_detail", staff_key=staff_key)

        stmt = text("""
            SELECT
                a.staff_key,
                s.staff_id,
                s.staff_name,
                s.position,
                SUM(a.total_net_amount)      AS total_net_amount,
                SUM(a.transaction_count)     AS transaction_count,
                SUM(a.total_net_amount)
                    / NULLIF(SUM(a.transaction_count), 0)
                                             AS avg_transaction_value,
                -- NOTE: SUM(unique_customers) across monthly aggregates is an
                -- approximation — customers active in multiple months are counted
                -- multiple times. Precise COUNT(DISTINCT) requires the fact table.
                SUM(a.unique_customers)      AS unique_customers
            FROM public_marts.agg_sales_by_staff a
            INNER JOIN public_marts.dim_staff s
                ON a.staff_key = s.staff_key
            WHERE a.staff_key = :staff_key
            GROUP BY a.staff_key, s.staff_id, s.staff_name, s.position
        """)
        row = self._session.execute(stmt, {"staff_key": staff_key}).fetchone()
        if row is None:
            return None

        return StaffPerformance(
            staff_key=int(row[0]),
            staff_id=str(row[1]),
            staff_name=str(row[2]),
            staff_position=str(row[3]),
            total_net_amount=Decimal(str(row[4])),
            transaction_count=int(row[5]),
            avg_transaction_value=Decimal(str(row[6])) if row[6] is not None else Decimal("0"),
            unique_customers=int(row[7]),
        )

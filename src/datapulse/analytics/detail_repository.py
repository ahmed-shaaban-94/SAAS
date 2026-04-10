"""Read-only repository for entity detail queries (product, customer, staff, site).

Extracted from ``AnalyticsRepository`` to keep individual modules under the
400-line convention.  Follows the same pattern: takes a SQLAlchemy session
in ``__init__`` and uses parameterized ``text()`` queries.
"""

from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.models import (
    CustomerAnalytics,
    ProductPerformance,
    SiteDetail,
    StaffPerformance,
    TimeSeriesPoint,
)
from datapulse.logging import get_logger

log = get_logger(__name__)


class DetailRepository:
    """Detail queries for individual products, customers, staff, and sites."""

    _ALLOWED_TABLES: frozenset[str] = frozenset(
        {
            "public_marts.agg_sales_by_product",
            "public_marts.agg_sales_by_customer",
            "public_marts.agg_sales_by_staff",
            "public_marts.agg_sales_by_site",
        }
    )

    _ALLOWED_KEY_COLS: frozenset[str] = frozenset(
        {
            "product_key",
            "customer_key",
            "staff_key",
            "site_key",
        }
    )

    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_monthly_trend(
        self,
        table: str,
        key_col: str,
        key_value: int,
    ) -> list[TimeSeriesPoint]:
        """Return monthly sales trend for a given entity."""
        if table not in self._ALLOWED_TABLES:
            raise ValueError(f"Invalid table: {table}")
        if key_col not in self._ALLOWED_KEY_COLS:
            raise ValueError(f"Invalid key column: {key_col}")
        stmt = text(f"""
            SELECT
                TO_CHAR(a.month, 'YYYY-MM') AS period,
                SUM(a.total_sales)      AS value
            FROM {table} a
            WHERE a.{key_col} = :key_value
            GROUP BY a.month
            ORDER BY a.month
        """)
        rows = self._session.execute(stmt, {"key_value": key_value}).fetchall()
        return [TimeSeriesPoint(period=str(r[0]), value=Decimal(str(r[1]))) for r in rows]

    @staticmethod
    def _parse_trend_points(raw_points) -> list[TimeSeriesPoint]:
        """Parse JSON-aggregated trend points into TimeSeriesPoint list."""
        if raw_points is None:
            return []
        if isinstance(raw_points, str):
            raw_points = json.loads(raw_points)
        return [
            TimeSeriesPoint(period=str(p["period"]), value=Decimal(str(p["value"])))
            for p in raw_points
        ]

    def get_product_detail(self, product_key: int) -> ProductPerformance | None:
        """Return detailed performance for a single product (single query)."""
        log.info("get_product_detail", product_key=product_key)

        stmt = text("""
            WITH summary AS (
                SELECT
                    a.product_key,
                    p.drug_code,
                    p.drug_name,
                    p.drug_brand,
                    p.drug_category,
                    SUM(a.total_quantity)        AS total_quantity,
                    SUM(a.total_sales)           AS total_sales,
                    COALESCE(
                        SUM(a.return_count)::NUMERIC
                        / NULLIF(SUM(a.transaction_count), 0), 0
                    )                            AS return_rate,
                    SUM(a.unique_customers)      AS unique_customers
                FROM public_marts.agg_sales_by_product a
                INNER JOIN public_marts.dim_product p
                    ON a.product_key = p.product_key
                WHERE a.product_key = :product_key
                GROUP BY a.product_key, p.drug_code, p.drug_name,
                         p.drug_brand, p.drug_category
            ),
            )
            SELECT s.*,
                (SELECT json_agg(
                    json_build_object('period', TO_CHAR(a.month, 'YYYY-MM'),
                                      'value', a.total_sales)
                    ORDER BY a.month
                )
                FROM (
                    SELECT month, SUM(total_sales) AS total_sales
                    FROM public_marts.agg_sales_by_product
                    WHERE product_key = :product_key
                    GROUP BY month
                ) a
                ) AS trend_points
            FROM summary s
        """)
        row = self._session.execute(stmt, {"product_key": product_key}).mappings().fetchone()
        if row is None:
            return None

        trend = self._parse_trend_points(row["trend_points"])

        return ProductPerformance(
            product_key=int(row["product_key"]),
            drug_code=str(row["drug_code"]),
            drug_name=str(row["drug_name"]),
            drug_brand=str(row["drug_brand"]),
            drug_category=str(row["drug_category"]),
            total_quantity=Decimal(str(row["total_quantity"])),
            total_sales=Decimal(str(row["total_sales"])),
            total_net_amount=Decimal(str(row["total_sales"])),
            return_rate=(Decimal(str(row["return_rate"])) * 100).quantize(Decimal("0.01")),
            unique_customers=int(row["unique_customers"]),
            monthly_trend=trend,
        )

    def get_customer_detail(self, customer_key: int) -> CustomerAnalytics | None:
        """Return detailed analytics for a single customer (single query)."""
        log.info("get_customer_detail", customer_key=customer_key)

        stmt = text("""
            WITH summary AS (
                SELECT
                    a.customer_key,
                    c.customer_id,
                    c.customer_name,
                    SUM(a.total_quantity)        AS total_quantity,
                    SUM(a.total_sales)           AS total_sales,
                    SUM(a.transaction_count)     AS transaction_count,
                    SUM(a.unique_products)       AS unique_products,
                    SUM(a.return_count)          AS return_count
                FROM public_marts.agg_sales_by_customer a
                INNER JOIN public_marts.dim_customer c
                    ON a.customer_key = c.customer_key
                WHERE a.customer_key = :customer_key
                GROUP BY a.customer_key, c.customer_id, c.customer_name
            ),
            )
            SELECT s.*,
                (SELECT json_agg(
                    json_build_object('period', TO_CHAR(a.month, 'YYYY-MM'),
                                      'value', a.total_sales)
                    ORDER BY a.month
                )
                FROM (
                    SELECT month, SUM(total_sales) AS total_sales
                    FROM public_marts.agg_sales_by_customer
                    WHERE customer_key = :customer_key
                    GROUP BY month
                ) a
                ) AS trend_points
            FROM summary s
        """)
        row = self._session.execute(stmt, {"customer_key": customer_key}).mappings().fetchone()
        if row is None:
            return None

        trend = self._parse_trend_points(row["trend_points"])

        return CustomerAnalytics(
            customer_key=int(row["customer_key"]),
            customer_id=str(row["customer_id"]),
            customer_name=str(row["customer_name"]),
            total_quantity=Decimal(str(row["total_quantity"])),
            total_net_amount=Decimal(str(row["total_sales"])),
            transaction_count=int(row["transaction_count"]),
            unique_products=int(row["unique_products"]),
            return_count=int(row["return_count"]),
            monthly_trend=trend,
        )

    def get_staff_detail(self, staff_key: int) -> StaffPerformance | None:
        """Return detailed performance for a single staff member (single query)."""
        log.info("get_staff_detail", staff_key=staff_key)

        stmt = text("""
            WITH summary AS (
                SELECT
                    a.staff_key,
                    s.staff_id,
                    s.staff_name,
                    s.position,
                    SUM(a.total_sales)           AS total_sales,
                    SUM(a.transaction_count)     AS transaction_count,
                    SUM(a.total_sales)
                        / NULLIF(SUM(a.transaction_count), 0)
                                                 AS avg_transaction_value,
                    SUM(a.unique_customers)      AS unique_customers
                FROM public_marts.agg_sales_by_staff a
                INNER JOIN public_marts.dim_staff s
                    ON a.staff_key = s.staff_key
                WHERE a.staff_key = :staff_key
                GROUP BY a.staff_key, s.staff_id, s.staff_name, s.position
            ),
            )
            SELECT s.*,
                (SELECT json_agg(
                    json_build_object('period', TO_CHAR(a.month, 'YYYY-MM'),
                                      'value', a.total_sales)
                    ORDER BY a.month
                )
                FROM (
                    SELECT month, SUM(total_sales) AS total_sales
                    FROM public_marts.agg_sales_by_staff
                    WHERE staff_key = :staff_key
                    GROUP BY month
                ) a
                ) AS trend_points
            FROM summary s
        """)
        row = self._session.execute(stmt, {"staff_key": staff_key}).mappings().fetchone()
        if row is None:
            return None

        trend = self._parse_trend_points(row["trend_points"])

        return StaffPerformance(
            staff_key=int(row["staff_key"]),
            staff_id=str(row["staff_id"]),
            staff_name=str(row["staff_name"]),
            staff_position=str(row["position"]),
            total_net_amount=Decimal(str(row["total_sales"])),
            transaction_count=int(row["transaction_count"]),
            avg_transaction_value=(
                Decimal(str(row["avg_transaction_value"]))
                if row["avg_transaction_value"] is not None
                else Decimal("0")
            ),
            unique_customers=int(row["unique_customers"]),
            monthly_trend=trend,
        )

    def get_site_detail(self, site_key: int) -> SiteDetail | None:
        """Return detailed metrics for a single site (single query)."""
        log.info("get_site_detail", site_key=site_key)

        stmt = text("""
            WITH summary AS (
                SELECT
                    a.site_key,
                    s.site_code,
                    s.site_name,
                    s.area_manager,
                    SUM(a.total_sales)           AS total_sales,
                    SUM(a.transaction_count)     AS transaction_count,
                    SUM(a.unique_customers)      AS unique_customers,
                    SUM(a.unique_staff)          AS unique_staff,
                    COALESCE(
                        SUM(a.walk_in_ratio * a.transaction_count)::NUMERIC
                        / NULLIF(SUM(a.transaction_count), 0), 0
                    )                            AS walk_in_ratio,
                    COALESCE(
                        SUM(a.insurance_ratio * a.transaction_count)::NUMERIC
                        / NULLIF(SUM(a.transaction_count), 0), 0
                    )                            AS insurance_ratio,
                    COALESCE(
                        SUM(a.return_count)::NUMERIC
                        / NULLIF(SUM(a.transaction_count), 0), 0
                    )                            AS return_rate
                FROM public_marts.agg_sales_by_site a
                INNER JOIN public_marts.dim_site s
                    ON a.site_key = s.site_key
                WHERE a.site_key = :site_key
                GROUP BY a.site_key, s.site_code, s.site_name, s.area_manager
            ),
            )
            SELECT s.*,
                (SELECT json_agg(
                    json_build_object('period',
                        a.year::TEXT || '-' || LPAD(a.month::TEXT, 2, '0'),
                        'value', a.total_sales)
                    ORDER BY a.year, a.month
                )
                FROM (
                    SELECT year, month, SUM(total_sales) AS total_sales
                    FROM public_marts.agg_sales_by_site
                    WHERE site_key = :site_key
                    GROUP BY year, month
                ) a
                ) AS trend_points
            FROM summary s
        """)
        row = self._session.execute(stmt, {"site_key": site_key}).mappings().fetchone()
        if row is None:
            return None

        trend = self._parse_trend_points(row["trend_points"])

        return SiteDetail(
            site_key=int(row["site_key"]),
            site_code=str(row["site_code"]) if row["site_code"] else "",
            site_name=str(row["site_name"]),
            area_manager=str(row["area_manager"]) if row["area_manager"] else "",
            total_net_amount=Decimal(str(row["total_sales"])),
            transaction_count=int(row["transaction_count"]),
            unique_customers=int(row["unique_customers"]),
            unique_staff=int(row["unique_staff"]),
            walk_in_ratio=Decimal(str(row["walk_in_ratio"])).quantize(Decimal("0.0001")),
            insurance_ratio=Decimal(str(row["insurance_ratio"])).quantize(Decimal("0.0001")),
            return_rate=(Decimal(str(row["return_rate"])) * 100).quantize(Decimal("0.01")),
            monthly_trend=trend,
        )

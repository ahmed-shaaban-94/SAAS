"""Product/customer/staff/site ranking query methods for the analytics layer."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.models import (
    AnalyticsFilter,
    RankingResult,
)
from datapulse.analytics.queries import (
    ALLOWED_RANKING_COLUMNS,
    ALLOWED_RANKING_TABLES,
    SITE_DATE_ONLY,
    build_ranking,
    build_where,
)
from datapulse.logging import get_logger

log = get_logger(__name__)


class RankingRepository:
    """Product/customer/staff/site ranking query methods."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # Dimension JOIN config for fact-table-based rankings (day-level precision).
    _DIM_JOIN: dict[str, tuple[str, str, str]] = {
        "public_marts.agg_sales_by_product": (
            "public_marts.dim_product",
            "product_key",
            "f.tenant_id = dim.tenant_id",
        ),
        "public_marts.agg_sales_by_customer": (
            "public_marts.dim_customer",
            "customer_key",
            "f.tenant_id = dim.tenant_id",
        ),
        "public_marts.agg_sales_by_staff": (
            "public_marts.dim_staff",
            "staff_key",
            "f.tenant_id = dim.tenant_id",
        ),
        "public_marts.agg_sales_by_site": (
            "public_marts.dim_site",
            "site_key",
            "f.tenant_id = dim.tenant_id",
        ),
    }

    def _get_ranking(
        self,
        table: str,
        key_col: str,
        name_col: str,
        filters: AnalyticsFilter,
        *,
        use_year_month: bool = True,
    ) -> RankingResult:
        """Top-N ranking query with day-level date precision.

        Queries fct_sales directly with date_key filtering and JOINs the
        appropriate dimension table to get the display name. This gives
        exact day-range results instead of month-level approximation.
        """
        if table not in ALLOWED_RANKING_TABLES:
            raise ValueError(f"Invalid ranking table: {table}")
        if key_col not in ALLOWED_RANKING_COLUMNS:
            raise ValueError(f"Invalid ranking key column: {key_col}")
        if name_col not in ALLOWED_RANKING_COLUMNS:
            raise ValueError(f"Invalid ranking name column: {name_col}")

        dim_table, dim_key, dim_join_cond = self._DIM_JOIN[table]
        where, params = build_where(
            filters,
            date_column="date_key",
            supported_fields=SITE_DATE_ONLY,
        )
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT f.{key_col}, dim.{name_col}, ROUND(SUM(f.sales), 2) AS value
            FROM public_marts.fct_sales f
            INNER JOIN {dim_table} dim
                ON f.{key_col} = dim.{dim_key} AND {dim_join_cond}
            WHERE {where} AND f.{key_col} != -1
            GROUP BY f.{key_col}, dim.{name_col}
            ORDER BY value DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return build_ranking(list(rows))

    def get_top_products(self, filters: AnalyticsFilter) -> RankingResult:
        """Return top-N products by net sales (excludes Services/Other origin).

        Uses fct_sales with day-level date_key filtering for exact date range precision.
        """
        log.info("get_top_products", filters=filters.model_dump())
        where, params = build_where(
            filters,
            date_column="date_key",
            supported_fields=SITE_DATE_ONLY,
        )
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT f.product_key, p.drug_brand, ROUND(SUM(f.sales), 2) AS value
            FROM public_marts.fct_sales f
            INNER JOIN public_marts.dim_product p
                ON f.product_key = p.product_key AND f.tenant_id = p.tenant_id
            WHERE {where}
              AND f.product_key != -1
              AND COALESCE(p.origin, 'Other') IN ('Pharma', 'Non-pharma', 'HVI')
            GROUP BY f.product_key, p.drug_brand
            ORDER BY value DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return build_ranking(list(rows))

    def get_origin_breakdown(self, filters: AnalyticsFilter) -> list[dict]:
        """Revenue breakdown by product origin (Pharma, Non-pharma, HVI)."""
        log.info("get_origin_breakdown", filters=filters.model_dump())
        where, params = build_where(
            filters,
            date_column="date_key",
            supported_fields=SITE_DATE_ONLY,
        )

        stmt = text(f"""
            SELECT COALESCE(p.origin, 'Other') AS origin,
                   ROUND(SUM(f.sales), 2) AS value,
                   COUNT(DISTINCT f.product_key) AS product_count
            FROM public_marts.fct_sales f
            INNER JOIN public_marts.dim_product p
                ON f.product_key = p.product_key AND f.tenant_id = p.tenant_id
            WHERE {where} AND f.product_key != -1
            GROUP BY COALESCE(p.origin, 'Other')
            ORDER BY value DESC
        """)
        rows = self._session.execute(stmt, params).fetchall()
        total = sum(Decimal(str(r[1])) for r in rows)
        return [
            {
                "origin": str(r[0]),
                "value": Decimal(str(r[1])),
                "product_count": int(r[2]),
                "pct": round(Decimal(str(r[1])) / total * 100, 2) if total else Decimal("0"),
            }
            for r in rows
        ]

    def get_top_customers(self, filters: AnalyticsFilter) -> RankingResult:
        """Return top-N customers by net sales."""
        log.info("get_top_customers", filters=filters.model_dump())
        return self._get_ranking(
            "public_marts.agg_sales_by_customer",
            "customer_key",
            "customer_name",
            filters,
        )

    def get_top_staff(self, filters: AnalyticsFilter) -> RankingResult:
        """Return top-N staff members by net sales with active_count.

        Active staff count uses 4 layers:
        1. Exclude Unknown (staff_key = -1)
        2. Exclude Services/Other origin transactions
        3. Only non-return transactions
        4. Exclude below 33% of average transaction count (data entry noise)

        'Unknown' staff are excluded from the ranking display but their
        revenue is kept in the total to avoid misleading percentages.
        """
        log.info("get_top_staff", filters=filters.model_dump())
        ranking = self._get_ranking(
            "public_marts.agg_sales_by_staff",
            "staff_key",
            "staff_name",
            filters,
        )

        # Remove 'Unknown' staff from display but keep their revenue in total
        filtered_items = [
            item.model_copy(update={"rank": idx})
            for idx, item in enumerate(
                (i for i in ranking.items if i.name != "Unknown"),
                start=1,
            )
        ]
        ranking = RankingResult(
            items=filtered_items,
            total=ranking.total,
            active_count=ranking.active_count,
        )

        # Compute active staff count with 4-layer filter
        where, params = build_where(filters, use_year_month=True)
        stmt = text(f"""
            WITH staff_txns AS (
                SELECT f.staff_key,
                       COUNT(*) FILTER (WHERE NOT f.is_return) AS sale_count
                FROM public_marts.fct_sales f
                INNER JOIN public_marts.dim_date d ON f.date_key = d.date_key
                INNER JOIN public_marts.dim_product p ON f.product_key = p.product_key
                    AND f.tenant_id = p.tenant_id
                WHERE {where}
                  AND f.staff_key != -1
                  AND COALESCE(p.origin, 'Other') IN ('Pharma', 'Non-pharma', 'HVI')
                  AND NOT f.is_return
                GROUP BY f.staff_key
            ),
            threshold AS (
                SELECT AVG(sale_count) * 0.33 AS min_txns FROM staff_txns
            )
            SELECT COUNT(*) FROM staff_txns, threshold
            WHERE sale_count >= min_txns
        """)
        row = self._session.execute(stmt, params).fetchone()
        active = int(row[0]) if row else 0

        return RankingResult(
            items=ranking.items,
            total=ranking.total,
            active_count=active,
        )

    def get_site_performance(self, filters: AnalyticsFilter) -> RankingResult:
        """Return site ranking by net sales with staff count per branch.

        The dashboard site table shows "N staff" under each branch (#507).
        We derive staff count as ``COUNT(DISTINCT staff_key)`` against
        ``fct_sales`` within the filter window — a staff member "belongs"
        to a site if they rang up at least one sale there. ``staff_key=-1``
        (Unknown) is excluded so unattributed rows don't inflate the
        headcount.
        """
        log.info("get_site_performance", filters=filters.model_dump())

        where, params = build_where(
            filters,
            date_column="date_key",
            supported_fields=SITE_DATE_ONLY,
        )
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT
                f.site_key,
                dim.site_name,
                ROUND(SUM(f.sales), 2) AS value,
                COUNT(DISTINCT f.staff_key) FILTER (
                    WHERE f.staff_key != -1
                ) AS staff_count
            FROM public_marts.fct_sales f
            INNER JOIN public_marts.dim_site dim
                ON f.site_key = dim.site_key AND f.tenant_id = dim.tenant_id
            WHERE {where} AND f.site_key != -1
            GROUP BY f.site_key, dim.site_name
            ORDER BY value DESC
            LIMIT :limit
        """)  # noqa: S608

        rows = self._session.execute(stmt, params).fetchall()
        # build_ranking expects 3-tuples (key, name, value); we have a 4th
        # column (staff_count). Tolerate 3-tuple rows from older mocks
        # / test doubles — staff_count falls back to None.
        base = build_ranking([(r[0], r[1], r[2]) for r in rows])
        enriched = [
            item.model_copy(
                update={
                    "staff_count": int(rows[idx][3]) if len(rows[idx]) > 3 else None,
                }
            )
            for idx, item in enumerate(base.items)
        ]
        return RankingResult(
            items=enriched,
            total=base.total,
            active_count=base.active_count,
        )

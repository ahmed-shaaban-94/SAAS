"""Advanced analytics repository — ABC analysis, heatmap, returns trend, segment summary."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.models import (
    ABCAnalysis,
    ABCItem,
    AnalyticsFilter,
    HeatmapCell,
    HeatmapData,
    ReturnsTrend,
    ReturnsTrendPoint,
    SegmentSummary,
)
from datapulse.analytics.queries import build_where
from datapulse.logging import get_logger

log = get_logger(__name__)
_ZERO = Decimal("0")


class AdvancedRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_abc_analysis(self, filters: AnalyticsFilter, entity: str = "product") -> ABCAnalysis:
        """ABC/Pareto analysis — uses drug_cluster for products, revenue-based for customers.

        Products with Services or Other origin are excluded.
        drug_cluster values: A, B, C, D, GT, N, Uncategorized, Unknown
        Mapped to ABC: A→A, B→B, C/D/GT/N/Uncategorized/Unknown→C
        """
        if entity == "product":
            table = "public_marts.agg_sales_by_product"
            key_col, name_col = "product_key", "drug_brand"
        else:
            table = "public_marts.agg_sales_by_customer"
            key_col, name_col = "customer_key", "customer_name"

        where, params = build_where(filters, use_year_month=True)

        if entity == "product":
            # Use drug_cluster for ABC class, exclude Services/Other origins
            stmt = text(f"""
                WITH ranked AS (
                    SELECT {key_col} AS key, {name_col} AS name,
                           SUM(total_sales) AS value,
                           MAX(drug_cluster) AS cluster
                    FROM {table}
                    WHERE {where}
                      AND COALESCE(origin, 'Other') NOT IN ('Services', 'Other')
                    GROUP BY {key_col}, {name_col}
                    HAVING SUM(total_sales) > 0
                    ORDER BY value DESC
                ),
                cumulative AS (
                    SELECT key, name, value, cluster,
                           ROW_NUMBER() OVER (ORDER BY value DESC) AS rank,
                           SUM(value) OVER () AS total,
                           SUM(value) OVER (ORDER BY value DESC)
                               / NULLIF(SUM(value) OVER (), 0) * 100 AS cumulative_pct
                    FROM ranked
                )
                SELECT key, name, value, rank, cumulative_pct, total, cluster
                FROM cumulative
                ORDER BY rank
                LIMIT 200
            """)
        else:
            stmt = text(f"""
                WITH ranked AS (
                    SELECT {key_col} AS key, {name_col} AS name,
                           SUM(total_sales) AS value
                    FROM {table}
                    WHERE {where}
                    GROUP BY {key_col}, {name_col}
                    HAVING SUM(total_sales) > 0
                    ORDER BY value DESC
                ),
                cumulative AS (
                    SELECT key, name, value,
                           ROW_NUMBER() OVER (ORDER BY value DESC) AS rank,
                           SUM(value) OVER () AS total,
                           SUM(value) OVER (ORDER BY value DESC)
                               / NULLIF(SUM(value) OVER (), 0) * 100 AS cumulative_pct
                    FROM ranked
                )
                SELECT key, name, value, rank, cumulative_pct, total, NULL AS cluster
                FROM cumulative
                ORDER BY rank
                LIMIT 200
            """)

        rows = self._session.execute(stmt, params).fetchall()
        if not rows:
            return ABCAnalysis(
                items=[],
                total=_ZERO,
                class_a_count=0,
                class_b_count=0,
                class_c_count=0,
                class_a_pct=_ZERO,
                class_b_pct=_ZERO,
                class_c_pct=_ZERO,
            )

        total = Decimal(str(rows[0][5]))
        items: list[ABCItem] = []
        a_count = b_count = c_count = 0
        a_value = b_value = c_value = _ZERO

        for r in rows:
            cum_pct = Decimal(str(r[4]))
            cluster = str(r[6]) if r[6] else None

            # For products: use drug_cluster; for customers: use cumulative %
            if cluster and cluster in ("A",):
                abc_class = "A"
            elif cluster and cluster in ("B",):
                abc_class = "B"
            elif cluster:
                abc_class = "C"
            elif cum_pct <= 80:
                abc_class = "A"
            elif cum_pct <= 95:
                abc_class = "B"
            else:
                abc_class = "C"

            if abc_class == "A":
                a_count += 1
                a_value += Decimal(str(r[2]))
            elif abc_class == "B":
                b_count += 1
                b_value += Decimal(str(r[2]))
            else:
                c_count += 1
                c_value += Decimal(str(r[2]))

            items.append(
                ABCItem(
                    rank=int(r[3]),
                    key=int(r[0]),
                    name=str(r[1]),
                    value=Decimal(str(r[2])),
                    cumulative_pct=cum_pct.quantize(Decimal("0.01")),
                    abc_class=abc_class,
                )
            )

        return ABCAnalysis(
            items=items,
            total=total,
            class_a_count=a_count,
            class_b_count=b_count,
            class_c_count=c_count,
            class_a_pct=(a_value / total * 100).quantize(Decimal("0.01")) if total else _ZERO,
            class_b_pct=(b_value / total * 100).quantize(Decimal("0.01")) if total else _ZERO,
            class_c_pct=(c_value / total * 100).quantize(Decimal("0.01")) if total else _ZERO,
        )

    def get_heatmap_data(self, year: int) -> HeatmapData:
        """Calendar heatmap — daily revenue for a year."""
        stmt = text("""
            SELECT full_date, daily_net_amount
            FROM public_marts.metrics_summary
            WHERE EXTRACT(YEAR FROM full_date) = :year
            ORDER BY full_date
        """)
        rows = self._session.execute(stmt, {"year": year}).fetchall()
        if not rows:
            return HeatmapData(cells=[], min_value=_ZERO, max_value=_ZERO)

        cells = [HeatmapCell(date=str(r[0]), value=Decimal(str(r[1]))) for r in rows]
        values = [c.value for c in cells]
        return HeatmapData(cells=cells, min_value=min(values), max_value=max(values))

    def get_returns_trend(self, filters: AnalyticsFilter) -> ReturnsTrend:
        """Monthly returns trend."""
        where, params = build_where(filters, use_year_month=True)

        stmt = text(f"""
            WITH monthly AS (
                SELECT year || '-' || LPAD(month::TEXT, 2, '0') AS period,
                       SUM(return_count) AS return_count,
                       SUM(return_amount) AS return_amount,
                       SUM(total_sales) AS total_amount
                FROM public_marts.agg_sales_monthly
                WHERE {where}
                GROUP BY year, month
                ORDER BY year, month
            )
            SELECT period, return_count,
                   ABS(return_amount) AS return_amount,
                   CASE WHEN total_amount > 0
                        THEN ROUND(ABS(return_amount) / total_amount * 100, 2)
                        ELSE 0 END AS return_rate
            FROM monthly
        """)
        rows = self._session.execute(stmt, params).fetchall()
        if not rows:
            return ReturnsTrend(
                points=[],
                total_returns=0,
                total_return_amount=_ZERO,
                avg_return_rate=_ZERO,
            )

        points = [
            ReturnsTrendPoint(
                period=str(r[0]),
                return_count=int(r[1]) if r[1] else 0,
                return_amount=Decimal(str(r[2])) if r[2] else _ZERO,
                return_rate=Decimal(str(r[3])) if r[3] else _ZERO,
            )
            for r in rows
        ]

        total_returns = sum(p.return_count for p in points)
        total_amount = Decimal(sum(p.return_amount for p in points))
        avg_rate = (
            Decimal(sum(p.return_rate for p in points) / len(points)).quantize(Decimal("0.01"))
            if points
            else _ZERO
        )

        return ReturnsTrend(
            points=points,
            total_returns=total_returns,
            total_return_amount=total_amount,
            avg_return_rate=avg_rate,
        )

    def get_segment_summary(self) -> list[SegmentSummary]:
        """Customer RFM segment summary from feature store."""
        stmt = text("""
            SELECT rfm_segment,
                   COUNT(*) AS count,
                   SUM(monetary) AS total_revenue,
                   ROUND(AVG(monetary), 2) AS avg_monetary,
                   ROUND(AVG(frequency), 2) AS avg_frequency
            FROM public_marts.feat_customer_segments
            GROUP BY rfm_segment
            ORDER BY total_revenue DESC
        """)
        rows = self._session.execute(stmt).fetchall()
        if not rows:
            return []

        total_customers = sum(int(r[1]) for r in rows)
        return [
            SegmentSummary(
                segment=str(r[0]),
                count=int(r[1]),
                total_revenue=Decimal(str(r[2])),
                avg_monetary=Decimal(str(r[3])),
                avg_frequency=Decimal(str(r[4])),
                pct_of_customers=(
                    (Decimal(str(r[1])) / total_customers * 100).quantize(Decimal("0.01"))
                    if total_customers
                    else _ZERO
                ),
            )
            for r in rows
        ]

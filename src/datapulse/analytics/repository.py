"""Read-only repository querying the marts (gold) schema.

All SQL uses parameterized queries via SQLAlchemy ``text()`` — no f-string
interpolation of user-supplied values.  Filter clauses are built dynamically
but every value is bound through ``:param`` placeholders.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.models import (
    AnalyticsFilter,
    KPISummary,
    RankingItem,
    RankingResult,
    ReturnAnalysis,
    TimeSeriesPoint,
    TrendResult,
)
from datapulse.utils.logging import get_logger

log = get_logger(__name__)

_ZERO = Decimal("0")


class AnalyticsRepository:
    """Thin read-only data-access layer over the marts schema."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_where(
        filters: AnalyticsFilter,
        *,
        date_column: str = "date_key",
        use_year_month: bool = False,
    ) -> tuple[str, dict]:
        """Build a WHERE clause string and bind-param dict from *filters*.

        Args:
            filters: User-supplied filter values.
            date_column: Column name used for date/range filtering.
            use_year_month: When ``True`` the date range is compared against
                ``year`` and ``month`` integer columns instead of a single
                date column.

        Returns:
            A ``(clause, params)`` tuple.  *clause* is a SQL fragment like
            ``"site_key = :site_key AND drug_category = :category"`` or
            ``"1=1"`` when no filters are active.
        """
        clauses: list[str] = []
        params: dict = {}

        if filters.date_range is not None:
            if use_year_month:
                clauses.append(
                    "year * 100 + month BETWEEN :start_ym AND :end_ym"
                )
                params["start_ym"] = (
                    filters.date_range.start_date.year * 100
                    + filters.date_range.start_date.month
                )
                params["end_ym"] = (
                    filters.date_range.end_date.year * 100
                    + filters.date_range.end_date.month
                )
            else:
                clauses.append(
                    f"{date_column} BETWEEN :start_date AND :end_date"
                )
                sd = filters.date_range.start_date
                ed = filters.date_range.end_date
                # date_key columns are stored as YYYYMMDD integers
                params["start_date"] = (
                    sd.year * 10000 + sd.month * 100 + sd.day
                )
                params["end_date"] = (
                    ed.year * 10000 + ed.month * 100 + ed.day
                )

        if filters.site_key is not None:
            clauses.append("site_key = :site_key")
            params["site_key"] = filters.site_key

        if filters.category is not None:
            clauses.append("drug_category = :category")
            params["category"] = filters.category

        if filters.brand is not None:
            clauses.append("drug_brand = :brand")
            params["brand"] = filters.brand

        if filters.staff_key is not None:
            clauses.append("staff_key = :staff_key")
            params["staff_key"] = filters.staff_key

        where = " AND ".join(clauses) if clauses else "1=1"
        return where, params

    @staticmethod
    def _safe_growth(current: Decimal, previous: Decimal) -> Decimal | None:
        """Return percentage growth or ``None`` when *previous* is zero."""
        if previous == _ZERO:
            return None
        return ((current - previous) / previous * 100).quantize(
            Decimal("0.01")
        )

    @staticmethod
    def _build_trend(rows: list) -> TrendResult:
        """Convert raw rows ``(period, value)`` into a ``TrendResult``."""
        if not rows:
            return TrendResult(
                points=[],
                total=_ZERO,
                average=_ZERO,
                minimum=_ZERO,
                maximum=_ZERO,
                growth_pct=None,
            )

        points = [
            TimeSeriesPoint(period=str(r[0]), value=Decimal(str(r[1])))
            for r in rows
        ]
        values = [p.value for p in points]
        total = sum(values, _ZERO)
        average = (total / len(values)).quantize(Decimal("0.01"))
        minimum = min(values)
        maximum = max(values)

        growth_pct: Decimal | None = None
        if len(values) >= 2:
            growth_pct = AnalyticsRepository._safe_growth(
                values[-1], values[0]
            )

        return TrendResult(
            points=points,
            total=total,
            average=average,
            minimum=minimum,
            maximum=maximum,
            growth_pct=growth_pct,
        )

    def _build_ranking(
        self,
        rows: list,
    ) -> RankingResult:
        """Convert raw rows ``(key, name, value)`` into a ``RankingResult``."""
        if not rows:
            return RankingResult(items=[], total=_ZERO)

        raw_items = [
            (int(r[0]), str(r[1]), Decimal(str(r[2]))) for r in rows
        ]
        total = sum(v for _, _, v in raw_items) or Decimal("1")

        items = [
            RankingItem(
                rank=idx,
                key=key,
                name=name,
                value=value,
                pct_of_total=(value / total * 100).quantize(Decimal("0.01")),
            )
            for idx, (key, name, value) in enumerate(raw_items, start=1)
        ]
        return RankingResult(items=items, total=total)

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def get_kpi_summary(self, target_date: date) -> KPISummary:
        """Return executive KPI snapshot for *target_date*.

        Queries ``public_marts.metrics_summary`` for daily totals and computes
        MTD / YTD aggregates plus month-over-month and year-over-year growth.
        """
        log.info("get_kpi_summary", target_date=str(target_date))

        # --- Daily row --------------------------------------------------
        daily_stmt = text("""
            SELECT daily_net_amount, mtd_net_amount, ytd_net_amount,
                   daily_transactions, daily_unique_customers
            FROM public_marts.metrics_summary
            WHERE full_date = :target_date
        """)
        row = self._session.execute(
            daily_stmt, {"target_date": target_date}
        ).fetchone()

        if row is None:
            log.warning("kpi_no_data", target_date=str(target_date))
            return KPISummary(
                today_net=_ZERO,
                mtd_net=_ZERO,
                ytd_net=_ZERO,
                mom_growth_pct=None,
                yoy_growth_pct=None,
                daily_transactions=0,
                daily_customers=0,
            )

        today_net = Decimal(str(row[0]))
        mtd_net = Decimal(str(row[1]))
        ytd_net = Decimal(str(row[2]))
        daily_transactions = int(row[3])
        daily_customers = int(row[4])

        # --- MoM growth -------------------------------------------------
        prev_month_stmt = text("""
            SELECT mtd_net_amount
            FROM public_marts.metrics_summary
            WHERE full_date = CAST(
                CAST(:target_date AS date) - INTERVAL '1 month'
            AS date)
        """)
        prev_month_row = self._session.execute(
            prev_month_stmt, {"target_date": target_date}
        ).fetchone()

        mom_growth: Decimal | None = None
        if prev_month_row is not None:
            mom_growth = self._safe_growth(
                mtd_net, Decimal(str(prev_month_row[0]))
            )

        # --- YoY growth -------------------------------------------------
        prev_year_stmt = text("""
            SELECT ytd_net_amount
            FROM public_marts.metrics_summary
            WHERE full_date = CAST(
                CAST(:target_date AS date) - INTERVAL '1 year'
            AS date)
        """)
        prev_year_row = self._session.execute(
            prev_year_stmt, {"target_date": target_date}
        ).fetchone()

        yoy_growth: Decimal | None = None
        if prev_year_row is not None:
            yoy_growth = self._safe_growth(
                ytd_net, Decimal(str(prev_year_row[0]))
            )

        return KPISummary(
            today_net=today_net,
            mtd_net=mtd_net,
            ytd_net=ytd_net,
            mom_growth_pct=mom_growth,
            yoy_growth_pct=yoy_growth,
            daily_transactions=daily_transactions,
            daily_customers=daily_customers,
        )

    def get_daily_trend(self, filters: AnalyticsFilter) -> TrendResult:
        """Return net-sales trend grouped by day."""
        log.info("get_daily_trend", filters=filters.model_dump())
        where, params = self._build_where(filters, date_column="date_key")

        stmt = text(f"""
            SELECT date_key AS period,
                   SUM(total_net_amount) AS value
            FROM public_marts.agg_sales_daily
            WHERE {where}
            GROUP BY date_key
            ORDER BY date_key
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return self._build_trend(rows)

    def get_monthly_trend(self, filters: AnalyticsFilter) -> TrendResult:
        """Return net-sales trend grouped by year-month."""
        log.info("get_monthly_trend", filters=filters.model_dump())
        where, params = self._build_where(
            filters, use_year_month=True
        )

        stmt = text(f"""
            SELECT LPAD(year::text, 4, '0') || '-'
                   || LPAD(month::text, 2, '0') AS period,
                   SUM(total_net_amount) AS value
            FROM public_marts.agg_sales_monthly
            WHERE {where}
            GROUP BY year, month
            ORDER BY year, month
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return self._build_trend(rows)

    def get_top_products(self, filters: AnalyticsFilter) -> RankingResult:
        """Return top-N products by net sales."""
        log.info("get_top_products", filters=filters.model_dump())
        where, params = self._build_where(filters, use_year_month=True)
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT product_key, drug_name, SUM(total_net_amount) AS value
            FROM public_marts.agg_sales_by_product
            WHERE {where}
            GROUP BY product_key, drug_name
            ORDER BY value DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return self._build_ranking(rows)

    def get_top_customers(self, filters: AnalyticsFilter) -> RankingResult:
        """Return top-N customers by net sales."""
        log.info("get_top_customers", filters=filters.model_dump())
        where, params = self._build_where(filters, use_year_month=True)
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT customer_key, customer_name,
                   SUM(total_net_amount) AS value
            FROM public_marts.agg_sales_by_customer
            WHERE {where}
            GROUP BY customer_key, customer_name
            ORDER BY value DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return self._build_ranking(rows)

    def get_top_staff(self, filters: AnalyticsFilter) -> RankingResult:
        """Return top-N staff members by net sales."""
        log.info("get_top_staff", filters=filters.model_dump())
        where, params = self._build_where(filters, use_year_month=True)
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT staff_key, staff_name,
                   SUM(total_net_amount) AS value
            FROM public_marts.agg_sales_by_staff
            WHERE {where}
            GROUP BY staff_key, staff_name
            ORDER BY value DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return self._build_ranking(rows)

    def get_site_performance(self, filters: AnalyticsFilter) -> RankingResult:
        """Return site ranking by net sales."""
        log.info("get_site_performance", filters=filters.model_dump())
        where, params = self._build_where(filters, use_year_month=True)
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT site_key, site_name,
                   SUM(total_net_amount) AS value
            FROM public_marts.agg_sales_by_site
            WHERE {where}
            GROUP BY site_key, site_name
            ORDER BY value DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return self._build_ranking(rows)

    def get_return_analysis(
        self, filters: AnalyticsFilter
    ) -> list[ReturnAnalysis]:
        """Return top return/credit-note entries."""
        log.info("get_return_analysis", filters=filters.model_dump())
        where, params = self._build_where(filters, use_year_month=True)
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT drug_name, customer_name,
                   return_quantity, return_amount,
                   return_count
            FROM public_marts.agg_returns
            WHERE {where}
            ORDER BY return_amount DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()

        if not rows:
            log.info("return_analysis_empty")
            return []

        return [
            ReturnAnalysis(
                drug_name=str(r[0]),
                customer_name=str(r[1]),
                return_quantity=Decimal(str(r[2])),
                return_amount=Decimal(str(r[3])),
                return_count=int(r[4]),
            )
            for r in rows
        ]

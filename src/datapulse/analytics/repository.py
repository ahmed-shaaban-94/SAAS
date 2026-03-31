"""Read-only repository querying the marts (gold) schema.

All SQL uses parameterized queries via SQLAlchemy ``text()`` — no f-string
interpolation of user-supplied values.  Filter clauses are built dynamically
but every value is bound through ``:param`` placeholders.

Shared helpers (build_where, build_ranking, etc.) live in ``queries.py``.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.models import (
    AnalyticsFilter,
    FilterOption,
    FilterOptions,
    KPISummary,
    RankingResult,
    ReturnAnalysis,
    TimeSeriesPoint,
    TrendResult,
)
from datapulse.analytics.queries import (
    ALLOWED_RANKING_COLUMNS,
    ALLOWED_RANKING_TABLES,
    build_ranking,
    build_trend,
    build_where,
    safe_growth,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

_ZERO = Decimal("0")


class AnalyticsRepository:
    """Thin read-only data-access layer over the marts schema."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_ranking(
        self,
        table: str,
        key_col: str,
        name_col: str,
        filters: AnalyticsFilter,
        *,
        use_year_month: bool = True,
    ) -> RankingResult:
        """Generic top-N ranking query against an aggregation table."""
        if table not in ALLOWED_RANKING_TABLES:
            raise ValueError(f"Invalid ranking table: {table}")
        if key_col not in ALLOWED_RANKING_COLUMNS:
            raise ValueError(f"Invalid ranking key column: {key_col}")
        if name_col not in ALLOWED_RANKING_COLUMNS:
            raise ValueError(f"Invalid ranking name column: {name_col}")

        where, params = build_where(filters, use_year_month=use_year_month)
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT {key_col}, {name_col}, SUM(total_net_amount) AS value
            FROM {table}
            WHERE {where}
            GROUP BY {key_col}, {name_col}
            ORDER BY value DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return build_ranking(rows)

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def get_data_date_range(self) -> tuple[date | None, date | None]:
        """Return (min_date, max_date) from metrics_summary."""
        stmt = text("""
            SELECT MIN(full_date), MAX(full_date)
            FROM public_marts.metrics_summary
        """)
        row = self._session.execute(stmt).fetchone()
        if row is None or row[0] is None:
            return None, None
        return row[0], row[1]

    def get_filter_options(self) -> FilterOptions:
        """Return distinct values for all slicer/dropdown filters."""
        log.info("get_filter_options")

        cat_rows = self._session.execute(
            text(
                "SELECT DISTINCT drug_category FROM public_marts.agg_sales_by_product "
                "WHERE drug_category IS NOT NULL ORDER BY drug_category"
            )
        ).fetchall()

        brand_rows = self._session.execute(
            text(
                "SELECT DISTINCT drug_brand FROM public_marts.agg_sales_by_product "
                "WHERE drug_brand IS NOT NULL ORDER BY drug_brand"
            )
        ).fetchall()

        site_rows = self._session.execute(
            text(
                "SELECT DISTINCT site_key, site_name "
                "FROM public_marts.agg_sales_by_site "
                "WHERE site_key > 0 ORDER BY site_name"
            )
        ).fetchall()

        staff_rows = self._session.execute(
            text(
                "SELECT DISTINCT staff_key, staff_name "
                "FROM public_marts.agg_sales_by_staff "
                "WHERE staff_key > 0 ORDER BY staff_name"
            )
        ).fetchall()

        return FilterOptions(
            categories=[str(r[0]) for r in cat_rows],
            brands=[str(r[0]) for r in brand_rows],
            sites=[FilterOption(key=int(r[0]), label=str(r[1])) for r in site_rows],
            staff=[FilterOption(key=int(r[0]), label=str(r[1])) for r in staff_rows],
        )

    def get_kpi_summary(self, target_date: date) -> KPISummary:
        """Return executive KPI snapshot for *target_date*.

        Queries ``public_marts.metrics_summary`` for daily totals and computes
        MTD / YTD aggregates plus month-over-month and year-over-year growth.
        """
        log.info("get_kpi_summary", target_date=str(target_date))

        # --- Daily row --------------------------------------------------
        daily_stmt = text("""
            SELECT daily_net_amount, mtd_net_amount, ytd_net_amount,
                   daily_transactions, daily_unique_customers,
                   daily_returns, mtd_transactions, ytd_transactions
            FROM public_marts.metrics_summary
            WHERE full_date = :target_date
        """)
        row = self._session.execute(daily_stmt, {"target_date": target_date}).fetchone()

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
                avg_basket_size=_ZERO,
                daily_returns=0,
                mtd_transactions=0,
                ytd_transactions=0,
                sparkline=[],
            )

        today_net = Decimal(str(row[0]))
        mtd_net = Decimal(str(row[1]))
        ytd_net = Decimal(str(row[2]))
        daily_transactions = int(row[3])
        daily_customers = int(row[4])
        daily_returns = int(row[5]) if row[5] is not None else 0
        mtd_transactions = int(row[6]) if row[6] is not None else 0
        ytd_transactions = int(row[7]) if row[7] is not None else 0

        # --- Avg basket size (SUM/NULLIF, not AVG of AVG) ---------------
        basket_stmt = text("""
            SELECT SUM(total_net_amount) / NULLIF(SUM(transaction_count), 0)
            FROM public_marts.agg_sales_daily
            WHERE date_key = :date_key
        """)
        date_key = target_date.year * 10000 + target_date.month * 100 + target_date.day
        basket_row = self._session.execute(basket_stmt, {"date_key": date_key}).fetchone()
        avg_basket = (
            Decimal(str(basket_row[0])).quantize(Decimal("0.01"))
            if basket_row and basket_row[0] is not None
            else _ZERO
        )

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
            mom_growth = safe_growth(mtd_net, Decimal(str(prev_month_row[0])))

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
            yoy_growth = safe_growth(ytd_net, Decimal(str(prev_year_row[0])))

        # --- Sparkline (last 7 days) ------------------------------------
        sparkline = self.get_kpi_sparkline(target_date)

        return KPISummary(
            today_net=today_net,
            mtd_net=mtd_net,
            ytd_net=ytd_net,
            mom_growth_pct=mom_growth,
            yoy_growth_pct=yoy_growth,
            daily_transactions=daily_transactions,
            daily_customers=daily_customers,
            avg_basket_size=avg_basket,
            daily_returns=daily_returns,
            mtd_transactions=mtd_transactions,
            ytd_transactions=ytd_transactions,
            sparkline=sparkline,
        )

    def get_kpi_sparkline(self, target_date: date, days: int = 7) -> list[TimeSeriesPoint]:
        """Last N days of daily_net_amount from metrics_summary."""
        start_date = target_date - timedelta(days=days)
        stmt = text("""
            SELECT full_date AS period, daily_net_amount AS value
            FROM public_marts.metrics_summary
            WHERE full_date BETWEEN :start_date AND :target_date
            ORDER BY full_date
        """)
        rows = self._session.execute(
            stmt, {"start_date": start_date, "target_date": target_date}
        ).fetchall()
        return [TimeSeriesPoint(period=str(r[0]), value=Decimal(str(r[1]))) for r in rows]

    def get_daily_trend(self, filters: AnalyticsFilter) -> TrendResult:
        """Return net-sales trend grouped by day."""
        log.info("get_daily_trend", filters=filters.model_dump())
        where, params = build_where(filters, date_column="date_key")

        stmt = text(f"""
            SELECT date_key AS period,
                   SUM(total_net_amount) AS value
            FROM public_marts.agg_sales_daily
            WHERE {where}
            GROUP BY date_key
            ORDER BY date_key
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return build_trend(rows)

    def get_monthly_trend(self, filters: AnalyticsFilter) -> TrendResult:
        """Return net-sales trend grouped by year-month."""
        log.info("get_monthly_trend", filters=filters.model_dump())
        where, params = build_where(filters, use_year_month=True)

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
        return build_trend(rows)

    def get_top_products(self, filters: AnalyticsFilter) -> RankingResult:
        """Return top-N products by net sales."""
        log.info("get_top_products", filters=filters.model_dump())
        return self._get_ranking(
            "public_marts.agg_sales_by_product",
            "product_key",
            "drug_name",
            filters,
        )

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
        """Return top-N staff members by net sales."""
        log.info("get_top_staff", filters=filters.model_dump())
        return self._get_ranking(
            "public_marts.agg_sales_by_staff",
            "staff_key",
            "staff_name",
            filters,
        )

    def get_site_performance(self, filters: AnalyticsFilter) -> RankingResult:
        """Return site ranking by net sales."""
        log.info("get_site_performance", filters=filters.model_dump())
        return self._get_ranking(
            "public_marts.agg_sales_by_site",
            "site_key",
            "site_name",
            filters,
        )

    def get_return_analysis(self, filters: AnalyticsFilter) -> list[ReturnAnalysis]:
        """Return top return/credit-note entries."""
        log.info("get_return_analysis", filters=filters.model_dump())
        where, params = build_where(filters, use_year_month=True)
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

    # Detail methods (get_product_detail, get_customer_detail, get_staff_detail)
    # have been extracted to datapulse.analytics.detail_repository.DetailRepository

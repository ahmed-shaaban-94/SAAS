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
    compute_z_score,
    safe_growth,
    significance_level,
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
        return build_ranking(list(rows))

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
        """Return distinct values for all slicer/dropdown filters.

        Uses a single UNION ALL query instead of 4 separate round-trips.
        """
        log.info("get_filter_options")

        stmt = text("""
            SELECT 'category' AS type, drug_category AS value, NULL::int AS key
            FROM public_marts.agg_sales_by_product
            WHERE drug_category IS NOT NULL
            GROUP BY drug_category

            UNION ALL

            SELECT 'brand', drug_brand, NULL
            FROM public_marts.agg_sales_by_product
            WHERE drug_brand IS NOT NULL
            GROUP BY drug_brand

            UNION ALL

            SELECT 'site', site_name, site_key
            FROM public_marts.agg_sales_by_site
            WHERE site_key > 0
            GROUP BY site_key, site_name

            UNION ALL

            SELECT 'staff', staff_name, staff_key
            FROM public_marts.agg_sales_by_staff
            WHERE staff_key > 0
            GROUP BY staff_key, staff_name

            ORDER BY type, value
        """)
        rows = self._session.execute(stmt).fetchall()

        categories: list[str] = []
        brands: list[str] = []
        sites: list[FilterOption] = []
        staff: list[FilterOption] = []

        for r in rows:
            rtype, value, key = str(r[0]), str(r[1]), r[2]
            if rtype == "category":
                categories.append(value)
            elif rtype == "brand":
                brands.append(value)
            elif rtype == "site":
                sites.append(FilterOption(key=int(key), label=value))
            elif rtype == "staff":
                staff.append(FilterOption(key=int(key), label=value))

        return FilterOptions(
            categories=categories,
            brands=brands,
            sites=sites,
            staff=staff,
        )

    def get_kpi_summary(self, target_date: date) -> KPISummary:
        """Return executive KPI snapshot for *target_date*.

        Uses a single unified CTE query to fetch daily KPIs, basket size,
        and previous-period comparisons in ONE database round-trip.
        Sparkline is a separate lightweight query.
        """
        log.info("get_kpi_summary", target_date=str(target_date))

        date_key = target_date.year * 10000 + target_date.month * 100 + target_date.day

        stmt = text("""
            WITH daily AS (
                SELECT daily_net_amount, mtd_net_amount, ytd_net_amount,
                       daily_transactions, daily_unique_customers,
                       daily_returns, mtd_transactions, ytd_transactions
                FROM public_marts.metrics_summary
                WHERE full_date = :target_date
            ),
            basket AS (
                SELECT ROUND(
                    SUM(total_net_amount) / NULLIF(SUM(transaction_count), 0),
                    2
                ) AS avg_basket_size
                FROM public_marts.agg_sales_daily
                WHERE date_key = :date_key
            ),
            prev_month AS (
                SELECT mtd_net_amount
                FROM public_marts.metrics_summary
                WHERE full_date = CAST(
                    CAST(:target_date AS date) - INTERVAL '1 month'
                AS date)
            ),
            prev_year AS (
                SELECT ytd_net_amount
                FROM public_marts.metrics_summary
                WHERE full_date = CAST(
                    CAST(:target_date AS date) - INTERVAL '1 year'
                AS date)
            )
            SELECT
                d.daily_net_amount,
                d.mtd_net_amount,
                d.ytd_net_amount,
                d.daily_transactions,
                d.daily_unique_customers,
                d.daily_returns,
                d.mtd_transactions,
                d.ytd_transactions,
                b.avg_basket_size,
                pm.mtd_net_amount AS prev_month_mtd,
                py.ytd_net_amount AS prev_year_ytd
            FROM daily d
            LEFT JOIN basket b ON TRUE
            LEFT JOIN prev_month pm ON TRUE
            LEFT JOIN prev_year py ON TRUE
        """)

        row = (
            self._session.execute(stmt, {"target_date": target_date, "date_key": date_key})
            .mappings()
            .fetchone()
        )

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

        today_net = Decimal(str(row["daily_net_amount"]))
        mtd_net = Decimal(str(row["mtd_net_amount"]))
        ytd_net = Decimal(str(row["ytd_net_amount"]))
        daily_transactions = int(row["daily_transactions"])
        daily_customers = int(row["daily_unique_customers"])
        daily_returns = int(row["daily_returns"]) if row["daily_returns"] is not None else 0
        mtd_transactions = (
            int(row["mtd_transactions"]) if row["mtd_transactions"] is not None else 0
        )
        ytd_transactions = (
            int(row["ytd_transactions"]) if row["ytd_transactions"] is not None else 0
        )
        avg_basket = (
            Decimal(str(row["avg_basket_size"])).quantize(Decimal("0.01"))
            if row["avg_basket_size"] is not None
            else _ZERO
        )

        mom_growth: Decimal | None = None
        if row["prev_month_mtd"] is not None:
            mom_growth = safe_growth(mtd_net, Decimal(str(row["prev_month_mtd"])))

        yoy_growth: Decimal | None = None
        if row["prev_year_ytd"] is not None:
            yoy_growth = safe_growth(ytd_net, Decimal(str(row["prev_year_ytd"])))

        sparkline = self.get_kpi_sparkline(target_date)

        # Statistical significance for MoM/YoY growth
        mom_sig = self._compute_growth_significance(target_date, "mom")
        yoy_sig = self._compute_growth_significance(target_date, "yoy")

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
            mom_significance=mom_sig,
            yoy_significance=yoy_sig,
        )

    def _compute_growth_significance(self, target_date: date, kind: str) -> str | None:
        """Compute statistical significance for MoM or YoY growth.

        Looks up the last 12 monthly MTD values (for MoM) or last 5 yearly YTD
        values (for YoY) and computes a z-score of the current growth rate vs
        the historical distribution of growth rates.
        """
        if kind == "mom":
            # Get last 12 months' MTD net amounts (same day-of-month)
            stmt = text("""
                SELECT mtd_net_amount
                FROM public_marts.metrics_summary
                WHERE EXTRACT(DAY FROM full_date) = EXTRACT(DAY FROM CAST(:td AS date))
                  AND full_date < CAST(:td AS date)
                ORDER BY full_date DESC
                LIMIT 12
            """)
        else:  # yoy
            stmt = text("""
                SELECT ytd_net_amount
                FROM public_marts.metrics_summary
                WHERE EXTRACT(MONTH FROM full_date) = EXTRACT(MONTH FROM CAST(:td AS date))
                  AND EXTRACT(DAY FROM full_date) = EXTRACT(DAY FROM CAST(:td AS date))
                  AND full_date < CAST(:td AS date)
                ORDER BY full_date DESC
                LIMIT 5
            """)

        try:
            rows = self._session.execute(stmt, {"td": target_date}).fetchall()
        except Exception:
            return None
        if len(rows) < 3:
            return None

        values: list[Decimal] = []
        for r in rows:
            if r[0] is not None:
                try:
                    values.append(Decimal(str(r[0])))
                except Exception:
                    continue
        if len(values) < 3:
            return None

        # Compute growth rates between consecutive values (reversed to chronological)
        values.reverse()
        growths: list[Decimal] = []
        for i in range(1, len(values)):
            g = safe_growth(values[i], values[i - 1])
            if g is not None:
                growths.append(g)

        if len(growths) < 3:
            return None

        # Current growth rate (last growth in the series)
        current_growth = growths[-1]
        z = compute_z_score(current_growth, growths)
        return significance_level(z)

    def get_kpi_summary_range(self, filters: AnalyticsFilter) -> KPISummary:
        """Aggregate KPI metrics over a date range instead of a single day.

        * ``today_net`` → total net amount for the *entire* selected range
        * ``mtd_net`` / ``ytd_net`` → running totals from the *last* day in range
        * ``daily_transactions`` → net transactions (sales minus returns) for range
        * ``daily_returns`` → total return count for range
        * ``avg_basket_size`` → weighted average for range
        * ``mom_growth_pct`` → compare range total to same-length previous period
        """
        if filters.date_range is None:
            return self.get_kpi_summary(date.today())

        start = filters.date_range.start_date
        end = filters.date_range.end_date
        log.info("get_kpi_summary_range", start=str(start), end=str(end))

        stmt = text("""
            WITH range_agg AS (
                SELECT
                    ROUND(SUM(daily_net_amount), 2) AS period_net,
                    SUM(daily_transactions)::INT     AS total_transactions,
                    SUM(daily_returns)::INT           AS total_returns,
                    SUM(daily_unique_customers)::INT  AS total_customers
                FROM public_marts.metrics_summary
                WHERE full_date BETWEEN :start_date AND :end_date
            ),
            last_day AS (
                SELECT mtd_net_amount, ytd_net_amount,
                       mtd_transactions, ytd_transactions
                FROM public_marts.metrics_summary
                WHERE full_date = :end_date
            ),
            basket AS (
                SELECT ROUND(
                    SUM(total_net_amount) / NULLIF(SUM(transaction_count), 0),
                    2
                ) AS avg_basket_size
                FROM public_marts.agg_sales_daily
                WHERE date_key BETWEEN :start_key AND :end_key
            ),
            prev_period AS (
                SELECT ROUND(SUM(daily_net_amount), 2) AS prev_net
                FROM public_marts.metrics_summary
                WHERE full_date BETWEEN
                    CAST(:start_date AS date) - (:end_date - :start_date + 1) * INTERVAL '1 day'
                    AND CAST(:start_date AS date) - INTERVAL '1 day'
            )
            SELECT
                r.period_net,
                r.total_transactions,
                r.total_returns,
                r.total_customers,
                l.mtd_net_amount,
                l.ytd_net_amount,
                l.mtd_transactions,
                l.ytd_transactions,
                b.avg_basket_size,
                p.prev_net
            FROM range_agg r
            LEFT JOIN last_day l ON TRUE
            LEFT JOIN basket b ON TRUE
            LEFT JOIN prev_period p ON TRUE
        """)

        start_key = start.year * 10000 + start.month * 100 + start.day
        end_key = end.year * 10000 + end.month * 100 + end.day

        row = (
            self._session.execute(
                stmt,
                {
                    "start_date": start,
                    "end_date": end,
                    "start_key": start_key,
                    "end_key": end_key,
                },
            )
            .mappings()
            .fetchone()
        )

        if row is None or row["period_net"] is None:
            log.warning("kpi_range_no_data", start=str(start), end=str(end))
            return KPISummary(
                today_net=_ZERO,
                mtd_net=_ZERO,
                ytd_net=_ZERO,
                daily_transactions=0,
                daily_customers=0,
                sparkline=[],
            )

        period_net = Decimal(str(row["period_net"]))
        mtd_net = (
            Decimal(str(row["mtd_net_amount"])) if row["mtd_net_amount"] is not None else _ZERO
        )
        ytd_net = (
            Decimal(str(row["ytd_net_amount"])) if row["ytd_net_amount"] is not None else _ZERO
        )
        total_transactions = int(row["total_transactions"] or 0)
        total_returns = int(row["total_returns"] or 0)
        total_customers = int(row["total_customers"] or 0)
        mtd_txn = int(row["mtd_transactions"] or 0)
        ytd_txn = int(row["ytd_transactions"] or 0)
        avg_basket = (
            Decimal(str(row["avg_basket_size"])).quantize(Decimal("0.01"))
            if row["avg_basket_size"] is not None
            else _ZERO
        )

        mom_growth: Decimal | None = None
        if row["prev_net"] is not None:
            prev_net = Decimal(str(row["prev_net"]))
            mom_growth = safe_growth(period_net, prev_net)

        sparkline = self.get_kpi_sparkline(end)

        return KPISummary(
            today_net=period_net,
            mtd_net=mtd_net,
            ytd_net=ytd_net,
            mom_growth_pct=mom_growth,
            yoy_growth_pct=None,
            daily_transactions=total_transactions - total_returns,
            daily_customers=total_customers,
            avg_basket_size=avg_basket,
            daily_returns=total_returns,
            mtd_transactions=mtd_txn,
            ytd_transactions=ytd_txn,
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
        return build_trend(list(rows))

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
        return build_trend(list(rows))

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

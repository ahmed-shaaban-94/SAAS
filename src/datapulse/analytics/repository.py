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
    CustomerAnalytics,
    FilterOption,
    FilterOptions,
    KPISummary,
    ProductPerformance,
    RankingItem,
    RankingResult,
    ReturnAnalysis,
    StaffPerformance,
    TimeSeriesPoint,
    TrendResult,
)
from datapulse.logging import get_logger

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

        # Validate date_column against whitelist to prevent injection
        if date_column not in AnalyticsRepository._ALLOWED_DATE_COLUMNS:
            raise ValueError(f"Invalid date_column: {date_column}")

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

    # Whitelist of valid date columns to prevent SQL injection via dynamic column names
    _ALLOWED_DATE_COLUMNS = frozenset({"date_key", "full_date"})

    def _get_ranking(
        self,
        table: str,
        key_col: str,
        name_col: str,
        filters: AnalyticsFilter,
        *,
        use_year_month: bool = True,
    ) -> RankingResult:
        """Generic top-N ranking query against an aggregation table.

        Consolidates the common pattern used by get_top_products,
        get_top_customers, get_top_staff, and get_site_performance.
        """
        where, params = self._build_where(filters, use_year_month=use_year_month)
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
        return self._build_ranking(rows)

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

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
            sites=[
                FilterOption(key=int(r[0]), label=str(r[1])) for r in site_rows
            ],
            staff=[
                FilterOption(key=int(r[0]), label=str(r[1])) for r in staff_rows
            ],
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
        return self._get_ranking(
            "public_marts.agg_sales_by_product", "product_key", "drug_name", filters,
        )

    def get_top_customers(self, filters: AnalyticsFilter) -> RankingResult:
        """Return top-N customers by net sales."""
        log.info("get_top_customers", filters=filters.model_dump())
        return self._get_ranking(
            "public_marts.agg_sales_by_customer", "customer_key", "customer_name", filters,
        )

    def get_top_staff(self, filters: AnalyticsFilter) -> RankingResult:
        """Return top-N staff members by net sales."""
        log.info("get_top_staff", filters=filters.model_dump())
        return self._get_ranking(
            "public_marts.agg_sales_by_staff", "staff_key", "staff_name", filters,
        )

    def get_site_performance(self, filters: AnalyticsFilter) -> RankingResult:
        """Return site ranking by net sales."""
        log.info("get_site_performance", filters=filters.model_dump())
        return self._get_ranking(
            "public_marts.agg_sales_by_site", "site_key", "site_name", filters,
        )

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

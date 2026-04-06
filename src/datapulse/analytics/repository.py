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
    SITE_DATE_ONLY,
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
            SELECT {key_col}, {name_col}, SUM(total_sales) AS value
            FROM {table}
            WHERE {where} AND {key_col} != -1
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
            SELECT * FROM (
                SELECT 'category' AS type, drug_category AS value, NULL::int AS key
                FROM public_marts.agg_sales_by_product
                WHERE drug_category IS NOT NULL
                GROUP BY drug_category
                ORDER BY drug_category
                LIMIT 500
            ) cats
            UNION ALL
            SELECT * FROM (
                SELECT 'brand', drug_brand, NULL
                FROM public_marts.agg_sales_by_product
                WHERE drug_brand IS NOT NULL
                GROUP BY drug_brand
                ORDER BY drug_brand
                LIMIT 500
            ) brands
            UNION ALL
            SELECT * FROM (
                SELECT 'site', site_name, site_key
                FROM public_marts.agg_sales_by_site
                WHERE site_key > 0
                GROUP BY site_key, site_name
                ORDER BY site_name
                LIMIT 100
            ) sites
            UNION ALL
            SELECT * FROM (
                SELECT 'staff', staff_name, staff_key
                FROM public_marts.agg_sales_by_staff
                WHERE staff_key > 0
                GROUP BY staff_key, staff_name
                ORDER BY staff_name
                LIMIT 500
            ) stf
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
        previous-period comparisons, AND sparkline in ONE database round-trip.
        """
        log.info("get_kpi_summary", target_date=str(target_date))

        date_key = target_date.year * 10000 + target_date.month * 100 + target_date.day
        sparkline_start = target_date - timedelta(days=7)

        # Single unified CTE: daily KPIs + basket + comparisons + sparkline +
        # significance history (MoM 12 months + YoY 5 years) — all in ONE query.
        stmt = text("""
            WITH daily AS (
                SELECT daily_gross_amount, 0 AS daily_discount,
                       mtd_gross_amount, ytd_gross_amount,
                       daily_quantity,
                       daily_transactions, daily_unique_customers,
                       daily_returns, mtd_transactions, ytd_transactions
                FROM public_marts.metrics_summary
                WHERE full_date = :target_date
            ),
            basket AS (
                SELECT ROUND(
                    SUM(total_sales) / NULLIF(SUM(unique_customers), 0),
                    2
                ) AS avg_basket_size
                FROM public_marts.agg_sales_daily
                WHERE date_key = :date_key
            ),
            prev_month AS (
                SELECT mtd_gross_amount
                FROM public_marts.metrics_summary
                WHERE full_date = CAST(
                    CAST(:target_date AS date) - INTERVAL '1 month'
                AS date)
            ),
            prev_year AS (
                SELECT ytd_gross_amount
                FROM public_marts.metrics_summary
                WHERE full_date = CAST(
                    CAST(:target_date AS date) - INTERVAL '1 year'
                AS date)
            ),
            sparkline AS (
                SELECT json_agg(
                    json_build_object('period', full_date, 'value', daily_gross_amount)
                    ORDER BY full_date
                ) AS points
                FROM public_marts.metrics_summary
                WHERE full_date BETWEEN :sparkline_start AND :target_date
            ),
            mom_history AS (
                SELECT json_agg(mtd_gross_amount ORDER BY full_date) AS vals
                FROM public_marts.metrics_summary
                WHERE full_date IN (
                    SELECT (CAST(:target_date AS date) - (n || ' months')::interval)::date
                    FROM generate_series(1, 12) AS n
                )
            ),
            yoy_history AS (
                SELECT json_agg(ytd_gross_amount ORDER BY full_date) AS vals
                FROM public_marts.metrics_summary
                WHERE full_date IN (
                    SELECT (CAST(:target_date AS date) - (n || ' years')::interval)::date
                    FROM generate_series(1, 5) AS n
                )
            )
            SELECT
                d.daily_gross_amount,
                d.daily_discount,
                d.mtd_gross_amount,
                d.ytd_gross_amount,
                d.daily_quantity,
                d.daily_transactions,
                d.daily_unique_customers,
                d.daily_returns,
                d.mtd_transactions,
                d.ytd_transactions,
                b.avg_basket_size,
                pm.mtd_gross_amount AS prev_month_mtd,
                py.ytd_gross_amount AS prev_year_ytd,
                sp.points AS sparkline_points,
                mh.vals AS mom_history,
                yh.vals AS yoy_history
            FROM daily d
            LEFT JOIN basket b ON TRUE
            LEFT JOIN prev_month pm ON TRUE
            LEFT JOIN prev_year py ON TRUE
            LEFT JOIN sparkline sp ON TRUE
            LEFT JOIN mom_history mh ON TRUE
            LEFT JOIN yoy_history yh ON TRUE
        """)

        row = (
            self._session.execute(
                stmt,
                {
                    "target_date": target_date,
                    "date_key": date_key,
                    "sparkline_start": sparkline_start,
                },
            )
            .mappings()
            .fetchone()
        )

        if row is None:
            log.warning("kpi_no_data", target_date=str(target_date))
            return KPISummary(
                today_gross=_ZERO,
                mtd_gross=_ZERO,
                ytd_gross=_ZERO,
                today_discount=_ZERO,
                mom_growth_pct=None,
                yoy_growth_pct=None,
                daily_quantity=_ZERO,
                daily_transactions=0,
                daily_customers=0,
                avg_basket_size=_ZERO,
                daily_returns=0,
                mtd_transactions=0,
                ytd_transactions=0,
                sparkline=[],
            )

        today_gross = Decimal(str(row["daily_gross_amount"]))
        mtd_gross = Decimal(str(row["mtd_gross_amount"]))
        ytd_gross = Decimal(str(row["ytd_gross_amount"]))
        today_discount = Decimal(str(row["daily_discount"])) if row["daily_discount"] else _ZERO
        daily_quantity = Decimal(str(row["daily_quantity"])) if row["daily_quantity"] is not None else _ZERO
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

        # Growth based on gross sales
        mom_growth: Decimal | None = None
        if row["prev_month_mtd"] is not None:
            mom_growth = safe_growth(mtd_gross, Decimal(str(row["prev_month_mtd"])))

        yoy_growth: Decimal | None = None
        if row["prev_year_ytd"] is not None:
            yoy_growth = safe_growth(ytd_gross, Decimal(str(row["prev_year_ytd"])))

        # Parse sparkline from JSON aggregate
        sparkline: list[TimeSeriesPoint] = []
        if row.get("sparkline_points") is not None:
            raw_points = row["sparkline_points"]
            # Handle both pre-parsed list and raw JSON string
            if isinstance(raw_points, str):
                import json

                raw_points = json.loads(raw_points)
            sparkline = [
                TimeSeriesPoint(period=str(p["period"]), value=Decimal(str(p["value"])))
                for p in raw_points
            ]

        # Statistical significance from inline CTE history (no extra queries)
        mom_sig = self._significance_from_history(row.get("mom_history"))
        yoy_sig = self._significance_from_history(row.get("yoy_history"))

        return KPISummary(
            today_gross=today_gross,
            mtd_gross=mtd_gross,
            ytd_gross=ytd_gross,
            today_discount=today_discount,
            mom_growth_pct=mom_growth,
            yoy_growth_pct=yoy_growth,
            daily_quantity=daily_quantity,
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

    @staticmethod
    def _significance_from_history(raw_history) -> str | None:
        """Compute significance from a JSON array of historical values.

        Reuses the same z-score logic as _compute_growth_significance
        but operates on pre-fetched data from the unified CTE — no extra queries.
        """
        if raw_history is None:
            return None
        import json as _json

        if isinstance(raw_history, str):
            raw_history = _json.loads(raw_history)
        values = [Decimal(str(v)) for v in raw_history if v is not None]
        if len(values) < 3:
            return None
        growths: list[Decimal] = []
        for i in range(1, len(values)):
            g = safe_growth(values[i], values[i - 1])
            if g is not None:
                growths.append(g)
        if len(growths) < 3:
            return None
        current_growth = growths[-1]
        z = compute_z_score(current_growth, growths)
        return significance_level(z)

    def _compute_growth_significance(self, target_date: date, kind: str) -> str | None:
        """Compute statistical significance for MoM or YoY growth.

        Looks up the last 12 monthly MTD values (for MoM) or last 5 yearly YTD
        values (for YoY) and computes a z-score of the current growth rate vs
        the historical distribution of growth rates.
        """
        if kind == "mom":
            # Get last 12 months' MTD amounts on the same day-of-month
            # Uses date arithmetic instead of EXTRACT to allow index usage
            stmt = text("""
                SELECT mtd_gross_amount
                FROM public_marts.metrics_summary
                WHERE full_date IN (
                    SELECT (CAST(:td AS date) - (n || ' months')::interval)::date
                    FROM generate_series(1, 12) AS n
                )
                ORDER BY full_date DESC
            """)
        else:  # yoy
            # Get last 5 years' YTD amounts on the same month+day
            stmt = text("""
                SELECT ytd_gross_amount
                FROM public_marts.metrics_summary
                WHERE full_date IN (
                    SELECT (CAST(:td AS date) - (n || ' years')::interval)::date
                    FROM generate_series(1, 5) AS n
                )
                ORDER BY full_date DESC
            """)

        try:
            rows = self._session.execute(stmt, {"td": target_date}).fetchall()
        except Exception as exc:
            log.error(
                "growth_significance_query_failed",
                target_date=str(target_date),
                kind=kind,
                error=str(exc),
            )
            return None
        if len(rows) < 3:
            return None

        values: list[Decimal] = []
        for r in rows:
            if r[0] is not None:
                try:
                    values.append(Decimal(str(r[0])))
                except Exception as exc:
                    log.warning(
                        "growth_significance_decimal_error", value=str(r[0]), error=str(exc)
                    )
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

        * ``today_gross`` → total net amount for the *entire* selected range
        * ``mtd_gross`` / ``ytd_gross`` → running totals from the *last* day in range
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
                    ROUND(SUM(daily_gross_amount), 2) AS period_net,
                    SUM(daily_quantity)::NUMERIC(18,4) AS total_quantity,
                    SUM(daily_transactions)::INT     AS total_transactions,
                    SUM(daily_returns)::INT           AS total_returns,
                    SUM(daily_unique_customers)::INT  AS total_customers
                FROM public_marts.metrics_summary
                WHERE full_date BETWEEN :start_date AND :end_date
            ),
            last_day AS (
                SELECT mtd_gross_amount, ytd_gross_amount,
                       mtd_transactions, ytd_transactions
                FROM public_marts.metrics_summary
                WHERE full_date = :end_date
            ),
            basket AS (
                SELECT ROUND(
                    SUM(total_sales) / NULLIF(SUM(transaction_count), 0),
                    2
                ) AS avg_basket_size
                FROM public_marts.agg_sales_daily
                WHERE date_key BETWEEN :start_key AND :end_key
            ),
            prev_period AS (
                SELECT ROUND(SUM(daily_gross_amount), 2) AS prev_net
                FROM public_marts.metrics_summary
                WHERE full_date BETWEEN
                    CAST(:start_date AS date) - (:end_date - :start_date + 1) * INTERVAL '1 day'
                    AND CAST(:start_date AS date) - INTERVAL '1 day'
            ),
            sparkline AS (
                SELECT json_agg(
                    json_build_object('period', full_date, 'value', daily_gross_amount)
                    ORDER BY full_date
                ) AS points
                FROM public_marts.metrics_summary
                WHERE full_date BETWEEN :sparkline_start AND :end_date
            )
            SELECT
                r.period_net,
                r.total_quantity,
                r.total_transactions,
                r.total_returns,
                r.total_customers,
                l.mtd_gross_amount,
                l.ytd_gross_amount,
                l.mtd_transactions,
                l.ytd_transactions,
                b.avg_basket_size,
                p.prev_net,
                sp.points AS sparkline_points
            FROM range_agg r
            LEFT JOIN last_day l ON TRUE
            LEFT JOIN basket b ON TRUE
            LEFT JOIN prev_period p ON TRUE
            LEFT JOIN sparkline sp ON TRUE
        """)

        sparkline_start = end - timedelta(days=7)
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
                    "sparkline_start": sparkline_start,
                },
            )
            .mappings()
            .fetchone()
        )

        if row is None or row["period_net"] is None:
            log.warning("kpi_range_no_data", start=str(start), end=str(end))
            return KPISummary(
                today_gross=_ZERO,
                mtd_gross=_ZERO,
                ytd_gross=_ZERO,
                daily_transactions=0,
                daily_customers=0,
                sparkline=[],
            )

        period_net = Decimal(str(row["period_net"]))
        total_quantity = Decimal(str(row["total_quantity"])) if row["total_quantity"] is not None else _ZERO
        mtd_gross = (
            Decimal(str(row["mtd_gross_amount"])) if row["mtd_gross_amount"] is not None else _ZERO
        )
        ytd_gross = (
            Decimal(str(row["ytd_gross_amount"])) if row["ytd_gross_amount"] is not None else _ZERO
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

        # Parse sparkline from JSON aggregate
        sparkline: list[TimeSeriesPoint] = []
        if row.get("sparkline_points") is not None:
            raw_points = row["sparkline_points"]
            if isinstance(raw_points, str):
                import json

                raw_points = json.loads(raw_points)
            sparkline = [
                TimeSeriesPoint(period=str(p["period"]), value=Decimal(str(p["value"])))
                for p in raw_points
            ]

        return KPISummary(
            today_gross=period_net,
            mtd_gross=mtd_gross,
            ytd_gross=ytd_gross,
            mom_growth_pct=mom_growth,
            yoy_growth_pct=None,
            daily_quantity=total_quantity,
            daily_transactions=total_transactions - total_returns,
            daily_customers=total_customers,
            avg_basket_size=avg_basket,
            daily_returns=total_returns,
            mtd_transactions=mtd_txn,
            ytd_transactions=ytd_txn,
            sparkline=sparkline,
        )

    def get_kpi_sparkline(self, target_date: date, days: int = 7) -> list[TimeSeriesPoint]:
        """Last N days of daily_gross_amount from metrics_summary."""
        start_date = target_date - timedelta(days=days)
        stmt = text("""
            SELECT full_date AS period, daily_gross_amount AS value
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
        where, params = build_where(filters, date_column="date_key", supported_fields=SITE_DATE_ONLY)

        stmt = text(f"""
            SELECT date_key AS period,
                   SUM(total_sales) AS value
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
        where, params = build_where(filters, use_year_month=True, supported_fields=SITE_DATE_ONLY)

        stmt = text(f"""
            SELECT LPAD(year::text, 4, '0') || '-'
                   || LPAD(month::text, 2, '0') AS period,
                   SUM(total_sales) AS value
            FROM public_marts.agg_sales_monthly
            WHERE {where}
            GROUP BY year, month
            ORDER BY year, month
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return build_trend(list(rows))

    def get_top_products(self, filters: AnalyticsFilter) -> RankingResult:
        """Return top-N products by net sales (excludes Services/Other origin)."""
        log.info("get_top_products", filters=filters.model_dump())
        where, params = build_where(filters, use_year_month=True)
        params["limit"] = filters.limit

        stmt = text(f"""
            SELECT product_key, drug_brand, SUM(total_sales) AS value
            FROM public_marts.agg_sales_by_product
            WHERE {where}
              AND product_key != -1
              AND COALESCE(origin, 'Other') IN ('Pharma', 'Non-pharma', 'HVI')
            GROUP BY product_key, drug_brand
            ORDER BY value DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return build_ranking(list(rows))

    def get_origin_breakdown(self, filters: AnalyticsFilter) -> list[dict]:
        """Revenue breakdown by product origin (Pharma, Non-pharma, HVI)."""
        log.info("get_origin_breakdown", filters=filters.model_dump())
        where, params = build_where(filters, use_year_month=True)

        stmt = text(f"""
            SELECT COALESCE(origin, 'Other') AS origin,
                   ROUND(SUM(total_sales), 2) AS value,
                   COUNT(DISTINCT product_key) AS product_count
            FROM public_marts.agg_sales_by_product
            WHERE {where} AND product_key != -1
            GROUP BY COALESCE(origin, 'Other')
            ORDER BY value DESC
        """)
        rows = self._session.execute(stmt, params).fetchall()
        total = sum(float(r[1]) for r in rows)
        return [
            {
                "origin": str(r[0]),
                "value": float(r[1]),
                "product_count": int(r[2]),
                "pct": round(float(r[1]) / total * 100, 1) if total else 0,
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
            SELECT a.drug_name, a.drug_brand, a.customer_name,
                   a.return_quantity, a.return_amount,
                   a.return_count,
                   COALESCE(p.origin, 'Other') AS origin
            FROM public_marts.agg_returns a
            LEFT JOIN public_marts.dim_product p
                ON a.product_key = p.product_key AND a.tenant_id = p.tenant_id
            WHERE {where}
              AND a.customer_key != -1
            ORDER BY a.return_amount DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()

        if not rows:
            log.info("return_analysis_empty")
            return []

        return [
            ReturnAnalysis(
                drug_name=str(r[0]),
                drug_brand=str(r[1]),
                customer_name=str(r[2]),
                return_quantity=Decimal(str(r[3])),
                return_amount=Decimal(str(r[4])),
                return_count=int(r[5]),
                origin=str(r[6]),
            )
            for r in rows
        ]

    # Detail methods (get_product_detail, get_customer_detail, get_staff_detail)
    # have been extracted to datapulse.analytics.detail_repository.DetailRepository

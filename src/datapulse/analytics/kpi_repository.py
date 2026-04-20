"""KPI and filter-options query methods for the analytics layer."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.kpi_queries import (
    DATE_RANGE_SQL,
    FILTER_OPTIONS_SQL,
    KPI_FCT_SALES_TEMPLATE,
    KPI_SPARKLINE_SQL,
    KPI_SUMMARY_DAILY_SQL,
    KPI_SUMMARY_RANGE_SQL,
)
from datapulse.analytics.models import (
    AnalyticsFilter,
    FilterOption,
    FilterOptions,
    KPISparkline,
    KPISummary,
    TimeSeriesPoint,
)
from datapulse.analytics.queries import (
    compute_z_score,
    safe_growth,
    significance_level,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

_ZERO = Decimal("0")


class KpiRepository:
    """KPI and filter-options query methods."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_data_date_range(self) -> tuple[date | None, date | None]:
        """Return (min_date, max_date) from metrics_summary."""
        stmt = text(DATE_RANGE_SQL)
        row = self._session.execute(stmt).fetchone()
        if row is None or row[0] is None:
            return None, None
        return row[0], row[1]

    def get_filter_options(self) -> FilterOptions:
        """Return distinct values for all slicer/dropdown filters.

        Uses a single UNION ALL query instead of 4 separate round-trips.
        """
        log.info("get_filter_options")

        stmt = text(FILTER_OPTIONS_SQL)
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
        # 11-point trailing sparkline (target + 10 prior days) for the new
        # dashboard KPI row — see #503.
        sparkline_start = target_date - timedelta(days=10)

        # Single unified CTE: daily KPIs + basket + comparisons + sparkline +
        # significance history (MoM 12 months + YoY 5 years) — all in ONE query.
        stmt = text(KPI_SUMMARY_DAILY_SQL)

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
                period_gross=_ZERO,
                period_transactions=0,
                period_customers=0,
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
        daily_quantity = (
            Decimal(str(row["daily_quantity"])) if row["daily_quantity"] is not None else _ZERO
        )
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

        # Parse sparkline(s) from JSON aggregates
        sparkline = self._parse_sparkline_points(row.get("sparkline_points"))
        orders_sparkline = self._parse_sparkline_points(row.get("sparkline_orders_points"))

        # Per-metric series for the new KPI row (#503). Stock-risk and
        # expiry-exposure sparklines are left for the route/service layer
        # to populate once historical snapshots exist.
        sparklines = [
            KPISparkline(metric="revenue", points=sparkline),
            KPISparkline(metric="orders", points=orders_sparkline),
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
            daily_transactions=daily_transactions - daily_returns,
            daily_customers=daily_customers,
            period_gross=today_gross,
            period_transactions=daily_transactions - daily_returns,
            period_customers=daily_customers,
            avg_basket_size=avg_basket,
            daily_returns=daily_returns,
            mtd_transactions=mtd_transactions,
            ytd_transactions=ytd_transactions,
            sparkline=sparkline,
            sparklines=sparklines,
            mom_significance=mom_sig,
            yoy_significance=yoy_sig,
        )

    @staticmethod
    def _parse_sparkline_points(raw: object) -> list[TimeSeriesPoint]:
        """Parse a ``json_agg`` sparkline payload into ``TimeSeriesPoint``s.

        Handles both pre-parsed list and raw JSON string (asyncpg vs
        psycopg2 drivers return JSON differently).
        """
        if raw is None:
            return []
        if isinstance(raw, str):
            import json as _json

            raw = _json.loads(raw)
        if not isinstance(raw, list):
            return []
        return [
            TimeSeriesPoint(period=str(p["period"]), value=Decimal(str(p["value"]))) for p in raw
        ]

    @staticmethod
    def _significance_from_history(raw_history) -> str | None:
        """Compute significance from a JSON array of historical values.

        Uses z-score logic on pre-fetched data from the unified CTE — no extra queries.
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

    def _has_dimensional_filters(self, filters: AnalyticsFilter) -> bool:
        """Check if any non-date dimensional filters are active."""
        return any(
            [
                filters.site_key is not None,
                filters.category is not None,
                filters.brand is not None,
                filters.staff_key is not None,
            ]
        )

    def _get_kpi_from_fct_sales(self, filters: AnalyticsFilter) -> KPISummary:
        """KPI aggregation via fct_sales with dimension JOINs for filtered queries."""
        assert filters.date_range is not None
        start = filters.date_range.start_date
        end = filters.date_range.end_date
        start_key = start.year * 10000 + start.month * 100 + start.day
        end_key = end.year * 10000 + end.month * 100 + end.day
        log.info(
            "get_kpi_fct_sales",
            start=str(start),
            end=str(end),
            filters=filters.model_dump(exclude_none=True),
        )

        # Build dimensional WHERE clauses
        where_parts = ["f.date_key BETWEEN :start_key AND :end_key"]
        params: dict = {"start_key": start_key, "end_key": end_key}

        joins: list[str] = []
        if filters.category is not None or filters.brand is not None:
            joins.append(
                "INNER JOIN public_marts.dim_product p"
                " ON f.product_key = p.product_key"
                " AND f.tenant_id = p.tenant_id"
            )
            if filters.category is not None:
                where_parts.append("p.drug_category = :category")
                params["category"] = filters.category
            if filters.brand is not None:
                where_parts.append("p.drug_brand = :brand")
                params["brand"] = filters.brand
        if filters.site_key is not None:
            where_parts.append("f.site_key = :site_key")
            params["site_key"] = filters.site_key
        if filters.staff_key is not None:
            where_parts.append("f.staff_key = :staff_key")
            params["staff_key"] = filters.staff_key

        join_clause = "\n".join(joins)
        where_clause = " AND ".join(where_parts)

        # Previous period for MoM growth
        period_len = (end - start).days + 1
        prev_start = start - timedelta(days=period_len)
        prev_end = start - timedelta(days=1)
        prev_start_key = prev_start.year * 10000 + prev_start.month * 100 + prev_start.day
        prev_end_key = prev_end.year * 10000 + prev_end.month * 100 + prev_end.day
        params["prev_start_key"] = prev_start_key
        params["prev_end_key"] = prev_end_key

        # MTD / YTD windows — both anchored at the range's end date so users
        # see the month-to-date and year-to-date running totals "as of" the
        # range they're looking at. Scoped by the same dimensional filters
        # so filtered views (category/brand/site/staff) show filtered MTD/YTD
        # rather than company-wide totals.
        mtd_start = date(end.year, end.month, 1)
        ytd_start = date(end.year, 1, 1)
        mtd_start_key = mtd_start.year * 10000 + mtd_start.month * 100 + mtd_start.day
        ytd_start_key = ytd_start.year * 10000 + ytd_start.month * 100 + ytd_start.day
        params["mtd_start_key"] = mtd_start_key
        params["ytd_start_key"] = ytd_start_key

        # Sparkline date keys
        sparkline_start = end - timedelta(days=7)
        spark_start_key = (
            sparkline_start.year * 10000 + sparkline_start.month * 100 + sparkline_start.day
        )
        params["spark_start_key"] = spark_start_key

        # Build previous period WHERE with same dimensional filters
        prev_where = where_clause.replace(
            "f.date_key BETWEEN :start_key AND :end_key",
            "f.date_key BETWEEN :prev_start_key AND :prev_end_key",
        )
        mtd_where = where_clause.replace(
            "f.date_key BETWEEN :start_key AND :end_key",
            "f.date_key BETWEEN :mtd_start_key AND :end_key",
        )
        ytd_where = where_clause.replace(
            "f.date_key BETWEEN :start_key AND :end_key",
            "f.date_key BETWEEN :ytd_start_key AND :end_key",
        )

        stmt = text(
            KPI_FCT_SALES_TEMPLATE.format(
                join_clause=join_clause,
                where_clause=where_clause,
                prev_where=prev_where,
                mtd_where=mtd_where,
                ytd_where=ytd_where,
            )
        )

        row = self._session.execute(stmt, params).mappings().fetchone()

        if row is None or row["period_net"] is None:
            log.warning("kpi_fct_no_data", start=str(start), end=str(end))
            return KPISummary(
                today_gross=_ZERO,
                mtd_gross=_ZERO,
                ytd_gross=_ZERO,
                daily_transactions=0,
                daily_customers=0,
                period_gross=_ZERO,
                period_transactions=0,
                period_customers=0,
                sparkline=[],
            )

        period_net = Decimal(str(row["period_net"]))
        total_quantity = (
            Decimal(str(row["total_quantity"])) if row["total_quantity"] is not None else _ZERO
        )
        total_transactions = int(row["total_transactions"] or 0)
        total_returns = int(row["total_returns"] or 0)
        total_customers = int(row["total_customers"] or 0)
        avg_basket = (
            Decimal(str(row["avg_basket_size"])).quantize(Decimal("0.01"))
            if row["avg_basket_size"] is not None
            else _ZERO
        )

        # MTD / YTD totals, scoped by the same dimensional filters.
        mtd_gross = Decimal(str(row["mtd_gross"])) if row["mtd_gross"] is not None else _ZERO
        ytd_gross = Decimal(str(row["ytd_gross"])) if row["ytd_gross"] is not None else _ZERO
        mtd_txn = int(row["mtd_transactions"] or 0)
        ytd_txn = int(row["ytd_transactions"] or 0)

        mom_growth: Decimal | None = None
        if row["prev_net"] is not None:
            prev_net = Decimal(str(row["prev_net"]))
            mom_growth = safe_growth(period_net, prev_net)

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
            period_gross=period_net,
            period_transactions=total_transactions - total_returns,
            period_customers=total_customers,
            avg_basket_size=avg_basket,
            daily_returns=total_returns,
            mtd_transactions=mtd_txn,
            ytd_transactions=ytd_txn,
            sparkline=sparkline,
        )

    def get_kpi_summary_range(self, filters: AnalyticsFilter) -> KPISummary:
        """Aggregate KPI metrics over a date range instead of a single day.

        * ``today_gross`` → total net amount for the *entire* selected range
        * ``mtd_gross`` / ``ytd_gross`` → running totals from the *last* day in range
        * ``daily_transactions`` → net transactions (sales minus returns) for range
        * ``daily_returns`` → total return count for range
        * ``avg_basket_size`` → weighted average for range
        * ``mom_growth_pct`` → compare range total to same-length previous period

        When dimensional filters (category, brand, site, staff) are active,
        queries fct_sales with dimension JOINs for accurate filtered results.
        Otherwise uses the fast pre-aggregated metrics_summary path.
        """
        if filters.date_range is None:
            return self.get_kpi_summary(date.today())

        # Use fct_sales path when dimensional filters are active
        if self._has_dimensional_filters(filters):
            return self._get_kpi_from_fct_sales(filters)

        assert filters.date_range is not None
        start = filters.date_range.start_date
        end = filters.date_range.end_date
        log.info("get_kpi_summary_range", start=str(start), end=str(end))

        stmt = text(KPI_SUMMARY_RANGE_SQL)

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
                period_gross=_ZERO,
                period_transactions=0,
                period_customers=0,
                sparkline=[],
            )

        period_net = Decimal(str(row["period_net"]))
        total_quantity = (
            Decimal(str(row["total_quantity"])) if row["total_quantity"] is not None else _ZERO
        )
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
            period_gross=period_net,
            period_transactions=total_transactions - total_returns,
            period_customers=total_customers,
            avg_basket_size=avg_basket,
            daily_returns=total_returns,
            mtd_transactions=mtd_txn,
            ytd_transactions=ytd_txn,
            sparkline=sparkline,
        )

    def get_kpi_sparkline(self, target_date: date, days: int = 7) -> list[TimeSeriesPoint]:
        """Last N days of daily_gross_amount from metrics_summary."""
        start_date = target_date - timedelta(days=days)
        stmt = text(KPI_SPARKLINE_SQL)
        rows = self._session.execute(
            stmt, {"start_date": start_date, "target_date": target_date}
        ).fetchall()
        return [TimeSeriesPoint(period=str(r[0]), value=Decimal(str(r[1]))) for r in rows]

"""Data access layer for forecasting — reads features, writes forecast results.

All SQL uses parameterized queries via SQLAlchemy ``text()`` — no f-string
interpolation of user-supplied values.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.forecasting.models import (
    CustomerSegment,
    ForecastAccuracy,
    ForecastPoint,
    ForecastResult,
)
from datapulse.logging import get_logger

log = get_logger(__name__)

_ZERO = Decimal("0")


class ForecastingRepository:
    """Read-only access to feature store + read/write access to forecast_results."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Feature store reads
    # ------------------------------------------------------------------

    def get_daily_revenue_series(
        self, lookback_days: int = 730
    ) -> list[tuple[date, float]]:
        """Daily net revenue from feat_revenue_daily_rolling, ordered by date."""
        stmt = text("""
            SELECT full_date, daily_net_amount
            FROM public_marts.feat_revenue_daily_rolling
            WHERE full_date >= CURRENT_DATE - :lookback
            ORDER BY full_date
        """)
        rows = self._session.execute(stmt, {"lookback": lookback_days}).fetchall()
        return [(row[0], float(row[1])) for row in rows]

    def get_monthly_revenue_series(self) -> list[tuple[str, float]]:
        """Monthly net revenue summed across all sites, ordered chronologically."""
        stmt = text("""
            SELECT
                year || '-' || LPAD(month::TEXT, 2, '0') AS period,
                SUM(total_net_amount) AS total
            FROM public_marts.agg_sales_monthly
            GROUP BY year, month
            ORDER BY year, month
        """)
        rows = self._session.execute(stmt).fetchall()
        return [(row[0], float(row[1])) for row in rows]

    def get_product_monthly_series(
        self, product_key: int
    ) -> list[tuple[str, float]]:
        """Monthly net revenue for a specific product."""
        stmt = text("""
            SELECT
                year || '-' || LPAD(month::TEXT, 2, '0') AS period,
                total_net_amount
            FROM public_marts.agg_sales_by_product
            WHERE product_key = :product_key
            ORDER BY year, month
        """)
        rows = self._session.execute(stmt, {"product_key": product_key}).fetchall()
        return [(row[0], float(row[1])) for row in rows]

    def get_top_products_by_revenue(self, limit: int = 50) -> list[tuple[int, str]]:
        """Return (product_key, drug_name) of top N products by total revenue."""
        stmt = text("""
            SELECT product_key, drug_name
            FROM public_marts.agg_sales_by_product
            GROUP BY product_key, drug_name
            ORDER BY SUM(total_net_amount) DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, {"limit": limit}).fetchall()
        return [(row[0], row[1]) for row in rows]

    def get_customer_segments(
        self,
        segment: str | None = None,
        limit: int = 50,
    ) -> list[CustomerSegment]:
        """Read customer segments from the feature store."""
        where = "1=1"
        params: dict = {"limit": limit}
        if segment:
            where = "rfm_segment = :segment"
            params["segment"] = segment

        stmt = text(f"""
            SELECT
                customer_key, customer_id, customer_name,
                rfm_segment, r_score, f_score, m_score,
                days_since_last, frequency, monetary,
                avg_basket_size, return_rate
            FROM public_marts.feat_customer_segments
            WHERE {where}
            ORDER BY monetary DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, params).fetchall()
        return [
            CustomerSegment(
                customer_key=r[0],
                customer_id=str(r[1]),
                customer_name=str(r[2]),
                rfm_segment=str(r[3]),
                r_score=int(r[4]),
                f_score=int(r[5]),
                m_score=int(r[6]),
                days_since_last=int(r[7]),
                frequency=int(r[8]),
                monetary=Decimal(str(r[9])),
                avg_basket_size=Decimal(str(r[10])) if r[10] else _ZERO,
                return_rate=Decimal(str(r[11])) if r[11] else _ZERO,
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Forecast result writes
    # ------------------------------------------------------------------

    def save_forecasts(
        self,
        results: list[ForecastResult],
        run_at: datetime,
    ) -> int:
        """Bulk upsert forecast points into forecast_results table.

        Returns the number of rows written.
        """
        if not results:
            return 0

        rows_written = 0
        for result in results:
            for point in result.points:
                stmt = text("""
                    INSERT INTO public.forecast_results (
                        entity_type, entity_key, granularity, method,
                        forecast_date, point_forecast, lower_bound, upper_bound,
                        mape, mae, rmse, run_at
                    ) VALUES (
                        :entity_type, :entity_key, :granularity, :method,
                        :forecast_date, :point_forecast, :lower_bound, :upper_bound,
                        :mape, :mae, :rmse, :run_at
                    )
                    ON CONFLICT (tenant_id, entity_type, entity_key, granularity, forecast_date)
                    DO UPDATE SET
                        method = EXCLUDED.method,
                        point_forecast = EXCLUDED.point_forecast,
                        lower_bound = EXCLUDED.lower_bound,
                        upper_bound = EXCLUDED.upper_bound,
                        mape = EXCLUDED.mape,
                        mae = EXCLUDED.mae,
                        rmse = EXCLUDED.rmse,
                        run_at = EXCLUDED.run_at
                """)
                accuracy = result.accuracy_metrics
                self._session.execute(
                    stmt,
                    {
                        "entity_type": result.entity_type,
                        "entity_key": result.entity_key,
                        "granularity": result.granularity,
                        "method": result.method,
                        "forecast_date": point.period,
                        "point_forecast": float(point.value),
                        "lower_bound": float(point.lower_bound),
                        "upper_bound": float(point.upper_bound),
                        "mape": float(accuracy.mape) if accuracy else None,
                        "mae": float(accuracy.mae) if accuracy else None,
                        "rmse": float(accuracy.rmse) if accuracy else None,
                        "run_at": run_at,
                    },
                )
                rows_written += 1

        self._session.flush()
        log.info("forecasts_saved", rows=rows_written)
        return rows_written

    # ------------------------------------------------------------------
    # Forecast result reads
    # ------------------------------------------------------------------

    def get_forecast(
        self,
        entity_type: str,
        granularity: str,
        entity_key: int | None = None,
    ) -> ForecastResult | None:
        """Read the latest forecast for display."""
        if entity_key is not None:
            where = "entity_type = :et AND entity_key = :ek AND granularity = :g"
            params = {"et": entity_type, "ek": entity_key, "g": granularity}
        else:
            where = "entity_type = :et AND entity_key IS NULL AND granularity = :g"
            params = {"et": entity_type, "g": granularity}

        stmt = text(f"""
            SELECT forecast_date, point_forecast, lower_bound, upper_bound,
                   method, mape, mae, rmse, run_at
            FROM public.forecast_results
            WHERE {where}
              AND forecast_date >= CURRENT_DATE
            ORDER BY forecast_date
        """)
        rows = self._session.execute(stmt, params).fetchall()
        if not rows:
            return None

        first = rows[0]
        method = str(first[4])
        mape = Decimal(str(first[5])) if first[5] is not None else None
        mae = Decimal(str(first[6])) if first[6] is not None else None
        rmse = Decimal(str(first[7])) if first[7] is not None else None

        points = [
            ForecastPoint(
                period=str(r[0]),
                value=Decimal(str(r[1])),
                lower_bound=Decimal(str(r[2])) if r[2] is not None else _ZERO,
                upper_bound=Decimal(str(r[3])) if r[3] is not None else _ZERO,
            )
            for r in rows
        ]

        accuracy = None
        if mape is not None:
            accuracy = ForecastAccuracy(
                mape=mape,
                mae=mae or _ZERO,
                rmse=rmse or _ZERO,
                coverage=_ZERO,
            )

        return ForecastResult(
            entity_type=entity_type,
            entity_key=entity_key,
            method=method,
            horizon=len(points),
            granularity=granularity,
            points=points,
            accuracy_metrics=accuracy,
        )

    def get_forecast_summary_data(self) -> dict:
        """Read aggregated forecast info for the summary endpoint."""
        # Latest run timestamp
        run_stmt = text("""
            SELECT MAX(run_at) FROM public.forecast_results
        """)
        last_run = self._session.execute(run_stmt).scalar()

        # Next 30 days revenue sum
        rev_30d_stmt = text("""
            SELECT COALESCE(SUM(point_forecast), 0)
            FROM public.forecast_results
            WHERE entity_type = 'revenue' AND granularity = 'daily'
              AND forecast_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 29
        """)
        next_30d = self._session.execute(rev_30d_stmt).scalar() or 0

        # Next 3 months revenue
        rev_3m_stmt = text("""
            SELECT COALESCE(SUM(point_forecast), 0)
            FROM public.forecast_results
            WHERE entity_type = 'revenue' AND granularity = 'monthly'
              AND forecast_date >= DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month')
              AND forecast_date < DATE_TRUNC('month', CURRENT_DATE + INTERVAL '4 months')
        """)
        next_3m = self._session.execute(rev_3m_stmt).scalar() or 0

        # Revenue MAPE
        mape_stmt = text("""
            SELECT mape FROM public.forecast_results
            WHERE entity_type = 'revenue' AND granularity = 'daily'
              AND mape IS NOT NULL
            ORDER BY run_at DESC LIMIT 1
        """)
        mape = self._session.execute(mape_stmt).scalar()

        # Top growing products (highest positive change)
        growing_stmt = text("""
            WITH product_forecast AS (
                SELECT entity_key,
                       SUM(point_forecast) AS future_total
                FROM public.forecast_results
                WHERE entity_type = 'product' AND granularity = 'monthly'
                  AND forecast_date >= CURRENT_DATE
                GROUP BY entity_key
            ),
            product_actual AS (
                SELECT product_key,
                       drug_name,
                       SUM(total_net_amount) AS past_total
                FROM public_marts.agg_sales_by_product
                WHERE year = EXTRACT(YEAR FROM CURRENT_DATE)::INT
                GROUP BY product_key, drug_name
            )
            SELECT pa.product_key, pa.drug_name,
                   ROUND((pf.future_total - pa.past_total) / NULLIF(pa.past_total, 0) * 100, 2)
                       AS change_pct
            FROM product_forecast pf
            INNER JOIN product_actual pa ON pf.entity_key = pa.product_key
            WHERE pa.past_total > 0
            ORDER BY change_pct DESC
            LIMIT 5
        """)
        growing = self._session.execute(growing_stmt).fetchall()

        # Top declining
        declining_stmt = text("""
            WITH product_forecast AS (
                SELECT entity_key,
                       SUM(point_forecast) AS future_total
                FROM public.forecast_results
                WHERE entity_type = 'product' AND granularity = 'monthly'
                  AND forecast_date >= CURRENT_DATE
                GROUP BY entity_key
            ),
            product_actual AS (
                SELECT product_key,
                       drug_name,
                       SUM(total_net_amount) AS past_total
                FROM public_marts.agg_sales_by_product
                WHERE year = EXTRACT(YEAR FROM CURRENT_DATE)::INT
                GROUP BY product_key, drug_name
            )
            SELECT pa.product_key, pa.drug_name,
                   ROUND((pf.future_total - pa.past_total) / NULLIF(pa.past_total, 0) * 100, 2)
                       AS change_pct
            FROM product_forecast pf
            INNER JOIN product_actual pa ON pf.entity_key = pa.product_key
            WHERE pa.past_total > 0
            ORDER BY change_pct ASC
            LIMIT 5
        """)
        declining = self._session.execute(declining_stmt).fetchall()

        return {
            "last_run_at": last_run,
            "next_30d_revenue": Decimal(str(next_30d)),
            "next_3m_revenue": Decimal(str(next_3m)),
            "mape": Decimal(str(mape)) if mape is not None else None,
            "growing": [
                {"product_key": r[0], "drug_name": r[1], "change_pct": Decimal(str(r[2]))}
                for r in growing
            ],
            "declining": [
                {"product_key": r[0], "drug_name": r[1], "change_pct": Decimal(str(r[2]))}
                for r in declining
            ],
        }

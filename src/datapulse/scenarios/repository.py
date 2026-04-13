"""Repository for fetching baseline data for scenario simulations."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.logging import get_logger

log = get_logger(__name__)


class ScenarioRepository:
    """Fetches monthly baseline aggregates from the marts schema."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_monthly_baseline(self, months: int) -> list[dict]:
        """Return last N months of revenue, cost, and volume from fct_sales.

        Column mapping against the current schema:
        - revenue → SUM(f.net_amount)     (gross sales minus discount)
        - volume  → SUM(f.quantity)
        - cost    → 0 (fct_sales has no cost-of-goods column yet;
                       the UI cost slider is inert until COGS data is ingested)

        Month bucket is derived with DATE_TRUNC on dim_date.full_date since
        dim_date exposes full_date / year_month / week_start_date but no
        month_start_date column.
        """
        sql = text("""
            SELECT
                TO_CHAR(DATE_TRUNC('month', d.full_date), 'YYYY-MM') AS month,
                COALESCE(SUM(f.net_amount), 0) AS revenue,
                0::NUMERIC AS cost,
                COALESCE(SUM(f.quantity), 0) AS volume
            FROM public_marts.fct_sales f
            JOIN public_marts.dim_date d ON f.date_key = d.date_key
            WHERE DATE_TRUNC('month', d.full_date) >= (
                SELECT DATE_TRUNC('month', MAX(d2.full_date))
                       - (INTERVAL '1 month' * :months)
                FROM public_marts.fct_sales f2
                JOIN public_marts.dim_date d2 ON f2.date_key = d2.date_key
            )
            GROUP BY DATE_TRUNC('month', d.full_date)
            ORDER BY DATE_TRUNC('month', d.full_date)
            LIMIT :limit
        """)
        rows = self._session.execute(sql, {"months": months, "limit": months}).fetchall()
        return [
            {
                "month": row[0],
                "revenue": Decimal(str(row[1])),
                "cost": Decimal(str(row[2])),
                "volume": int(row[3]),
            }
            for row in rows
        ]

    def get_average_price(self) -> Decimal:
        """Return average unit price (net_amount / quantity) over the last ~365 days.

        fct_sales has no unit_price column, so it is computed.
        date_key is YYYYMMDD-encoded INT so "last 365 days" is enforced via a
        full_date join on dim_date (subtracting 365 from date_key would cross
        calendar boundaries and yield invalid dates).
        """
        sql = text("""
            SELECT COALESCE(AVG(f.net_amount / NULLIF(f.quantity, 0)), 0)
            FROM public_marts.fct_sales f
            JOIN public_marts.dim_date d ON f.date_key = d.date_key
            WHERE d.full_date >= (
                SELECT MAX(d2.full_date) - INTERVAL '365 days'
                FROM public_marts.fct_sales f2
                JOIN public_marts.dim_date d2 ON f2.date_key = d2.date_key
            )
        """)
        result = self._session.execute(sql).scalar()
        return Decimal(str(result or 0))

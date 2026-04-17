"""Production fetchers for first-insight candidates.

Each fetcher reads directly from the medallion layers (bronze/silver/gold)
and returns at most one `InsightCandidate`, or None if it has nothing to
say for this tenant. Fetchers are intentionally defensive — they never
raise; they return None on any soft failure.

Shipped fetchers:
- `fetch_top_seller_candidate`    (#402)   fallback — top product, last 30 days.
- `fetch_mom_change_candidate`    (#402 follow-up #2)   biggest MoM swing,
                                          product or site, picks the one
                                          with the largest absolute
                                          percentage change.

Tracked follow-ups (picker + service already accept new fetchers):
- expiry_risk   — SKUs expiring within 30 days.
- stock_risk    — SKUs below reorder point.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.insights_first.models import InsightCandidate
from datapulse.logging import get_logger

log = get_logger(__name__)


def fetch_top_seller_candidate(session: Session, tenant_id: int) -> InsightCandidate | None:
    """Top product by net_sales in the last 30 days.

    Returns None when there is no data for this tenant yet (e.g. a
    brand-new tenant who hasn't loaded sample data).
    """
    stmt = text("""
        SELECT
            material_desc            AS product,
            SUM(net_sales)::FLOAT    AS revenue,
            COUNT(*)                 AS transactions
        FROM bronze.sales
        WHERE tenant_id = :tenant_id
          AND date >= (CURRENT_DATE - INTERVAL '30 days')
          AND net_sales IS NOT NULL
        GROUP BY material_desc
        ORDER BY revenue DESC
        LIMIT 1
    """)
    try:
        row = session.execute(stmt, {"tenant_id": tenant_id}).mappings().fetchone()
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "first_insight_top_seller_query_failed",
            tenant_id=tenant_id,
            error=str(exc),
        )
        return None

    if row is None or row["product"] is None:
        return None

    product = str(row["product"])
    revenue = float(row["revenue"] or 0.0)
    if revenue <= 0:
        return None

    return InsightCandidate(
        kind="top_seller",
        title=f"Your top seller: {product}",
        body=(
            f"{product} drove ${revenue:,.0f} over the last 30 days. "
            "See how it stacks up against the rest of the catalog."
        ),
        action_href="/products",
        # Confidence grows with volume; capped at 0.9 since this is the
        # fallback signal, not the strongest.
        confidence=min(0.9, 0.4 + min(0.5, revenue / 100_000.0)),
    )


_MOM_CHANGE_SQL = text("""
    WITH windows AS (
        SELECT
            DATE_TRUNC('month', CURRENT_DATE)::date                     AS curr_start,
            (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month')::date
                                                                         AS next_start,
            (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::date
                                                                         AS prev_start
    ),
    product_agg AS (
        SELECT
            'product' AS dimension,
            s.material_desc AS label,
            SUM(CASE WHEN s.date >= w.curr_start AND s.date < w.next_start
                     THEN s.net_sales ELSE 0 END)::FLOAT AS current_revenue,
            SUM(CASE WHEN s.date >= w.prev_start AND s.date < w.curr_start
                     THEN s.net_sales ELSE 0 END)::FLOAT AS previous_revenue
        FROM bronze.sales s, windows w
        WHERE s.tenant_id = :tenant_id
          AND s.material_desc IS NOT NULL
          AND s.date >= w.prev_start
          AND s.date < w.next_start
          AND s.net_sales IS NOT NULL
        GROUP BY s.material_desc
    ),
    site_agg AS (
        SELECT
            'site' AS dimension,
            s.site_name AS label,
            SUM(CASE WHEN s.date >= w.curr_start AND s.date < w.next_start
                     THEN s.net_sales ELSE 0 END)::FLOAT AS current_revenue,
            SUM(CASE WHEN s.date >= w.prev_start AND s.date < w.curr_start
                     THEN s.net_sales ELSE 0 END)::FLOAT AS previous_revenue
        FROM bronze.sales s, windows w
        WHERE s.tenant_id = :tenant_id
          AND s.site_name IS NOT NULL
          AND s.date >= w.prev_start
          AND s.date < w.next_start
          AND s.net_sales IS NOT NULL
        GROUP BY s.site_name
    ),
    combined AS (
        SELECT * FROM product_agg
        UNION ALL
        SELECT * FROM site_agg
    )
    SELECT
        dimension,
        label,
        current_revenue,
        previous_revenue,
        CASE
            WHEN previous_revenue > 0
            THEN (current_revenue - previous_revenue) / previous_revenue
            ELSE NULL
        END AS mom_pct
    FROM combined
    WHERE previous_revenue > 0
      AND current_revenue >= 0
    ORDER BY ABS(
        CASE
            WHEN previous_revenue > 0
            THEN (current_revenue - previous_revenue) / previous_revenue
            ELSE 0
        END
    ) DESC,
    ABS(current_revenue - previous_revenue) DESC
    LIMIT 1
""")


def _format_mom_title(label: str, mom_pct: float) -> str:
    """Pharma-operator wording: '{Label} +42% MoM' / '-15% MoM'."""
    pct = round(mom_pct * 100)
    sign = "+" if pct >= 0 else ""
    return f"{label}: {sign}{pct}% MoM"


def _format_mom_body(
    dimension: str, label: str, current: float, previous: float, mom_pct: float
) -> str:
    direction = "up" if mom_pct >= 0 else "down"
    arrow = "increase" if mom_pct >= 0 else "drop"
    what = "Product" if dimension == "product" else "Branch"
    return (
        f"{what} '{label}' is {direction} ${current:,.0f} this month "
        f"from ${previous:,.0f} last month — a {arrow} of "
        f"{abs(round(mom_pct * 100))}%. Worth a look before it compounds."
    )


def _mom_action_href(dimension: str) -> str:
    return "/products" if dimension == "product" else "/sites"


def _mom_confidence(mom_pct: float) -> float:
    """Linear in |mom_pct|; floored at 0.40, capped at 0.95."""
    magnitude = abs(mom_pct)
    # 0% → 0.40, 100% swing → 0.90, saturates to 0.95.
    return min(0.95, 0.40 + min(0.55, magnitude * 0.5))


def fetch_mom_change_candidate(session: Session, tenant_id: int) -> InsightCandidate | None:
    """Biggest month-over-month revenue swing (product or site).

    Picks the single label with the largest absolute percentage change,
    tie-breaking by absolute revenue delta. Returns None when no tenant
    data exists with a valid previous-month baseline.
    """
    try:
        row = session.execute(_MOM_CHANGE_SQL, {"tenant_id": tenant_id}).mappings().fetchone()
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "first_insight_mom_query_failed",
            tenant_id=tenant_id,
            error=str(exc),
        )
        return None

    if row is None:
        return None

    mom_pct_raw = row.get("mom_pct") if hasattr(row, "get") else row["mom_pct"]
    if mom_pct_raw is None:
        return None

    mom_pct = float(mom_pct_raw)
    dimension = str(row["dimension"])
    label = str(row["label"])
    current = float(row["current_revenue"] or 0.0)
    previous = float(row["previous_revenue"] or 0.0)

    if previous <= 0:
        return None

    return InsightCandidate(
        kind="mom_change",
        title=_format_mom_title(label, mom_pct),
        body=_format_mom_body(dimension, label, current, previous, mom_pct),
        action_href=_mom_action_href(dimension),
        confidence=_mom_confidence(mom_pct),
    )

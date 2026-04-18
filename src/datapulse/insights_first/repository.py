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
- `fetch_expiry_risk_candidate`   (#402 follow-up #3)   single SKU most at
                                          risk of expiry within 30 days.
- `fetch_stock_risk_candidate`    (#402 follow-up #4)   single SKU with the
                                          biggest shortfall below its
                                          reorder point.

All four Phase 2 fetchers active — the picker's full priority chain
(mom_change > expiry_risk > stock_risk > top_seller) is wired.
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


_EXPIRY_WINDOW_DAYS = 30

_EXPIRY_RISK_SQL = text("""
    SELECT
        b.drug_name,
        b.batch_number,
        b.site_code,
        b.current_quantity,
        b.days_to_expiry,
        b.alert_level
    FROM public_marts.feat_expiry_alerts b
    WHERE b.days_to_expiry <= :days_threshold
      AND b.current_quantity > 0
    ORDER BY b.days_to_expiry ASC,
             b.current_quantity DESC,
             b.drug_name ASC
    LIMIT 1
""")


_STOCK_RISK_SQL = text("""
    SELECT
        sl.drug_name,
        sl.drug_code,
        sl.site_code,
        sl.current_quantity,
        rc.reorder_point,
        rc.reorder_quantity
    FROM public_marts.agg_stock_levels sl
    INNER JOIN public.reorder_config rc
        ON sl.drug_code = rc.drug_code
       AND sl.site_code = rc.site_code
       AND sl.tenant_id = rc.tenant_id
    WHERE sl.tenant_id = :tenant_id
      AND rc.reorder_point IS NOT NULL
      AND sl.current_quantity <= rc.reorder_point
    ORDER BY (rc.reorder_point - sl.current_quantity) DESC,
             sl.current_quantity ASC
    LIMIT 1
""")


def _expiry_confidence(days_to_expiry: int) -> float:
    """Already expired → 0.95 (capped). 0 days → 0.92. 30 days → ~0.50.

    Linear ramp down from the cap as the days-to-expiry grows; floored
    at 0.40 to stay inside the `InsightCandidate` confidence contract.
    """
    if days_to_expiry <= 0:
        return 0.95
    # 30 days maps to ~0.50, shorter horizons closer to 0.90.
    conf = 0.95 - (days_to_expiry / 30.0) * 0.45
    return min(0.95, max(0.40, conf))


def _format_expiry_title(drug_name: str, days_to_expiry: int) -> str:
    if days_to_expiry <= 0:
        return f"{drug_name}: already expired"
    return f"{drug_name}: {days_to_expiry} days to expiry"


def _format_expiry_body(
    drug_name: str,
    batch_number: str,
    site_code: str,
    quantity: float,
    days_to_expiry: int,
) -> str:
    qty = f"{quantity:,.0f}"
    if days_to_expiry <= 0:
        window = "already past expiry"
    elif days_to_expiry == 1:
        window = "1 day from expiry"
    else:
        window = f"{days_to_expiry} days from expiry"
    return (
        f"Batch {batch_number} at {site_code} carries {qty} units of "
        f"{drug_name}, {window}. FEFO or write-off before the loss hits."
    )


def fetch_expiry_risk_candidate(session: Session, tenant_id: int) -> InsightCandidate | None:
    """Single SKU most at risk of expiring within the next 30 days.

    Picks the batch with the smallest ``days_to_expiry`` (ties broken by
    larger ``current_quantity``). Returns None when no batch meets the
    threshold or has positive on-hand stock.
    """
    try:
        row = (
            session.execute(
                _EXPIRY_RISK_SQL,
                {"tenant_id": tenant_id, "days_threshold": _EXPIRY_WINDOW_DAYS},
            )
            .mappings()
            .fetchone()
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "first_insight_expiry_query_failed",
            tenant_id=tenant_id,
            error=str(exc),
        )
        return None

    if row is None:
        return None

    quantity = float(row["current_quantity"] or 0.0)
    if quantity <= 0:
        return None

    drug_name = str(row["drug_name"] or "(unknown drug)")
    batch_number = str(row["batch_number"] or "")
    site_code = str(row["site_code"] or "")
    days_to_expiry = int(row["days_to_expiry"] or 0)

    return InsightCandidate(
        kind="expiry_risk",
        title=_format_expiry_title(drug_name, days_to_expiry),
        body=_format_expiry_body(drug_name, batch_number, site_code, quantity, days_to_expiry),
        action_href="/expiry",
        confidence=_expiry_confidence(days_to_expiry),
    )


def _stock_confidence(deficit_ratio: float) -> float:
    """deficit_ratio = (reorder_point - current) / reorder_point.

    0 → 0.40 (at threshold). 1 → 0.95 (fully stocked out).
    Clamped to [0.40, 0.95].
    """
    return min(0.95, max(0.40, 0.40 + 0.55 * min(1.0, max(0.0, deficit_ratio))))


def _format_stock_title(drug_name: str, current: float, reorder_point: float) -> str:
    if current <= 0:
        return f"{drug_name}: out of stock"
    shortfall = round(reorder_point - current)
    return f"{drug_name}: {shortfall} units below reorder point"


def _format_stock_body(
    drug_name: str,
    site_code: str,
    current: float,
    reorder_point: float,
    reorder_quantity: float,
) -> str:
    qty_now = f"{current:,.0f}"
    qty_rp = f"{reorder_point:,.0f}"
    qty_order = f"{reorder_quantity:,.0f}"
    if current <= 0:
        lead = f"{drug_name} is out of stock at {site_code}"
    else:
        lead = f"{drug_name} at {site_code} is down to {qty_now} units (reorder point {qty_rp})"
    return f"{lead}. Open the reorder to restock {qty_order} units before it affects dispensing."


def fetch_stock_risk_candidate(session: Session, tenant_id: int) -> InsightCandidate | None:
    """Single SKU with the biggest shortfall below its reorder point.

    Picks by descending absolute deficit ``(reorder_point - current_quantity)``,
    tie-broken by lowest ``current_quantity``. Returns None on soft failure,
    empty result, missing reorder config, or (defensively) if current already
    exceeds the reorder point.
    """
    try:
        row = session.execute(_STOCK_RISK_SQL, {"tenant_id": tenant_id}).mappings().fetchone()
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "first_insight_stock_query_failed",
            tenant_id=tenant_id,
            error=str(exc),
        )
        return None

    if row is None:
        return None

    reorder_point_raw = row["reorder_point"]
    if reorder_point_raw is None:
        return None

    drug_name = str(row["drug_name"] or "(unknown drug)")
    site_code = str(row["site_code"] or "")
    current = float(row["current_quantity"] or 0.0)
    reorder_point = float(reorder_point_raw)
    reorder_quantity = float(row["reorder_quantity"] or 0.0)

    # Defensive: refuse rows where the deficit isn't real.
    if reorder_point <= 0 or current > reorder_point:
        return None

    deficit_ratio = (reorder_point - current) / reorder_point
    return InsightCandidate(
        kind="stock_risk",
        title=_format_stock_title(drug_name, current, reorder_point),
        body=_format_stock_body(drug_name, site_code, current, reorder_point, reorder_quantity),
        action_href="/inventory",
        confidence=_stock_confidence(deficit_ratio),
    )

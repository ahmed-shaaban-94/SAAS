"""Shared query helpers for the analytics module.

Extracted from ``AnalyticsRepository`` so that multiple repository classes
(breakdown, comparison, hierarchy) can reuse the same WHERE-clause builder,
ranking logic, and trend aggregation without circular imports.
"""

from __future__ import annotations

import statistics as _stats
from decimal import Decimal

from datapulse.analytics.models import (
    AnalyticsFilter,
    RankingItem,
    RankingResult,
    StatisticalAnnotation,
    TimeSeriesPoint,
    TrendResult,
)

_ZERO = Decimal("0")

# Whitelists for SQL-safe dynamic identifiers
ALLOWED_DATE_COLUMNS = frozenset({"date_key", "full_date"})

ALLOWED_RANKING_TABLES = frozenset(
    {
        "public_marts.agg_sales_by_product",
        "public_marts.agg_sales_by_customer",
        "public_marts.agg_sales_by_staff",
        "public_marts.agg_sales_by_site",
    }
)

ALLOWED_RANKING_COLUMNS = frozenset(
    {
        "product_key",
        "drug_name",
        "customer_key",
        "customer_name",
        "staff_key",
        "staff_name",
        "site_key",
        "site_name",
    }
)


# Supported filter field sets per table schema.
# Tables that don't have certain columns must exclude those filter fields.
ALL_FILTER_FIELDS = frozenset({"site_key", "category", "brand", "staff_key"})
SITE_DATE_ONLY = frozenset({"site_key"})  # agg_sales_daily, agg_sales_monthly, agg_sales_by_site


def build_where(
    filters: AnalyticsFilter,
    *,
    date_column: str = "date_key",
    use_year_month: bool = False,
    supported_fields: frozenset[str] | None = None,
) -> tuple[str, dict]:
    """Build a WHERE clause string and bind-param dict from *filters*.

    Args:
        supported_fields: Which non-date filter fields the target table supports.
            Defaults to ``ALL_FILTER_FIELDS`` (site_key, category, brand, staff_key).
            Pass ``SITE_DATE_ONLY`` for tables like agg_sales_daily that only
            have site_key (no drug_category, drug_brand, staff_key columns).

    Returns a ``(clause, params)`` tuple.  *clause* is a SQL fragment like
    ``"site_key = :site_key AND drug_category = :category"`` or ``"1=1"``
    when no filters are active.
    """
    if date_column not in ALLOWED_DATE_COLUMNS:
        raise ValueError(f"Invalid date_column: {date_column}")

    fields = supported_fields if supported_fields is not None else ALL_FILTER_FIELDS

    clauses: list[str] = []
    params: dict = {}

    if filters.date_range is not None:
        if use_year_month:
            clauses.append("year * 100 + month BETWEEN :start_ym AND :end_ym")
            params["start_ym"] = (
                filters.date_range.start_date.year * 100 + filters.date_range.start_date.month
            )
            params["end_ym"] = (
                filters.date_range.end_date.year * 100 + filters.date_range.end_date.month
            )
        else:
            clauses.append(f"{date_column} BETWEEN :start_date AND :end_date")
            sd = filters.date_range.start_date
            ed = filters.date_range.end_date
            params["start_date"] = sd.year * 10000 + sd.month * 100 + sd.day
            params["end_date"] = ed.year * 10000 + ed.month * 100 + ed.day

    if filters.site_key is not None and "site_key" in fields:
        clauses.append("site_key = :site_key")
        params["site_key"] = filters.site_key

    if filters.category is not None and "category" in fields:
        clauses.append("drug_category = :category")
        params["category"] = filters.category

    if filters.brand is not None and "brand" in fields:
        clauses.append("drug_brand = :brand")
        params["brand"] = filters.brand

    if filters.staff_key is not None and "staff_key" in fields:
        clauses.append("staff_key = :staff_key")
        params["staff_key"] = filters.staff_key

    where = " AND ".join(clauses) if clauses else "1=1"
    return where, params


def safe_growth(current: Decimal, previous: Decimal) -> Decimal | None:
    """Return percentage growth or ``None`` when *previous* is zero."""
    if previous == _ZERO:
        return None
    return ((current - previous) / previous * 100).quantize(Decimal("0.01"))


def build_trend(rows: list) -> TrendResult:
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

    points = [TimeSeriesPoint(period=str(r[0]), value=Decimal(str(r[1]))) for r in rows]
    values = [p.value for p in points]
    total = sum(values, _ZERO)
    average = (total / len(values)).quantize(Decimal("0.01"))
    minimum = min(values)
    maximum = max(values)

    growth_pct: Decimal | None = None
    if len(values) >= 2:
        growth_pct = safe_growth(values[-1], values[0])

    # Statistical annotation on trend series
    stats: StatisticalAnnotation | None = None
    if len(values) >= 3:
        cv = coefficient_of_variation(values)
        # z-score of last value vs the series distribution
        z = compute_z_score(values[-1], values)
        sig = significance_level(z)
        stats = StatisticalAnnotation(z_score=z, cv=cv, significance=sig)

    return TrendResult(
        points=points,
        total=total,
        average=average,
        minimum=minimum,
        maximum=maximum,
        growth_pct=growth_pct,
        stats=stats,
    )


def compute_z_score(current: Decimal, values: list[Decimal]) -> Decimal | None:
    """Return z-score of *current* relative to *values* distribution.

    Returns ``None`` when fewer than 3 data points or zero standard deviation.
    """
    floats = [float(v) for v in values]
    if len(floats) < 3:
        return None
    try:
        mean = _stats.mean(floats)
        stdev = _stats.stdev(floats)
    except _stats.StatisticsError:
        return None
    if stdev == 0:
        return None
    z = (float(current) - mean) / stdev
    return Decimal(str(round(z, 4)))


def coefficient_of_variation(values: list[Decimal]) -> Decimal | None:
    """Return CV (stdev/mean * 100) as a percentage.

    Returns ``None`` when fewer than 3 data points or zero mean.
    """
    floats = [float(v) for v in values]
    if len(floats) < 3:
        return None
    try:
        mean = _stats.mean(floats)
        stdev = _stats.stdev(floats)
    except _stats.StatisticsError:
        return None
    if mean == 0:
        return None
    cv = abs(stdev / mean) * 100
    return Decimal(str(round(cv, 2)))


def significance_level(z: Decimal | None) -> str:
    """Classify z-score into significance level.

    - |z| >= 1.96  ->  "significant"   (p < 0.05)
    - |z| >= 1.28  ->  "inconclusive"  (p < 0.10)
    - else         ->  "noise"
    """
    if z is None:
        return "noise"
    abs_z = abs(z)
    if abs_z >= Decimal("1.96"):
        return "significant"
    if abs_z >= Decimal("1.28"):
        return "inconclusive"
    return "noise"


def build_ranking(rows: list) -> RankingResult:
    """Convert raw rows ``(key, name, value)`` into a ``RankingResult``."""
    if not rows:
        return RankingResult(items=[], total=_ZERO)

    raw_items = [(int(r[0]), str(r[1]), Decimal(str(r[2]))) for r in rows]
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

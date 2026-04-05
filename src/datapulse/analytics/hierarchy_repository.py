"""Repository for product category/brand hierarchy queries.

Provides a nested Category > Brand > Product view with performance guard
(top 10 products per brand via window function).
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from datapulse.analytics.models import (
    AnalyticsFilter,
    BrandGroup,
    CategoryGroup,
    ProductHierarchy,
    ProductInCategory,
)
from datapulse.analytics.queries import build_where
from datapulse.logging import get_logger

log = get_logger(__name__)

_ZERO = Decimal("0")


class HierarchyRepository:
    """Product hierarchy queries (Category > Brand > Product)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_product_hierarchy(self, filters: AnalyticsFilter) -> ProductHierarchy:
        """Return nested product hierarchy with top 10 products per brand."""
        log.info("get_product_hierarchy", filters=filters.model_dump())
        where, params = build_where(filters, use_year_month=True)

        stmt = text(f"""
            WITH ranked AS (
                SELECT drug_category, drug_brand, product_key, drug_name,
                       SUM(total_sales)  AS total_sales,
                       SUM(transaction_count) AS transaction_count,
                       ROW_NUMBER() OVER (
                           PARTITION BY drug_brand
                           ORDER BY SUM(total_sales) DESC
                       ) AS rn
                FROM public_marts.agg_sales_by_product
                WHERE {where}
                GROUP BY drug_category, drug_brand, product_key, drug_name
            )
            SELECT drug_category, drug_brand, product_key, drug_name,
                   total_sales, transaction_count
            FROM ranked
            WHERE rn <= 10
            ORDER BY drug_category, drug_brand, total_sales DESC
        """)
        rows = self._session.execute(stmt, params).fetchall()

        if not rows:
            return ProductHierarchy(categories=[])

        # Group into nested structure in Python
        cat_map: dict[str, dict[str, list[ProductInCategory]]] = defaultdict(
            lambda: defaultdict(list)
        )
        cat_totals: dict[str, Decimal] = defaultdict(lambda: _ZERO)
        brand_totals: dict[tuple[str, str], Decimal] = defaultdict(lambda: _ZERO)

        for r in rows:
            cat = str(r[0]) if r[0] else "Uncategorized"
            brand = str(r[1]) if r[1] else "Unknown"
            amount = Decimal(str(r[4]))

            cat_map[cat][brand].append(
                ProductInCategory(
                    product_key=int(r[2]),
                    drug_name=str(r[3]),
                    total_sales=amount,
                    transaction_count=int(r[5]),
                )
            )
            cat_totals[cat] += amount
            brand_totals[(cat, brand)] += amount

        # Build sorted hierarchy
        categories = sorted(
            [
                CategoryGroup(
                    category=cat,
                    total_sales=cat_totals[cat],
                    brands=sorted(
                        [
                            BrandGroup(
                                brand=brand,
                                total_sales=brand_totals[(cat, brand)],
                                products=products,
                            )
                            for brand, products in brands.items()
                        ],
                        key=lambda b: b.total_sales,
                        reverse=True,
                    ),
                )
                for cat, brands in cat_map.items()
            ],
            key=lambda c: c.total_sales,
            reverse=True,
        )

        return ProductHierarchy(categories=categories)

"""Repository for product affinity queries."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


class AffinityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_affinity_for_product(
        self,
        product_key: int,
        limit: int = 10,
    ) -> list[dict]:
        """Get top co-purchased products for a given product."""
        stmt = text("""
            SELECT
                CASE WHEN product_key_a = :pk
                     THEN product_key_b ELSE product_key_a
                END AS related_key,
                CASE WHEN product_key_a = :pk
                     THEN product_name_b ELSE product_name_a
                END AS related_name,
                co_occurrence_count,
                support_pct,
                CASE WHEN product_key_a = :pk
                     THEN confidence_a_to_b ELSE confidence_b_to_a
                END AS confidence
            FROM public_marts.feat_product_affinity
            WHERE product_key_a = :pk OR product_key_b = :pk
            ORDER BY co_occurrence_count DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, {"pk": product_key, "limit": limit}).mappings().all()
        return [dict(r) for r in rows]

    def get_top_pairs(self, limit: int = 20) -> list[dict]:
        """Get top product pairs by co-occurrence."""
        stmt = text("""
            SELECT product_key_a, product_name_a,
                   product_key_b, product_name_b,
                   co_occurrence_count, support_pct,
                   confidence_a_to_b, confidence_b_to_a
            FROM public_marts.feat_product_affinity
            ORDER BY co_occurrence_count DESC
            LIMIT :limit
        """)
        rows = self._session.execute(stmt, {"limit": limit}).mappings().all()
        return [dict(r) for r in rows]

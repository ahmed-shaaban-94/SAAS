"""Repository for global fuzzy search across dimension tables."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


class SearchRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def search(self, query: str, limit: int = 10) -> dict:
        """Search products, customers, and staff by name using pg_trgm similarity."""
        per_type = max(limit // 3, 3)

        products = self._search_products(query, per_type)
        customers = self._search_customers(query, per_type)
        staff = self._search_staff(query, per_type)

        return {
            "products": products,
            "customers": customers,
            "staff": staff,
        }

    def _search_products(self, query: str, limit: int) -> list[dict]:
        sql = text("""
            SELECT product_key AS key,
                   drug_name AS name,
                   drug_category AS category,
                   similarity(drug_name, :q) AS score
            FROM public_marts.dim_product
            WHERE drug_name % :q OR drug_name ILIKE :pattern
            ORDER BY similarity(drug_name, :q) DESC
            LIMIT :lim
        """)
        rows = (
            self._session.execute(sql, {"q": query, "pattern": f"%{query}%", "lim": limit})
            .mappings()
            .all()
        )
        return [
            {
                "key": r["key"],
                "name": r["name"],
                "subtitle": r["category"] or "",
                "type": "product",
            }
            for r in rows
        ]

    def _search_customers(self, query: str, limit: int) -> list[dict]:
        sql = text("""
            SELECT customer_key AS key,
                   customer_name AS name,
                   similarity(customer_name, :q) AS score
            FROM public_marts.dim_customer
            WHERE customer_name % :q OR customer_name ILIKE :pattern
            ORDER BY similarity(customer_name, :q) DESC
            LIMIT :lim
        """)
        rows = (
            self._session.execute(sql, {"q": query, "pattern": f"%{query}%", "lim": limit})
            .mappings()
            .all()
        )
        return [
            {"key": r["key"], "name": r["name"], "subtitle": "", "type": "customer"} for r in rows
        ]

    def _search_staff(self, query: str, limit: int) -> list[dict]:
        sql = text("""
            SELECT staff_key AS key,
                   staff_name AS name,
                   similarity(staff_name, :q) AS score
            FROM public_marts.dim_staff
            WHERE staff_name % :q OR staff_name ILIKE :pattern
            ORDER BY similarity(staff_name, :q) DESC
            LIMIT :lim
        """)
        rows = (
            self._session.execute(sql, {"q": query, "pattern": f"%{query}%", "lim": limit})
            .mappings()
            .all()
        )
        return [{"key": r["key"], "name": r["name"], "subtitle": "", "type": "staff"} for r in rows]

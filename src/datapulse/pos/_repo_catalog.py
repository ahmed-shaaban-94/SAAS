"""Read-only product catalog + pharmacist PIN lookup.

Sources: public_marts.dim_product, public_staging.stg_batches,
public.tenant_members (for PIN hash).

Extracted from the original 1,187-LOC ``repository.py`` facade (see #543).
Methods preserve their SQL text and parameter order byte-for-byte.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from datapulse.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

log = get_logger(__name__)


class CatalogRepoMixin:
    """Mixin for :class:`PosRepository` — requires ``self._session`` set by __init__."""

    _session: Session

    def search_dim_products(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search ``public_marts.dim_product`` by drug_code / drug_name / drug_brand.

        Tenant isolation is enforced by RLS via ``SET LOCAL app.tenant_id``.
        ``unit_price`` is the most-recent unit_price from ``public_marts.fct_sales``
        (falls back to 0 when the drug has never been sold).
        """
        pattern = f"%{query}%"
        rows = (
            self._session.execute(
                text("""
                    SELECT
                        p.drug_code,
                        p.drug_name,
                        p.drug_brand,
                        p.drug_cluster,
                        p.drug_category,
                        COALESCE(
                            (
                                SELECT f.unit_price
                                FROM   public_marts.fct_sales f
                                WHERE  f.tenant_id = p.tenant_id
                                AND    f.drug_code = p.drug_code
                                ORDER  BY f.invoice_date DESC
                                LIMIT  1
                            ),
                            0
                        ) AS unit_price
                    FROM   public_marts.dim_product p
                    WHERE  (
                           p.drug_name  ILIKE :pattern
                        OR p.drug_code  ILIKE :pattern
                        OR p.drug_brand ILIKE :pattern
                    )
                    ORDER  BY p.drug_name
                    LIMIT  :limit
                """),
                {"pattern": pattern, "limit": limit},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_product_by_code(self, drug_code: str) -> dict[str, Any] | None:
        """Return a single product by ``drug_code`` with its most-recent unit price."""
        row = (
            self._session.execute(
                text("""
                    SELECT
                        p.drug_code,
                        p.drug_name,
                        p.drug_brand,
                        p.drug_cluster,
                        p.drug_category,
                        COALESCE(
                            (
                                SELECT f.unit_price
                                FROM   public_marts.fct_sales f
                                WHERE  f.tenant_id = p.tenant_id
                                AND    f.drug_code = p.drug_code
                                ORDER  BY f.invoice_date DESC
                                LIMIT  1
                            ),
                            0
                        ) AS unit_price
                    FROM   public_marts.dim_product p
                    WHERE  p.drug_code = :drug_code
                    LIMIT  1
                """),
                {"drug_code": drug_code},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def list_catalog_products(
        self,
        cursor: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return up to *limit* products from ``dim_product`` ordered by drug_code.

        Uses a ``DISTINCT ON`` CTE to pre-compute the latest unit_price for every
        drug_code in a single fct_sales scan — avoids 17.8k correlated subqueries
        that would fire when pulling the full catalog.
        """
        rows = (
            self._session.execute(
                text("""
                    WITH latest_price AS (
                        SELECT DISTINCT ON (drug_code)
                            drug_code,
                            unit_price
                        FROM   public_marts.fct_sales
                        ORDER  BY drug_code, invoice_date DESC
                    )
                    SELECT
                        p.drug_code,
                        p.drug_name,
                        p.drug_brand,
                        p.drug_cluster,
                        p.drug_category,
                        COALESCE(lp.unit_price, 0) AS unit_price
                    FROM   public_marts.dim_product p
                    LEFT   JOIN latest_price lp USING (drug_code)
                    WHERE  (:cursor IS NULL OR p.drug_code > :cursor)
                    ORDER  BY p.drug_code
                    LIMIT  :limit
                """),
                {"cursor": cursor, "limit": limit},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def list_catalog_stock(
        self,
        site: str | None,
        cursor: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return active batches from ``public_staging.stg_batches`` ordered by loaded_at.

        The *cursor* is an ISO timestamp string.  Only batches with
        ``loaded_at > cursor`` are returned so the desktop can page forward
        through the full batch ledger.
        """
        rows = (
            self._session.execute(
                text("""
                    SELECT
                        drug_code,
                        site_code,
                        batch_number,
                        current_quantity,
                        expiry_date,
                        loaded_at
                    FROM   public_staging.stg_batches
                    WHERE  status = 'active'
                      AND  (:site IS NULL OR site_code = :site)
                      AND  (:cursor IS NULL OR loaded_at > :cursor::timestamptz)
                    ORDER  BY loaded_at, drug_code, site_code, batch_number
                    LIMIT  :limit
                """),
                {"site": site, "cursor": cursor, "limit": limit},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_pharmacist_pin_hash(self, pharmacist_id: str) -> str | None:
        """Return the stored PIN hash for a pharmacist member, or None.

        Looks up ``tenant_members.pharmacist_pin_hash`` by ``user_id``.
        RLS scopes the query to the current tenant automatically.
        Returns ``None`` when the member does not exist or has no PIN set.
        """
        row = (
            self._session.execute(
                text("""
                    SELECT pharmacist_pin_hash
                    FROM   public.tenant_members
                    WHERE  user_id = :user_id
                      AND  is_active = TRUE
                    LIMIT 1
                """),
                {"user_id": pharmacist_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return row["pharmacist_pin_hash"]

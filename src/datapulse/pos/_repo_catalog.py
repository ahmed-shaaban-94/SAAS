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
        """Search ``public_marts.dim_product`` and ``pharma.drug_catalog``.

        Tenant isolation on ``dim_product`` is enforced by RLS via
        ``SET LOCAL app.tenant_id``. ``pharma.drug_catalog`` is a global SAP
        catalog (no tenant column) and is visible to every tenant for now;
        revisit when ``pharma.drug_alias`` lands.

        ``unit_price`` is 0 for ``dim_product`` rows here. The previous
        correlated subquery against ``public_marts.fct_sales`` (1.38M rows,
        no per-product index) caused statement timeouts on the search path.
        A proper "latest price" feature will need a materialized view; for
        now, prices come only from ``drug_catalog.price_egp``. dim_product
        still wins when the same code exists in both — see the
        ``NOT EXISTS`` filter on the catalog leg.
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
                        0::numeric AS unit_price
                    FROM   public_marts.dim_product p
                    WHERE  (
                           p.drug_name  ILIKE :pattern
                        OR p.drug_code  ILIKE :pattern
                        OR p.drug_brand ILIKE :pattern
                    )
                    UNION ALL
                    SELECT
                        c.material_code AS drug_code,
                        c.name_en       AS drug_name,
                        c.vendor_name   AS drug_brand,
                        c.subcategory   AS drug_cluster,
                        c.category      AS drug_category,
                        COALESCE(c.price_egp, 0) AS unit_price
                    FROM   pharma.drug_catalog c
                    WHERE  (
                           c.name_en       ILIKE :pattern
                        OR c.material_code ILIKE :pattern
                        OR c.vendor_name   ILIKE :pattern
                    )
                    AND    NOT EXISTS (
                        SELECT 1 FROM public_marts.dim_product p2
                        WHERE  p2.drug_code = c.material_code
                    )
                    ORDER  BY drug_name
                    LIMIT  :limit
                """),
                {"pattern": pattern, "limit": limit},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_product_by_code(self, drug_code: str) -> dict[str, Any] | None:
        """Return a single product by ``drug_code`` with its most-recent unit price.

        Falls back to ``pharma.drug_catalog`` (matched on ``material_code``)
        when the code is not in ``dim_product``. The catalog leg is global
        across tenants — see ``search_dim_products`` docstring for context.
        """
        row = (
            self._session.execute(
                text("""
                    SELECT
                        p.drug_code,
                        p.drug_name,
                        p.drug_brand,
                        p.drug_cluster,
                        p.drug_category,
                        0::numeric AS unit_price
                    FROM   public_marts.dim_product p
                    WHERE  p.drug_code = :drug_code
                    UNION ALL
                    SELECT
                        c.material_code AS drug_code,
                        c.name_en       AS drug_name,
                        c.vendor_name   AS drug_brand,
                        c.subcategory   AS drug_cluster,
                        c.category      AS drug_category,
                        COALESCE(c.price_egp, 0) AS unit_price
                    FROM   pharma.drug_catalog c
                    WHERE  c.material_code = :drug_code
                    AND    NOT EXISTS (
                        SELECT 1 FROM public_marts.dim_product p2
                        WHERE  p2.drug_code = c.material_code
                    )
                    LIMIT  1
                """),
                {"drug_code": drug_code},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_drug_detail(self, drug_code: str) -> dict[str, Any] | None:
        """Return drug detail joined with POS-owned clinical meta (#623).

        LEFT JOIN on ``pos.product_catalog_meta`` so a drug without clinical
        data still returns its dim_product core with ``counseling_text=NULL``
        and ``active_ingredient=NULL``. RLS scopes both tables to the current
        tenant.
        """
        row = (
            self._session.execute(
                text("""
                    SELECT
                        p.drug_code,
                        p.drug_name,
                        p.drug_brand,
                        p.drug_cluster,
                        p.drug_category,
                        0::numeric AS unit_price,
                        m.counseling_text,
                        m.active_ingredient
                    FROM   public_marts.dim_product p
                    LEFT   JOIN pos.product_catalog_meta m
                           ON m.tenant_id = p.tenant_id
                          AND m.drug_code = p.drug_code
                    WHERE  p.drug_code = :drug_code
                    LIMIT  1
                """),
                {"drug_code": drug_code},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_cross_sell_rules(self, drug_code: str) -> list[dict[str, Any]]:
        """Return static cross-sell suggestions for ``drug_code`` (#623).

        Joins ``pos.cross_sell_rules`` to ``dim_product`` for the suggested
        name + latest unit_price. Rows whose suggested drug is missing from
        ``dim_product`` are silently dropped (INNER JOIN) so the UI never
        shows an orphan code with no name.
        """
        rows = (
            self._session.execute(
                text("""
                    SELECT
                        r.suggested_drug_code AS drug_code,
                        p.drug_name,
                        r.reason,
                        r.reason_tag,
                        0::numeric AS unit_price
                    FROM   pos.cross_sell_rules r
                    JOIN   public_marts.dim_product p
                           ON p.drug_code = r.suggested_drug_code
                    WHERE  r.primary_drug_code = :drug_code
                    ORDER  BY r.id
                """),
                {"drug_code": drug_code},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def get_alternatives_by_ingredient(
        self,
        drug_code: str,
    ) -> list[dict[str, Any]]:
        """Return drugs sharing the same ``active_ingredient`` (#623).

        Self-joins ``product_catalog_meta`` on ``active_ingredient`` to find
        siblings, then joins ``dim_product`` for names + latest unit_price.
        Excludes the primary drug itself. Caller is responsible for filtering
        to positive-savings rows — this repo method returns all siblings.
        """
        rows = (
            self._session.execute(
                text("""
                    WITH primary_drug AS (
                        SELECT
                            m.tenant_id,
                            m.drug_code,
                            m.active_ingredient,
                            0::numeric AS unit_price
                        FROM   pos.product_catalog_meta m
                        WHERE  m.drug_code = :drug_code
                          AND  m.active_ingredient IS NOT NULL
                    )
                    SELECT
                        alt.drug_code,
                        p.drug_name,
                        0::numeric AS unit_price,
                        primary_drug.unit_price AS primary_unit_price
                    FROM   pos.product_catalog_meta alt
                    JOIN   primary_drug
                           ON alt.tenant_id         = primary_drug.tenant_id
                          AND alt.active_ingredient = primary_drug.active_ingredient
                          AND alt.drug_code         <> primary_drug.drug_code
                    JOIN   public_marts.dim_product p
                           ON p.drug_code = alt.drug_code
                          AND p.tenant_id = alt.tenant_id
                    ORDER  BY p.drug_name
                """),
                {"drug_code": drug_code},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def list_catalog_products(
        self,
        cursor: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return up to *limit* products ordered by drug_code.

        Combines ``public_marts.dim_product`` (tenant-scoped via RLS) with
        ``pharma.drug_catalog`` (global SAP catalog, ``price_egp``). Catalog
        rows are excluded when the same code is already in ``dim_product``
        to keep precedence intact.

        ``unit_price`` is 0 for ``dim_product`` rows here — the previous
        ``DISTINCT ON`` over ``fct_sales`` (1.38M rows) caused statement
        timeouts at the search endpoint. A proper "latest price" feature
        will need a per-product materialized view; for now, prices come
        only from ``drug_catalog.price_egp``.
        """
        rows = (
            self._session.execute(
                text("""
                    WITH combined AS (
                        SELECT
                            p.drug_code,
                            p.drug_name,
                            p.drug_brand,
                            p.drug_cluster,
                            p.drug_category,
                            0::numeric AS unit_price
                        FROM   public_marts.dim_product p
                        UNION ALL
                        SELECT
                            c.material_code AS drug_code,
                            c.name_en       AS drug_name,
                            c.vendor_name   AS drug_brand,
                            c.subcategory   AS drug_cluster,
                            c.category      AS drug_category,
                            COALESCE(c.price_egp, 0) AS unit_price
                        FROM   pharma.drug_catalog c
                        WHERE  NOT EXISTS (
                            SELECT 1 FROM public_marts.dim_product p2
                            WHERE  p2.drug_code = c.material_code
                        )
                    )
                    SELECT *
                    FROM   combined
                    WHERE  (:cursor IS NULL OR drug_code > :cursor)
                    ORDER  BY drug_code
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

    def get_pharmacist_pin_hash(self, pharmacist_id: str, tenant_id: int) -> str | None:
        """Return the stored PIN hash for a pharmacist member, or None.

        Looks up ``tenant_members.pharmacist_pin_hash`` by ``user_id`` **and**
        ``tenant_id``.  The explicit tenant predicate is a defence-in-depth
        measure (C3): even if RLS were bypassed a pharmacist from tenant A
        cannot match PIN data belonging to tenant B.
        Returns ``None`` when the member does not exist or has no PIN set.
        """
        row = (
            self._session.execute(
                text("""
                    SELECT pharmacist_pin_hash
                    FROM   public.tenant_members
                    WHERE  user_id   = :user_id
                      AND  tenant_id = :tenant_id
                      AND  is_active = TRUE
                    LIMIT 1
                """),
                {"user_id": pharmacist_id, "tenant_id": tenant_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return row["pharmacist_pin_hash"]

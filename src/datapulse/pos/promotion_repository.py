"""Promotion repository — raw SQL access for pos.promotions and joins.

Phase 2 of the POS discount system. Mirrors :class:`VoucherRepository`
conventions (parameterised text queries, tenant-scoped, frozen response
models). ``record_application`` inserts an audit row inside the caller's
transaction — commit/rollback is owned by :func:`datapulse.pos.commit.atomic_commit`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from datapulse.logging import get_logger
from datapulse.pos.exceptions import (
    PosConflictError,
    PosInternalError,
    PosNotFoundError,
    PosValidationError,
)
from datapulse.pos.models import (
    PromotionApplicationRow,
    PromotionCreate,
    PromotionDiscountType,
    PromotionResponse,
    PromotionScope,
    PromotionStatus,
    PromotionUpdate,
)
from datapulse.pos.models.promotions import PreviewMatchesResponse

log = get_logger(__name__)

ALLOWED_COLUMNS: frozenset[str] = frozenset(
    {
        "name",
        "description",
        "discount_type",
        "value",
        "scope",
        "starts_at",
        "ends_at",
        "min_purchase",
        "max_discount",
    }
)


def _row_to_response(
    row: dict,
    *,
    scope_items: list[str],
    scope_categories: list[str],
    scope_brands: list[str] | None = None,
    scope_active_ingredients: list[str] | None = None,
    usage_count: int = 0,
    total_discount_given: Decimal = Decimal("0"),
) -> PromotionResponse:
    """Coerce a DB row + joined sets into a frozen :class:`PromotionResponse`."""
    return PromotionResponse(
        id=int(row["id"]),
        tenant_id=int(row["tenant_id"]),
        name=str(row["name"]),
        description=row.get("description"),
        discount_type=PromotionDiscountType(row["discount_type"]),
        value=Decimal(str(row["value"])),
        scope=PromotionScope(row["scope"]),
        starts_at=row["starts_at"],
        ends_at=row["ends_at"],
        min_purchase=(
            Decimal(str(row["min_purchase"])) if row.get("min_purchase") is not None else None
        ),
        max_discount=(
            Decimal(str(row["max_discount"])) if row.get("max_discount") is not None else None
        ),
        status=PromotionStatus(row["status"]),
        scope_items=scope_items,
        scope_categories=scope_categories,
        scope_brands=scope_brands or [],
        scope_active_ingredients=scope_active_ingredients or [],
        usage_count=usage_count,
        total_discount_given=total_discount_given,
        created_at=row["created_at"],
    )


class PromotionRepository:
    """Raw SQL access for ``pos.promotions`` and its joins.

    All queries are tenant-scoped. Joins (``promotion_items`` /
    ``promotion_categories``) are loaded in a second query to keep the
    primary SELECT simple; for the list view we batch-load them in one
    round trip per join.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def create(self, tenant_id: int, payload: PromotionCreate) -> PromotionResponse:
        """Insert a new promotion plus scope joins. Defaults status to 'paused'."""
        try:
            row = (
                self._session.execute(
                    text(
                        """
                        INSERT INTO pos.promotions
                            (tenant_id, name, description, discount_type, value,
                             scope, starts_at, ends_at, min_purchase, max_discount,
                             status)
                        VALUES
                            (:tid, :name, :desc, :dtype, :val,
                             :scope, :sa, :ea, :minp, :maxd,
                             'paused')
                        RETURNING
                            id, tenant_id, name, description, discount_type, value,
                            scope, starts_at, ends_at, min_purchase, max_discount,
                            status, created_at
                        """
                    ),
                    {
                        "tid": tenant_id,
                        "name": payload.name,
                        "desc": payload.description,
                        "dtype": payload.discount_type.value,
                        "val": payload.value,
                        "scope": payload.scope.value,
                        "sa": payload.starts_at,
                        "ea": payload.ends_at,
                        "minp": payload.min_purchase,
                        "maxd": payload.max_discount,
                    },
                )
                .mappings()
                .first()
            )
        except IntegrityError as exc:
            self._session.rollback()
            raise PosConflictError(f"promotion_name_already_exists:{payload.name}") from exc
        if row is None:  # pragma: no cover — INSERT RETURNING always yields a row
            raise PosInternalError("promotion_insert_no_row")
        promotion_id = int(row["id"])
        self._write_scope_joins(
            promotion_id,
            scope=payload.scope,
            scope_items=payload.scope_items,
            scope_categories=payload.scope_categories,
            scope_brands=payload.scope_brands,
            scope_active_ingredients=payload.scope_active_ingredients,
        )
        return _row_to_response(
            dict(row),
            scope_items=list(payload.scope_items),
            scope_categories=list(payload.scope_categories),
            scope_brands=list(payload.scope_brands),
            scope_active_ingredients=list(payload.scope_active_ingredients),
        )

    def update(
        self,
        tenant_id: int,
        promotion_id: int,
        payload: PromotionUpdate,
    ) -> PromotionResponse:
        """Partial update. Scope joins are rewritten only when ``scope`` changes
        or the matching scope list is provided.
        """
        current = self.get(tenant_id, promotion_id)
        if current is None:
            raise PosNotFoundError("promotion_not_found")

        fields: dict[str, object] = {}
        if payload.name is not None:
            fields["name"] = payload.name
        if payload.description is not None:
            fields["description"] = payload.description
        if payload.discount_type is not None:
            fields["discount_type"] = payload.discount_type.value
        if payload.value is not None:
            fields["value"] = payload.value
        if payload.scope is not None:
            fields["scope"] = payload.scope.value
        if payload.starts_at is not None:
            fields["starts_at"] = payload.starts_at
        if payload.ends_at is not None:
            fields["ends_at"] = payload.ends_at
        if payload.min_purchase is not None:
            fields["min_purchase"] = payload.min_purchase
        if payload.max_discount is not None:
            fields["max_discount"] = payload.max_discount

        if fields:
            unknown = set(fields) - ALLOWED_COLUMNS
            if unknown:
                raise ValueError(f"Unknown promotion column(s): {unknown!r}")
            set_clause = ", ".join(f"{k} = :{k}" for k in fields)
            params = dict(fields)
            params.update({"tid": tenant_id, "pid": promotion_id})
            self._session.execute(
                text(
                    f"""
                    UPDATE pos.promotions
                       SET {set_clause}, updated_at = now()
                     WHERE tenant_id = :tid AND id = :pid
                    """
                ),
                params,
            )

        # Rewrite scope joins if scope or any list changed.
        effective_scope = payload.scope or current.scope
        if payload.scope is not None or payload.scope_items is not None:
            self._delete_scope_items(promotion_id)
        if payload.scope is not None or payload.scope_categories is not None:
            self._delete_scope_categories(promotion_id)
        if payload.scope is not None or payload.scope_brands is not None:
            self._delete_scope_brands(promotion_id)
        if payload.scope is not None or payload.scope_active_ingredients is not None:
            self._delete_scope_active_ingredients(promotion_id)
        self._write_scope_joins(
            promotion_id,
            scope=effective_scope,
            scope_items=(
                payload.scope_items if payload.scope_items is not None else current.scope_items
            ),
            scope_categories=(
                payload.scope_categories
                if payload.scope_categories is not None
                else current.scope_categories
            ),
            scope_brands=(
                payload.scope_brands if payload.scope_brands is not None else current.scope_brands
            ),
            scope_active_ingredients=(
                payload.scope_active_ingredients
                if payload.scope_active_ingredients is not None
                else current.scope_active_ingredients
            ),
        )
        refreshed = self.get(tenant_id, promotion_id)
        assert refreshed is not None  # just wrote it, must exist
        return refreshed

    def set_status(
        self,
        tenant_id: int,
        promotion_id: int,
        status: PromotionStatus,
    ) -> PromotionResponse:
        """Flip a promotion between ``active`` and ``paused``. ``expired`` is
        managed by the scheduled expiry job, not this endpoint.
        """
        if status not in (PromotionStatus.active, PromotionStatus.paused):
            raise PosValidationError("promotion_status_invalid")
        updated = (
            self._session.execute(
                text(
                    """
                    UPDATE pos.promotions
                       SET status = :s, updated_at = now()
                     WHERE tenant_id = :tid AND id = :pid
                     RETURNING id
                    """
                ),
                {"s": status.value, "tid": tenant_id, "pid": promotion_id},
            )
            .mappings()
            .first()
        )
        if updated is None:
            raise PosNotFoundError("promotion_not_found")
        refreshed = self.get(tenant_id, promotion_id)
        assert refreshed is not None
        return refreshed

    def _write_scope_joins(
        self,
        promotion_id: int,
        *,
        scope: PromotionScope,
        scope_items: list[str],
        scope_categories: list[str],
        scope_brands: list[str],
        scope_active_ingredients: list[str],
    ) -> None:
        if scope == PromotionScope.items:
            for drug_code in scope_items:
                self._session.execute(
                    text(
                        """
                        INSERT INTO pos.promotion_items (promotion_id, drug_code)
                        VALUES (:pid, :dc)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"pid": promotion_id, "dc": drug_code},
                )
        elif scope == PromotionScope.category:
            for cluster in scope_categories:
                self._session.execute(
                    text(
                        """
                        INSERT INTO pos.promotion_categories (promotion_id, drug_cluster)
                        VALUES (:pid, :dc)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"pid": promotion_id, "dc": cluster},
                )
        elif scope == PromotionScope.brand:
            for brand in scope_brands:
                self._session.execute(
                    text(
                        """
                        INSERT INTO pos.promotion_brands (promotion_id, brand_name)
                        VALUES (:pid, :br)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"pid": promotion_id, "br": brand},
                )
        elif scope == PromotionScope.active_ingredient:
            for ingredient in scope_active_ingredients:
                self._session.execute(
                    text(
                        """
                        INSERT INTO pos.promotion_active_ingredients
                            (promotion_id, active_ingredient)
                        VALUES (:pid, :ai)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"pid": promotion_id, "ai": ingredient},
                )

    def _delete_scope_items(self, promotion_id: int) -> None:
        self._session.execute(
            text("DELETE FROM pos.promotion_items WHERE promotion_id = :pid"),
            {"pid": promotion_id},
        )

    def _delete_scope_categories(self, promotion_id: int) -> None:
        self._session.execute(
            text("DELETE FROM pos.promotion_categories WHERE promotion_id = :pid"),
            {"pid": promotion_id},
        )

    def _delete_scope_brands(self, promotion_id: int) -> None:
        self._session.execute(
            text("DELETE FROM pos.promotion_brands WHERE promotion_id = :pid"),
            {"pid": promotion_id},
        )

    def _delete_scope_active_ingredients(self, promotion_id: int) -> None:
        self._session.execute(
            text("DELETE FROM pos.promotion_active_ingredients WHERE promotion_id = :pid"),
            {"pid": promotion_id},
        )

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get(self, tenant_id: int, promotion_id: int) -> PromotionResponse | None:
        row = (
            self._session.execute(
                text(
                    """
                    SELECT
                        id, tenant_id, name, description, discount_type, value,
                        scope, starts_at, ends_at, min_purchase, max_discount,
                        status, created_at
                      FROM pos.promotions
                     WHERE tenant_id = :tid AND id = :pid
                    """
                ),
                {"tid": tenant_id, "pid": promotion_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        items, cats, brands, ais = self._load_scope_joins(promotion_id)
        usage, total = self._load_usage_stats(tenant_id, promotion_id)
        return _row_to_response(
            dict(row),
            scope_items=items,
            scope_categories=cats,
            scope_brands=brands,
            scope_active_ingredients=ais,
            usage_count=usage,
            total_discount_given=total,
        )

    def list_for_tenant(
        self,
        tenant_id: int,
        *,
        status: PromotionStatus | None = None,
    ) -> list[PromotionResponse]:
        params: dict[str, object] = {"tid": tenant_id}
        status_filter = ""
        if status is not None:
            status_filter = " AND status = :status"
            params["status"] = status.value
        rows = (
            self._session.execute(
                text(
                    f"""
                    SELECT
                        id, tenant_id, name, description, discount_type, value,
                        scope, starts_at, ends_at, min_purchase, max_discount,
                        status, created_at
                      FROM pos.promotions
                     WHERE tenant_id = :tid{status_filter}
                  ORDER BY created_at DESC
                    """
                ),
                params,
            )
            .mappings()
            .all()
        )
        result: list[PromotionResponse] = []
        for r in rows:
            pid = int(r["id"])
            items, cats, brands, ais = self._load_scope_joins(pid)
            usage, total = self._load_usage_stats(tenant_id, pid)
            result.append(
                _row_to_response(
                    dict(r),
                    scope_items=items,
                    scope_categories=cats,
                    scope_brands=brands,
                    scope_active_ingredients=ais,
                    usage_count=usage,
                    total_discount_given=total,
                )
            )
        return result

    def list_eligible(
        self,
        tenant_id: int,
        *,
        now: datetime,
        drug_codes: list[str],
        drug_clusters: list[str],
        drug_brands: list[str],
        active_ingredients: list[str],
        subtotal: Decimal,
    ) -> list[PromotionResponse]:
        """Return currently-active promotions whose eligibility rules match the cart.

        A promotion is eligible when:
        * ``status = 'active'``
        * ``now`` is inside ``[starts_at, ends_at)``
        * ``scope = 'all'`` OR
          (``scope = 'items'`` AND any drug_code matches) OR
          (``scope = 'category'`` AND any drug_cluster matches) OR
          (``scope = 'brand'`` AND any drug_brand matches — case-insensitive) OR
          (``scope = 'active_ingredient'`` AND any active_ingredient matches — case-insensitive)
        * ``min_purchase`` is null or ``subtotal >= min_purchase``
        """
        rows = (
            self._session.execute(
                text(
                    """
                    SELECT DISTINCT
                        p.id, p.tenant_id, p.name, p.description, p.discount_type,
                        p.value, p.scope, p.starts_at, p.ends_at, p.min_purchase,
                        p.max_discount, p.status, p.created_at
                      FROM pos.promotions p
                 LEFT JOIN pos.promotion_items pi       ON pi.promotion_id = p.id
                 LEFT JOIN pos.promotion_categories pc  ON pc.promotion_id = p.id
                 LEFT JOIN pos.promotion_brands pb      ON pb.promotion_id = p.id
                 LEFT JOIN pos.promotion_active_ingredients pai
                                                        ON pai.promotion_id = p.id
                     WHERE p.tenant_id = :tid
                       AND p.status    = 'active'
                       AND :now BETWEEN p.starts_at AND p.ends_at
                       AND (p.min_purchase IS NULL OR :sub >= p.min_purchase)
                       AND (
                              p.scope = 'all'
                           OR (p.scope = 'items'    AND pi.drug_code    = ANY(:codes))
                           OR (p.scope = 'category' AND pc.drug_cluster = ANY(:clusters))
                           OR (p.scope = 'brand'
                               AND LOWER(pb.brand_name) = ANY(:brands))
                           OR (p.scope = 'active_ingredient'
                               AND LOWER(pai.active_ingredient) = ANY(:ais))
                       )
                  ORDER BY p.created_at DESC
                    """
                ),
                {
                    "tid": tenant_id,
                    "now": now,
                    "sub": subtotal,
                    "codes": drug_codes or [""],
                    "clusters": drug_clusters or [""],
                    "brands": [b.lower() for b in drug_brands] or [""],
                    "ais": [a.lower() for a in active_ingredients] or [""],
                },
            )
            .mappings()
            .all()
        )
        out: list[PromotionResponse] = []
        for r in rows:
            pid = int(r["id"])
            items, cats, brands, ais = self._load_scope_joins(pid)
            # Omit usage stats here — eligibility is hot-path; admin detail
            # view re-queries via get() and pays the extra round-trip.
            out.append(
                _row_to_response(
                    dict(r),
                    scope_items=items,
                    scope_categories=cats,
                    scope_brands=brands,
                    scope_active_ingredients=ais,
                )
            )
        return out

    def _load_scope_joins(
        self, promotion_id: int
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """Return (scope_items, scope_categories, scope_brands, scope_active_ingredients).

        Four round-trips — acceptable for admin CRUD paths. The hot-path
        eligibility query above avoids calling this per-row beyond what's
        already needed for the response shape.
        """
        items = [
            str(r["drug_code"])
            for r in self._session.execute(
                text(
                    "SELECT drug_code FROM pos.promotion_items "
                    "WHERE promotion_id = :pid ORDER BY drug_code"
                ),
                {"pid": promotion_id},
            )
            .mappings()
            .all()
        ]
        cats = [
            str(r["drug_cluster"])
            for r in self._session.execute(
                text(
                    "SELECT drug_cluster FROM pos.promotion_categories "
                    "WHERE promotion_id = :pid ORDER BY drug_cluster"
                ),
                {"pid": promotion_id},
            )
            .mappings()
            .all()
        ]
        brands = [
            str(r["brand_name"])
            for r in self._session.execute(
                text(
                    "SELECT brand_name FROM pos.promotion_brands "
                    "WHERE promotion_id = :pid ORDER BY brand_name"
                ),
                {"pid": promotion_id},
            )
            .mappings()
            .all()
        ]
        ais = [
            str(r["active_ingredient"])
            for r in self._session.execute(
                text(
                    "SELECT active_ingredient FROM pos.promotion_active_ingredients "
                    "WHERE promotion_id = :pid ORDER BY active_ingredient"
                ),
                {"pid": promotion_id},
            )
            .mappings()
            .all()
        ]
        return items, cats, brands, ais

    def _load_usage_stats(self, tenant_id: int, promotion_id: int) -> tuple[int, Decimal]:
        row = (
            self._session.execute(
                text(
                    """
                    SELECT COUNT(*)::INT                       AS n,
                           COALESCE(SUM(discount_applied), 0)  AS total
                      FROM pos.promotion_applications
                     WHERE tenant_id = :tid AND promotion_id = :pid
                    """
                ),
                {"tid": tenant_id, "pid": promotion_id},
            )
            .mappings()
            .first()
        )
        if row is None:  # pragma: no cover — COUNT always returns a row
            return 0, Decimal("0")
        return int(row["n"]), Decimal(str(row["total"]))

    # ------------------------------------------------------------------
    # Preview-matches — admin UI live count
    # ------------------------------------------------------------------

    def preview_matches(
        self, tenant_id: int, scope: PromotionScope, values: list[str]
    ) -> PreviewMatchesResponse:
        """Return the count of SKUs in the product catalog that match scope+values.

        Used by the admin UI to show "matches N SKUs" before saving a promotion.
        ``scope='brand'`` queries ``public_marts.dim_product.drug_brand``.
        ``scope='active_ingredient'`` queries ``pos.product_catalog_meta.active_ingredient``.
        Other scopes (``all``, ``items``, ``category``) return 0 — not meaningful
        without a full cart context.
        """
        lowered = [v.lower() for v in values if v.strip()]
        count = 0
        if scope == PromotionScope.brand and lowered:
            row = (
                self._session.execute(
                    text(
                        """
                        SELECT COUNT(DISTINCT drug_code)::INT AS n
                          FROM public_marts.dim_product
                         WHERE LOWER(drug_brand) = ANY(:vals)
                        """
                    ),
                    {"vals": lowered},
                )
                .mappings()
                .first()
            )
            count = int(row["n"]) if row else 0
        elif scope == PromotionScope.active_ingredient and lowered:
            row = (
                self._session.execute(
                    text(
                        """
                        SELECT COUNT(DISTINCT drug_code)::INT AS n
                          FROM pos.product_catalog_meta
                         WHERE tenant_id = :tid
                           AND LOWER(active_ingredient) = ANY(:vals)
                        """
                    ),
                    {"tid": tenant_id, "vals": lowered},
                )
                .mappings()
                .first()
            )
            count = int(row["n"]) if row else 0
        return PreviewMatchesResponse(scope=scope, values=values, matched_sku_count=count)

    # ------------------------------------------------------------------
    # Atomic application — called from commit.py
    # ------------------------------------------------------------------

    def lock_for_application(
        self,
        tenant_id: int,
        promotion_id: int,
        now: datetime,
    ) -> PromotionResponse:
        """Lock the promotion row + assert it is still active and in-window.

        Uses ``SELECT ... FOR UPDATE`` to serialise with admin pause toggles
        during concurrent checkouts. Must be called inside the caller's
        transaction; the row-lock releases on caller commit.
        """
        row = (
            self._session.execute(
                text(
                    """
                    SELECT
                        id, tenant_id, name, description, discount_type, value,
                        scope, starts_at, ends_at, min_purchase, max_discount,
                        status, created_at
                      FROM pos.promotions
                     WHERE tenant_id = :tid AND id = :pid
                       FOR UPDATE
                    """
                ),
                {"tid": tenant_id, "pid": promotion_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            raise PosNotFoundError("promotion_not_found", http_status=400)
        items, cats, brands, ais = self._load_scope_joins(promotion_id)
        promo = _row_to_response(
            dict(row),
            scope_items=items,
            scope_categories=cats,
            scope_brands=brands,
            scope_active_ingredients=ais,
        )
        if promo.status != PromotionStatus.active:
            raise PosValidationError("promotion_inactive")
        if now < promo.starts_at:
            raise PosValidationError("promotion_not_yet_active")
        if now > promo.ends_at:
            raise PosValidationError("promotion_expired")
        return promo

    def record_application(
        self,
        *,
        tenant_id: int,
        promotion_id: int,
        transaction_id: int,
        cashier_staff_id: str,
        discount_applied: Decimal,
        applied_at: datetime,
    ) -> PromotionApplicationRow:
        """Insert an audit row inside the caller's transaction."""
        row = (
            self._session.execute(
                text(
                    """
                    INSERT INTO pos.promotion_applications
                        (tenant_id, promotion_id, transaction_id,
                         cashier_staff_id, discount_applied, applied_at)
                    VALUES
                        (:tid, :pid, :txn, :cash, :disc, :at)
                    RETURNING id, promotion_id, transaction_id,
                              cashier_staff_id, discount_applied, applied_at
                    """
                ),
                {
                    "tid": tenant_id,
                    "pid": promotion_id,
                    "txn": transaction_id,
                    "cash": cashier_staff_id,
                    "disc": discount_applied,
                    "at": applied_at,
                },
            )
            .mappings()
            .first()
        )
        if row is None:  # pragma: no cover
            raise PosInternalError("promotion_application_insert_no_row")
        return PromotionApplicationRow(
            id=int(row["id"]),
            promotion_id=int(row["promotion_id"]),
            transaction_id=int(row["transaction_id"]),
            cashier_staff_id=str(row["cashier_staff_id"]),
            discount_applied=Decimal(str(row["discount_applied"])),
            applied_at=row["applied_at"],
        )

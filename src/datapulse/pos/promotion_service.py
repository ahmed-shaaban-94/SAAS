"""Promotion service — business logic for admin management + cashier eligibility.

Most CRUD methods are thin pass-throughs to :class:`PromotionRepository`.
``list_eligible()`` enriches the repository eligibility query with the
preview discount the cashier would see if they applied each promotion.
``compute_discount()`` is a pure static helper mirroring
:meth:`VoucherService.compute_discount` for consistency.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from datapulse.logging import get_logger
from datapulse.pos.models import (
    EligibleCartItem,
    EligiblePromotion,
    EligiblePromotionsRequest,
    EligiblePromotionsResponse,
    PromotionCreate,
    PromotionDiscountType,
    PromotionResponse,
    PromotionScope,
    PromotionStatus,
    PromotionUpdate,
)
from datapulse.pos.models.promotions import PreviewMatchesRequest, PreviewMatchesResponse
from datapulse.pos.promotion_repository import PromotionRepository

log = get_logger(__name__)

_MONEY_QUANT = Decimal("0.0001")


class PromotionService:
    """Business logic for promotion management and cashier eligibility."""

    def __init__(self, repo: PromotionRepository) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, tenant_id: int, payload: PromotionCreate) -> PromotionResponse:
        return self._repo.create(tenant_id, payload)

    def update(
        self,
        tenant_id: int,
        promotion_id: int,
        payload: PromotionUpdate,
    ) -> PromotionResponse:
        return self._repo.update(tenant_id, promotion_id, payload)

    def set_status(
        self,
        tenant_id: int,
        promotion_id: int,
        status: PromotionStatus,
    ) -> PromotionResponse:
        return self._repo.set_status(tenant_id, promotion_id, status)

    def get(self, tenant_id: int, promotion_id: int) -> PromotionResponse | None:
        return self._repo.get(tenant_id, promotion_id)

    def list_all(
        self,
        tenant_id: int,
        *,
        status: PromotionStatus | None = None,
    ) -> list[PromotionResponse]:
        return self._repo.list_for_tenant(tenant_id, status=status)

    # ------------------------------------------------------------------
    # Eligibility
    # ------------------------------------------------------------------

    def list_eligible(
        self,
        tenant_id: int,
        req: EligiblePromotionsRequest,
    ) -> EligiblePromotionsResponse:
        """Return promotions the cashier can apply to the current cart.

        The repository returns candidate rows; we then compute the preview
        discount each promotion would yield on the supplied subtotal,
        honouring ``scope`` (only the eligible slice of the cart counts
        toward the percent calculation) and ``max_discount`` caps.
        """
        drug_codes = sorted({item.drug_code for item in req.items})
        drug_clusters = sorted(
            {item.drug_cluster for item in req.items if item.drug_cluster is not None}
        )
        drug_brands = sorted({item.drug_brand for item in req.items if item.drug_brand is not None})
        active_ingredients = sorted(
            {item.active_ingredient for item in req.items if item.active_ingredient is not None}
        )
        now = datetime.now(UTC)
        candidates = self._repo.list_eligible(
            tenant_id,
            now=now,
            drug_codes=drug_codes,
            drug_clusters=drug_clusters,
            drug_brands=drug_brands,
            active_ingredients=active_ingredients,
            subtotal=Decimal(str(req.subtotal)),
        )
        out: list[EligiblePromotion] = []
        for promo in candidates:
            eligible_base = self.eligible_base(promo, req.items)
            if eligible_base <= 0:
                # Subtotal-wide promotions always see `subtotal`; item/category
                # promotions that match no cart line are skipped.
                continue
            preview = self.compute_discount(
                promo.discount_type,
                promo.value,
                eligible_base,
                max_discount=promo.max_discount,
            )
            out.append(
                EligiblePromotion(
                    id=promo.id,
                    name=promo.name,
                    description=promo.description,
                    discount_type=promo.discount_type,
                    value=promo.value,
                    scope=promo.scope,
                    min_purchase=promo.min_purchase,
                    max_discount=promo.max_discount,
                    ends_at=promo.ends_at,
                    preview_discount=preview,
                )
            )
        return EligiblePromotionsResponse(promotions=out)

    @staticmethod
    def eligible_base(
        promo: PromotionResponse,
        items: list[EligibleCartItem],
    ) -> Decimal:
        """Subtotal over only the cart lines that match the promotion's scope.

        ``scope='all'`` uses the full cart subtotal. The narrower scopes
        (``items``, ``category``, ``brand``) sum only matching lines so a
        percent promo is applied to the eligible slice, not the whole cart.
        Brand matching is case-insensitive — the admin-entered list and the
        catalog's ``drug_brand`` are both lowered on comparison.
        """
        if promo.scope == PromotionScope.all:
            return sum(
                (Decimal(str(i.quantity)) * Decimal(str(i.unit_price)) for i in items),
                Decimal("0"),
            )
        if promo.scope == PromotionScope.items:
            codes = set(promo.scope_items)
            return sum(
                (
                    Decimal(str(i.quantity)) * Decimal(str(i.unit_price))
                    for i in items
                    if i.drug_code in codes
                ),
                Decimal("0"),
            )
        if promo.scope == PromotionScope.category:
            clusters = set(promo.scope_categories)
            return sum(
                (
                    Decimal(str(i.quantity)) * Decimal(str(i.unit_price))
                    for i in items
                    if i.drug_cluster in clusters
                ),
                Decimal("0"),
            )
        if promo.scope == PromotionScope.brand:
            brands = {b.lower() for b in promo.scope_brands}
            return sum(
                (
                    Decimal(str(i.quantity)) * Decimal(str(i.unit_price))
                    for i in items
                    if i.drug_brand is not None and i.drug_brand.lower() in brands
                ),
                Decimal("0"),
            )
        # active_ingredient (migration 106)
        ais = {a.lower() for a in promo.scope_active_ingredients}
        return sum(
            (
                Decimal(str(i.quantity)) * Decimal(str(i.unit_price))
                for i in items
                if i.active_ingredient is not None and i.active_ingredient.lower() in ais
            ),
            Decimal("0"),
        )

    def preview_matches(self, tenant_id: int, req: PreviewMatchesRequest) -> PreviewMatchesResponse:
        """Return how many SKUs match the given scope+values in the product catalog."""
        return self._repo.preview_matches(tenant_id, req.scope, req.values)

    # ------------------------------------------------------------------
    # Discount computation — pure helper (parallels VoucherService)
    # ------------------------------------------------------------------

    @staticmethod
    def compute_discount(
        discount_type: PromotionDiscountType,
        value: Decimal,
        base: Decimal,
        *,
        max_discount: Decimal | None = None,
    ) -> Decimal:
        """Return the absolute discount amount to subtract from a subtotal.

        Never exceeds ``base``. Percent promos compute ``base * value / 100``
        and quantize to 4 decimal places (HALF_UP). ``max_discount`` caps
        the absolute amount, which is useful for percent promos that should
        not exceed e.g. EGP 500 on large carts.
        """
        if base <= 0:
            return Decimal("0")
        if discount_type == PromotionDiscountType.amount:
            raw = min(value, base).quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)
        else:
            pct = (base * value) / Decimal("100")
            raw = pct.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)
            raw = min(raw, base)
        if max_discount is not None:
            raw = min(raw, max_discount.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP))
        return raw

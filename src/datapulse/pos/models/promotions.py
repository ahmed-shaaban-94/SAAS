"""Promotion discount engine (Phase 2) — admin-configured time-bound discounts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from datapulse.types import JsonDecimal


class PromotionDiscountType(StrEnum):
    """Kind of discount applied by a promotion."""

    amount = "amount"
    percent = "percent"


class PromotionScope(StrEnum):
    """Which cart items a promotion may be applied against.

    ``brand`` matches against ``dim_product.drug_brand`` (migration 104).
    ``active_ingredient`` matches against ``pos.product_catalog_meta.active_ingredient``
    (migration 106); case-insensitive on both sides.
    """

    all = "all"
    items = "items"
    category = "category"
    brand = "brand"
    active_ingredient = "active_ingredient"


class PromotionStatus(StrEnum):
    """Lifecycle states of a promotion."""

    active = "active"
    paused = "paused"
    expired = "expired"


PromotionNameStr = Annotated[str, StringConstraints(min_length=1, max_length=120)]


class PromotionCreate(BaseModel):
    """Request body to create a new promotion.

    Defaults to ``status='paused'`` on the server side — admins toggle to
    ``active`` explicitly after previewing. ``scope_items`` is required when
    ``scope='items'`` and ``scope_categories`` is required when
    ``scope='category'``. Both lists are ignored for ``scope='all'``.
    """

    model_config = ConfigDict(frozen=True)

    name: PromotionNameStr
    description: str | None = None
    discount_type: PromotionDiscountType
    value: JsonDecimal
    scope: PromotionScope
    starts_at: datetime
    ends_at: datetime
    min_purchase: JsonDecimal | None = None
    max_discount: JsonDecimal | None = None
    scope_items: list[str] = Field(default_factory=list)
    scope_categories: list[str] = Field(default_factory=list)
    scope_brands: list[str] = Field(default_factory=list)
    scope_active_ingredients: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> PromotionCreate:
        if self.value <= 0:
            raise ValueError("value must be > 0")
        if self.discount_type == PromotionDiscountType.percent and self.value > Decimal("100"):
            raise ValueError("percent promotion value must be <= 100")
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.scope == PromotionScope.items and not self.scope_items:
            raise ValueError("scope_items required when scope='items'")
        if self.scope == PromotionScope.category and not self.scope_categories:
            raise ValueError("scope_categories required when scope='category'")
        if self.scope == PromotionScope.brand and not self.scope_brands:
            raise ValueError("scope_brands required when scope='brand'")
        if self.scope == PromotionScope.active_ingredient and not self.scope_active_ingredients:
            raise ValueError("scope_active_ingredients required when scope='active_ingredient'")
        if self.min_purchase is not None and self.min_purchase < 0:
            raise ValueError("min_purchase must be >= 0")
        if self.max_discount is not None and self.max_discount <= 0:
            raise ValueError("max_discount must be > 0")
        return self


class PromotionUpdate(BaseModel):
    """Request body for partial update. All fields optional."""

    model_config = ConfigDict(frozen=True)

    name: PromotionNameStr | None = None
    description: str | None = None
    discount_type: PromotionDiscountType | None = None
    value: JsonDecimal | None = None
    scope: PromotionScope | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    min_purchase: JsonDecimal | None = None
    max_discount: JsonDecimal | None = None
    scope_items: list[str] | None = None
    scope_categories: list[str] | None = None
    scope_brands: list[str] | None = None
    scope_active_ingredients: list[str] | None = None


class PromotionStatusUpdate(BaseModel):
    """Request body for ``PATCH /pos/promotions/{id}/status``."""

    model_config = ConfigDict(frozen=True)

    status: Literal["active", "paused"]


class PromotionResponse(BaseModel):
    """API response representing a single promotion."""

    model_config = ConfigDict(frozen=True)

    id: int
    tenant_id: int
    name: str
    description: str | None = None
    discount_type: PromotionDiscountType
    value: JsonDecimal
    scope: PromotionScope
    starts_at: datetime
    ends_at: datetime
    min_purchase: JsonDecimal | None = None
    max_discount: JsonDecimal | None = None
    status: PromotionStatus
    scope_items: list[str] = Field(default_factory=list)
    scope_categories: list[str] = Field(default_factory=list)
    scope_brands: list[str] = Field(default_factory=list)
    scope_active_ingredients: list[str] = Field(default_factory=list)
    usage_count: int = 0
    total_discount_given: JsonDecimal = Decimal("0")
    created_at: datetime


class EligibleCartItem(BaseModel):
    """One cart line sent to ``POST /pos/promotions/eligible`` for scoring.

    ``drug_brand`` is optional; when null the line cannot match ``scope='brand'``.
    ``active_ingredient`` is optional; when null the line cannot match
    ``scope='active_ingredient'`` (added in migration 106).
    """

    model_config = ConfigDict(frozen=True)

    drug_code: str
    drug_cluster: str | None = None
    drug_brand: str | None = None
    active_ingredient: str | None = None
    quantity: JsonDecimal
    unit_price: JsonDecimal


class EligiblePromotionsRequest(BaseModel):
    """Request body for ``POST /pos/promotions/eligible``."""

    model_config = ConfigDict(frozen=True)

    items: list[EligibleCartItem]
    subtotal: JsonDecimal


class EligiblePromotion(BaseModel):
    """One entry in the eligible-promotion response — promo + preview discount."""

    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    description: str | None = None
    discount_type: PromotionDiscountType
    value: JsonDecimal
    scope: PromotionScope
    min_purchase: JsonDecimal | None = None
    max_discount: JsonDecimal | None = None
    ends_at: datetime
    # Preview — what the cashier would see if they applied this promotion.
    preview_discount: JsonDecimal


class EligiblePromotionsResponse(BaseModel):
    """Response body for ``POST /pos/promotions/eligible``."""

    model_config = ConfigDict(frozen=True)

    promotions: list[EligiblePromotion]


class PreviewMatchesRequest(BaseModel):
    """Request body for ``POST /pos/promotions/preview-matches``.

    Returns the number of SKUs in the product catalog whose ``scope``-matched
    attribute contains any of the supplied ``values``.
    """

    model_config = ConfigDict(frozen=True)

    scope: PromotionScope
    values: list[str] = Field(min_length=1)


class PreviewMatchesResponse(BaseModel):
    """Response for ``POST /pos/promotions/preview-matches``."""

    model_config = ConfigDict(frozen=True)

    scope: PromotionScope
    values: list[str]
    matched_sku_count: int


class PromotionApplicationRow(BaseModel):
    """Audit row — one applied promotion attached to a transaction."""

    model_config = ConfigDict(frozen=True)

    id: int
    promotion_id: int
    transaction_id: int
    cashier_staff_id: str
    discount_applied: JsonDecimal
    applied_at: datetime

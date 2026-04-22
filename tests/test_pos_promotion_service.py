"""PromotionService unit tests — mocked repository only.

Covers compute_discount arithmetic, eligible_base scope resolution, and
the list_eligible preview discount pipeline.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.pos.models import (
    EligibleCartItem,
    EligiblePromotionsRequest,
    PromotionDiscountType,
    PromotionResponse,
    PromotionScope,
    PromotionStatus,
)
from datapulse.pos.promotion_service import PromotionService

pytestmark = pytest.mark.unit


def _promo(
    *,
    scope: PromotionScope = PromotionScope.all,
    discount_type: PromotionDiscountType = PromotionDiscountType.amount,
    value: Decimal = Decimal("10"),
    scope_items: list[str] | None = None,
    scope_categories: list[str] | None = None,
    scope_brands: list[str] | None = None,
    min_purchase: Decimal | None = None,
    max_discount: Decimal | None = None,
) -> PromotionResponse:
    return PromotionResponse(
        id=1,
        tenant_id=1,
        name="Test Promo",
        description=None,
        discount_type=discount_type,
        value=value,
        scope=scope,
        starts_at=datetime.now(UTC) - timedelta(days=1),
        ends_at=datetime.now(UTC) + timedelta(days=7),
        min_purchase=min_purchase,
        max_discount=max_discount,
        status=PromotionStatus.active,
        scope_items=scope_items or [],
        scope_categories=scope_categories or [],
        scope_brands=scope_brands or [],
        usage_count=0,
        total_discount_given=Decimal("0"),
        created_at=datetime.now(UTC),
    )


def _items(
    *triples: tuple[str, str | None, Decimal, Decimal]
    | tuple[str, str | None, Decimal, Decimal, str | None],
) -> list[EligibleCartItem]:
    """Build EligibleCartItem list.

    Each tuple is ``(drug_code, drug_cluster, qty, unit_price)`` or
    ``(drug_code, drug_cluster, qty, unit_price, drug_brand)``. The
    4-tuple form leaves drug_brand=None for backward-compatibility
    with the pre-migration-101 tests.
    """
    out: list[EligibleCartItem] = []
    for t in triples:
        if len(t) == 4:
            code, cluster, qty, price = t
            brand = None
        else:
            code, cluster, qty, price, brand = t
        out.append(
            EligibleCartItem(
                drug_code=code,
                drug_cluster=cluster,
                drug_brand=brand,
                quantity=qty,
                unit_price=price,
            )
        )
    return out


# ---------------------------------------------------------------------------
# compute_discount
# ---------------------------------------------------------------------------


def test_compute_discount_amount_caps_at_base() -> None:
    disc = PromotionService.compute_discount(
        PromotionDiscountType.amount, Decimal("50"), Decimal("20")
    )
    assert disc == Decimal("20.0000")


def test_compute_discount_percent() -> None:
    disc = PromotionService.compute_discount(
        PromotionDiscountType.percent, Decimal("15"), Decimal("200")
    )
    assert disc == Decimal("30.0000")


def test_compute_discount_max_discount_caps_percent() -> None:
    # 20% of 1000 = 200, capped at 50
    disc = PromotionService.compute_discount(
        PromotionDiscountType.percent,
        Decimal("20"),
        Decimal("1000"),
        max_discount=Decimal("50"),
    )
    assert disc == Decimal("50.0000")


def test_compute_discount_zero_base_returns_zero() -> None:
    assert PromotionService.compute_discount(
        PromotionDiscountType.amount, Decimal("10"), Decimal("0")
    ) == Decimal("0")


# ---------------------------------------------------------------------------
# eligible_base — scope resolution
# ---------------------------------------------------------------------------


def test_eligible_base_scope_all_sums_full_cart() -> None:
    items = _items(
        ("A", None, Decimal("2"), Decimal("10")),
        ("B", None, Decimal("1"), Decimal("5")),
    )
    base = PromotionService.eligible_base(_promo(scope=PromotionScope.all), items)
    assert base == Decimal("25")


def test_eligible_base_scope_items_sums_only_matching() -> None:
    promo = _promo(scope=PromotionScope.items, scope_items=["A"])
    items = _items(
        ("A", None, Decimal("2"), Decimal("10")),  # matches → 20
        ("B", None, Decimal("1"), Decimal("5")),  # skipped
    )
    base = PromotionService.eligible_base(promo, items)
    assert base == Decimal("20")


def test_eligible_base_scope_category_sums_only_matching_clusters() -> None:
    promo = _promo(scope=PromotionScope.category, scope_categories=["antibiotics"])
    items = _items(
        ("A", "antibiotics", Decimal("1"), Decimal("30")),
        ("B", "painkillers", Decimal("2"), Decimal("10")),
    )
    base = PromotionService.eligible_base(promo, items)
    assert base == Decimal("30")


def test_eligible_base_scope_brand_sums_only_matching_brands() -> None:
    """Brand scope (migration 101) — case-insensitive match on drug_brand."""
    promo = _promo(scope=PromotionScope.brand, scope_brands=["Bayer", "GSK"])
    items = _items(
        ("A", None, Decimal("2"), Decimal("15"), "BAYER"),  # case-insensitive → 30
        ("B", None, Decimal("1"), Decimal("20"), "Sanofi"),  # skipped
        ("C", None, Decimal("3"), Decimal("10"), "gsk"),     # case-insensitive → 30
        ("D", None, Decimal("1"), Decimal("5"), None),       # no brand → skipped
    )
    base = PromotionService.eligible_base(promo, items)
    assert base == Decimal("60")


def test_eligible_base_scope_brand_skips_when_no_brand_matches() -> None:
    promo = _promo(scope=PromotionScope.brand, scope_brands=["Novartis"])
    items = _items(
        ("A", None, Decimal("1"), Decimal("10"), "Bayer"),
        ("B", None, Decimal("1"), Decimal("10"), None),
    )
    assert PromotionService.eligible_base(promo, items) == Decimal("0")


# ---------------------------------------------------------------------------
# list_eligible — preview discount pipeline
# ---------------------------------------------------------------------------


def test_list_eligible_filters_out_zero_base_promotions() -> None:
    """scope='items' with no cart match yields base=0 and is skipped."""
    repo = MagicMock()
    repo.list_eligible.return_value = [
        _promo(scope=PromotionScope.items, scope_items=["OTHER"]),
    ]
    service = PromotionService(repo)
    resp = service.list_eligible(
        1,
        EligiblePromotionsRequest(
            items=_items(("A", None, Decimal("1"), Decimal("10"))),
            subtotal=Decimal("10"),
        ),
    )
    assert resp.promotions == []


def test_list_eligible_includes_preview_discount() -> None:
    repo = MagicMock()
    repo.list_eligible.return_value = [
        _promo(
            scope=PromotionScope.all,
            discount_type=PromotionDiscountType.percent,
            value=Decimal("10"),
        ),
    ]
    service = PromotionService(repo)
    resp = service.list_eligible(
        1,
        EligiblePromotionsRequest(
            items=_items(("A", None, Decimal("1"), Decimal("100"))),
            subtotal=Decimal("100"),
        ),
    )
    assert len(resp.promotions) == 1
    assert resp.promotions[0].preview_discount == Decimal("10.0000")


def test_list_eligible_passes_drug_codes_and_clusters_to_repo() -> None:
    repo = MagicMock()
    repo.list_eligible.return_value = []
    service = PromotionService(repo)
    service.list_eligible(
        42,
        EligiblePromotionsRequest(
            items=_items(
                ("A", "antibiotics", Decimal("1"), Decimal("10")),
                ("B", "painkillers", Decimal("2"), Decimal("5")),
            ),
            subtotal=Decimal("20"),
        ),
    )
    _, kwargs = repo.list_eligible.call_args
    assert kwargs["drug_codes"] == ["A", "B"]
    assert kwargs["drug_clusters"] == ["antibiotics", "painkillers"]
    assert kwargs["subtotal"] == Decimal("20")


# ---------------------------------------------------------------------------
# CRUD pass-throughs
# ---------------------------------------------------------------------------


def test_list_passes_status_filter_to_repository() -> None:
    repo = MagicMock()
    repo.list_for_tenant.return_value = []
    service = PromotionService(repo)
    service.list_all(1, status=PromotionStatus.active)
    repo.list_for_tenant.assert_called_once_with(1, status=PromotionStatus.active)


def test_set_status_passes_through_to_repository() -> None:
    repo = MagicMock()
    repo.set_status.return_value = _promo()
    service = PromotionService(repo)
    service.set_status(1, 5, PromotionStatus.paused)
    repo.set_status.assert_called_once_with(1, 5, PromotionStatus.paused)

"""Plan definitions and Stripe price-to-plan mapping."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanLimits:
    """Immutable plan limits — -1 means unlimited, 0 means disabled."""

    data_sources: int
    max_rows: int
    ai_insights: bool
    pipeline_automation: bool
    quality_gates: bool
    name: str
    price_display: str

    # Platform tier fields (pharmaceutical inventory & dispensing)
    inventory_management: bool = False
    expiry_tracking: bool = False
    dispensing_analytics: bool = False
    purchase_orders: bool = False
    pos_integration: bool = False
    max_stock_items: int = 0  # 0 = disabled, -1 = unlimited
    max_suppliers: int = 0  # 0 = disabled, -1 = unlimited
    stock_alerts: bool = False


PLAN_LIMITS: dict[str, PlanLimits] = {
    "starter": PlanLimits(
        data_sources=1,
        max_rows=10_000,
        ai_insights=False,
        pipeline_automation=False,
        quality_gates=False,
        name="Starter",
        price_display="$0/mo",
        inventory_management=False,
        expiry_tracking=False,
        dispensing_analytics=False,
        purchase_orders=False,
        pos_integration=False,
        max_stock_items=0,
        max_suppliers=0,
        stock_alerts=False,
    ),
    "pro": PlanLimits(
        data_sources=5,
        max_rows=1_000_000,
        ai_insights=True,
        pipeline_automation=True,
        quality_gates=True,
        name="Pro",
        price_display="$49/mo",
        inventory_management=True,
        expiry_tracking=True,
        dispensing_analytics=True,
        purchase_orders=True,
        pos_integration=False,
        max_stock_items=50_000,
        max_suppliers=500,
        stock_alerts=True,
    ),
    # Platform tier: Analytics + POS + Inventory for pharmaceutical operations.
    # Upsell path from Pro ($49) → Platform ($99). seeded by migration 075.
    "platform": PlanLimits(
        data_sources=5,
        max_rows=1_000_000,
        ai_insights=True,
        pipeline_automation=True,
        quality_gates=True,
        name="Platform",
        price_display="$99/mo",
        inventory_management=True,
        expiry_tracking=True,
        dispensing_analytics=True,
        purchase_orders=True,
        pos_integration=True,
        max_stock_items=100_000,
        max_suppliers=1_000,
        stock_alerts=True,
    ),
    "enterprise": PlanLimits(
        data_sources=-1,
        max_rows=-1,
        ai_insights=True,
        pipeline_automation=True,
        quality_gates=True,
        name="Enterprise",
        price_display="Custom",
        inventory_management=True,
        expiry_tracking=True,
        dispensing_analytics=True,
        purchase_orders=True,
        pos_integration=True,
        max_stock_items=-1,
        max_suppliers=-1,
        stock_alerts=True,
    ),
}

DEFAULT_PLAN = "starter"


def get_plan_limits(plan: str) -> PlanLimits:
    """Return limits for a plan, defaulting to starter for unknown plans."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[DEFAULT_PLAN])


def resolve_plan_from_price(price_id: str, price_to_plan: dict[str, str]) -> str:
    """Map a Stripe price ID to a plan name, defaulting to starter."""
    return price_to_plan.get(price_id, DEFAULT_PLAN)

"""Plan definitions and Stripe price-to-plan mapping."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanLimits:
    """Immutable plan limits — -1 means unlimited."""

    data_sources: int
    max_rows: int
    ai_insights: bool
    pipeline_automation: bool
    quality_gates: bool
    name: str
    price_display: str


PLAN_LIMITS: dict[str, PlanLimits] = {
    "starter": PlanLimits(
        data_sources=1,
        max_rows=10_000,
        ai_insights=False,
        pipeline_automation=False,
        quality_gates=False,
        name="Starter",
        price_display="$0/mo",
    ),
    "pro": PlanLimits(
        data_sources=5,
        max_rows=1_000_000,
        ai_insights=True,
        pipeline_automation=True,
        quality_gates=True,
        name="Pro",
        price_display="$49/mo",
    ),
    "enterprise": PlanLimits(
        data_sources=-1,
        max_rows=-1,
        ai_insights=True,
        pipeline_automation=True,
        quality_gates=True,
        name="Enterprise",
        price_display="Custom",
    ),
}

DEFAULT_PLAN = "starter"


def get_plan_limits(plan: str) -> PlanLimits:
    """Return limits for a plan, defaulting to starter for unknown plans."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[DEFAULT_PLAN])


def resolve_plan_from_price(price_id: str, price_to_plan: dict[str, str]) -> str:
    """Map a Stripe price ID to a plan name, defaulting to starter."""
    return price_to_plan.get(price_id, DEFAULT_PLAN)

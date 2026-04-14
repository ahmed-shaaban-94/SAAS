"""Tests for PlanLimits — pharmaceutical platform tier fields.

Covers:
  - All 8 new platform fields exist with correct default values
  - Tier assignments: starter (all disabled), pro (partial), enterprise (all enabled)
  - get_plan_limits() returns correct tier for known plans
  - Unknown plans fall back to starter defaults
  - PlanLimits remains frozen (immutable)
"""

from __future__ import annotations

import pytest

from datapulse.billing.plans import (
    DEFAULT_PLAN,
    PLAN_LIMITS,
    PlanLimits,
    get_plan_limits,
)

# ---------------------------------------------------------------------------
# PlanLimits — field presence and defaults
# ---------------------------------------------------------------------------


class TestPlanLimitsFields:
    """Verify new platform fields exist with correct defaults."""

    def test_inventory_management_default_false(self):
        limits = PlanLimits(
            data_sources=1,
            max_rows=1000,
            ai_insights=False,
            pipeline_automation=False,
            quality_gates=False,
            name="Test",
            price_display="$0",
        )
        assert limits.inventory_management is False

    def test_expiry_tracking_default_false(self):
        limits = PlanLimits(
            data_sources=1,
            max_rows=1000,
            ai_insights=False,
            pipeline_automation=False,
            quality_gates=False,
            name="Test",
            price_display="$0",
        )
        assert limits.expiry_tracking is False

    def test_dispensing_analytics_default_false(self):
        limits = PlanLimits(
            data_sources=1,
            max_rows=1000,
            ai_insights=False,
            pipeline_automation=False,
            quality_gates=False,
            name="Test",
            price_display="$0",
        )
        assert limits.dispensing_analytics is False

    def test_purchase_orders_default_false(self):
        limits = PlanLimits(
            data_sources=1,
            max_rows=1000,
            ai_insights=False,
            pipeline_automation=False,
            quality_gates=False,
            name="Test",
            price_display="$0",
        )
        assert limits.purchase_orders is False

    def test_pos_integration_default_false(self):
        limits = PlanLimits(
            data_sources=1,
            max_rows=1000,
            ai_insights=False,
            pipeline_automation=False,
            quality_gates=False,
            name="Test",
            price_display="$0",
        )
        assert limits.pos_integration is False

    def test_max_stock_items_default_zero(self):
        limits = PlanLimits(
            data_sources=1,
            max_rows=1000,
            ai_insights=False,
            pipeline_automation=False,
            quality_gates=False,
            name="Test",
            price_display="$0",
        )
        assert limits.max_stock_items == 0

    def test_max_suppliers_default_zero(self):
        limits = PlanLimits(
            data_sources=1,
            max_rows=1000,
            ai_insights=False,
            pipeline_automation=False,
            quality_gates=False,
            name="Test",
            price_display="$0",
        )
        assert limits.max_suppliers == 0

    def test_stock_alerts_default_false(self):
        limits = PlanLimits(
            data_sources=1,
            max_rows=1000,
            ai_insights=False,
            pipeline_automation=False,
            quality_gates=False,
            name="Test",
            price_display="$0",
        )
        assert limits.stock_alerts is False

    def test_plan_limits_is_frozen(self):
        limits = PlanLimits(
            data_sources=1,
            max_rows=1000,
            ai_insights=False,
            pipeline_automation=False,
            quality_gates=False,
            name="Test",
            price_display="$0",
        )
        with pytest.raises((AttributeError, TypeError)):
            limits.inventory_management = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tier assignments
# ---------------------------------------------------------------------------


class TestStarterTier:
    """Starter plan has all platform features disabled."""

    def setup_method(self):
        self.limits = PLAN_LIMITS["starter"]

    def test_inventory_management_disabled(self):
        assert self.limits.inventory_management is False

    def test_expiry_tracking_disabled(self):
        assert self.limits.expiry_tracking is False

    def test_dispensing_analytics_disabled(self):
        assert self.limits.dispensing_analytics is False

    def test_purchase_orders_disabled(self):
        assert self.limits.purchase_orders is False

    def test_pos_integration_disabled(self):
        assert self.limits.pos_integration is False

    def test_max_stock_items_zero(self):
        assert self.limits.max_stock_items == 0

    def test_max_suppliers_zero(self):
        assert self.limits.max_suppliers == 0

    def test_stock_alerts_disabled(self):
        assert self.limits.stock_alerts is False


class TestProTier:
    """Pro plan has core inventory features but no POS integration."""

    def setup_method(self):
        self.limits = PLAN_LIMITS["pro"]

    def test_inventory_management_enabled(self):
        assert self.limits.inventory_management is True

    def test_expiry_tracking_enabled(self):
        assert self.limits.expiry_tracking is True

    def test_dispensing_analytics_enabled(self):
        assert self.limits.dispensing_analytics is True

    def test_purchase_orders_enabled(self):
        assert self.limits.purchase_orders is True

    def test_pos_integration_disabled(self):
        assert self.limits.pos_integration is False

    def test_max_stock_items_limited(self):
        assert self.limits.max_stock_items == 50_000

    def test_max_suppliers_limited(self):
        assert self.limits.max_suppliers == 500

    def test_stock_alerts_enabled(self):
        assert self.limits.stock_alerts is True


class TestEnterpriseTier:
    """Enterprise plan has all platform features enabled with no limits."""

    def setup_method(self):
        self.limits = PLAN_LIMITS["enterprise"]

    def test_inventory_management_enabled(self):
        assert self.limits.inventory_management is True

    def test_expiry_tracking_enabled(self):
        assert self.limits.expiry_tracking is True

    def test_dispensing_analytics_enabled(self):
        assert self.limits.dispensing_analytics is True

    def test_purchase_orders_enabled(self):
        assert self.limits.purchase_orders is True

    def test_pos_integration_enabled(self):
        assert self.limits.pos_integration is True

    def test_max_stock_items_unlimited(self):
        assert self.limits.max_stock_items == -1

    def test_max_suppliers_unlimited(self):
        assert self.limits.max_suppliers == -1

    def test_stock_alerts_enabled(self):
        assert self.limits.stock_alerts is True


# ---------------------------------------------------------------------------
# get_plan_limits() helper
# ---------------------------------------------------------------------------


class TestGetPlanLimits:
    """get_plan_limits() returns correct tier and falls back gracefully."""

    def test_starter_returns_starter_limits(self):
        limits = get_plan_limits("starter")
        assert limits.inventory_management is False
        assert limits.name == "Starter"

    def test_pro_returns_pro_limits(self):
        limits = get_plan_limits("pro")
        assert limits.inventory_management is True
        assert limits.name == "Pro"

    def test_enterprise_returns_enterprise_limits(self):
        limits = get_plan_limits("enterprise")
        assert limits.pos_integration is True
        assert limits.name == "Enterprise"

    def test_unknown_plan_falls_back_to_starter(self):
        limits = get_plan_limits("unknown_plan")
        assert limits == PLAN_LIMITS[DEFAULT_PLAN]
        assert limits.inventory_management is False

    def test_empty_string_falls_back_to_starter(self):
        limits = get_plan_limits("")
        assert limits == PLAN_LIMITS[DEFAULT_PLAN]

    def test_all_tiers_present_in_plan_limits(self):
        assert "starter" in PLAN_LIMITS
        assert "pro" in PLAN_LIMITS
        assert "enterprise" in PLAN_LIMITS

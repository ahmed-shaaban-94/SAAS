# tests/test_plan_limits_egp.py
"""EGP pricing fields on PlanLimits (#604 Spec 1 PR 3)."""

from datapulse.billing.plans import PLAN_LIMITS, get_plan_limits


class TestPlanLimitsEgp:
    def test_pro_has_egp_price(self):
        pro = get_plan_limits("pro")
        assert pro.price_egp == 149_900  # piastres → 1,499 EGP
        assert pro.price_currency_default == "USD"

    def test_platform_has_egp_price(self):
        plat = get_plan_limits("platform")
        assert plat.price_egp == 299_900  # piastres → 2,999 EGP

    def test_starter_egp_zero(self):
        starter = get_plan_limits("starter")
        assert starter.price_egp == 0

    def test_every_plan_has_egp_field(self):
        for name, limits in PLAN_LIMITS.items():
            assert hasattr(limits, "price_egp"), f"{name} missing price_egp"
            assert hasattr(limits, "price_currency_default"), (
                f"{name} missing price_currency_default"
            )

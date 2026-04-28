"""M9 — SplitPaymentProcessor._GATEWAYS must be per-instance, not class-level.

A class-level mutable dict is shared across all instances.  Adding or removing
a gateway on one instance would corrupt every other instance.  The fix moves
the dict to __init__ so each instance owns its own copy.
"""

from __future__ import annotations

import pytest

from datapulse.pos.payment import SplitPaymentProcessor

pytestmark = pytest.mark.unit


class TestSplitPaymentProcessorIsolation:
    """M9: two instances must not share gateway state."""

    def test_two_instances_have_independent_gateway_dicts(self) -> None:
        """Mutating one instance's _GATEWAYS does not affect a second instance."""
        p1 = SplitPaymentProcessor()
        p2 = SplitPaymentProcessor()

        # Inject a sentinel into p1's gateway dict
        p1._GATEWAYS["__sentinel__"] = object()  # type: ignore[assignment]

        assert "__sentinel__" not in p2._GATEWAYS, (
            "_GATEWAYS is shared at class level — it must be per-instance"
        )

    def test_instance_gateways_not_same_object(self) -> None:
        """The _GATEWAYS dict on two instances must be different objects."""
        p1 = SplitPaymentProcessor()
        p2 = SplitPaymentProcessor()

        assert p1._GATEWAYS is not p2._GATEWAYS, (
            "_GATEWAYS dict is the same object on both instances — not isolated"
        )

    def test_default_gateways_present_after_init(self) -> None:
        """After __init__, the expected default gateways are present."""
        p = SplitPaymentProcessor()

        assert "cash" in p._GATEWAYS, "cash gateway missing after __init__"
        assert "insurance" in p._GATEWAYS, "insurance gateway missing after __init__"

    def test_class_gateways_not_contaminated_by_instance_mutation(self) -> None:
        """Mutating an instance dict must not change the class-level attribute."""
        p = SplitPaymentProcessor()
        p._GATEWAYS["__test__"] = object()  # type: ignore[assignment]

        class_gateways = SplitPaymentProcessor.__dict__.get("_GATEWAYS", {})
        assert "__test__" not in class_gateways, (
            "Instance mutation leaked into SplitPaymentProcessor class dict"
        )

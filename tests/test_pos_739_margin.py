"""Unit tests for issue #739 — cost_per_unit on transaction_items + agg_basket_margin.

Tests:
- PosCartItem accepts cost_per_unit without error (new optional field)
- Migration 119 SQL is idempotent (the DO $$ block is safe to run twice)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from datapulse.pos.models.cart import PosCartItem

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# PosCartItem model tests
# ---------------------------------------------------------------------------


class TestPosCartItemCostField:
    def test_cart_item_accepts_cost_per_unit(self) -> None:
        """PosCartItem can be constructed with an explicit cost_per_unit."""
        item = PosCartItem(
            drug_code="DRUG001",
            drug_name="Test Drug",
            quantity=Decimal("2"),
            unit_price=Decimal("10.0000"),
            line_total=Decimal("20.0000"),
            cost_per_unit=Decimal("6.0000"),
        )
        assert item.cost_per_unit == Decimal("6.0000")

    def test_cart_item_cost_per_unit_defaults_to_none(self) -> None:
        """cost_per_unit is optional; omitting it gives None (backward compat)."""
        item = PosCartItem(
            drug_code="DRUG001",
            drug_name="Test Drug",
            quantity=Decimal("1"),
            unit_price=Decimal("5.0000"),
            line_total=Decimal("5.0000"),
        )
        assert item.cost_per_unit is None

    def test_cart_item_cost_per_unit_accepts_none_explicitly(self) -> None:
        """Passing cost_per_unit=None is accepted and remains None."""
        item = PosCartItem(
            drug_code="DRUG002",
            drug_name="Another Drug",
            quantity=Decimal("3"),
            unit_price=Decimal("7.5000"),
            line_total=Decimal("22.5000"),
            cost_per_unit=None,
        )
        assert item.cost_per_unit is None

    def test_cart_item_is_frozen(self) -> None:
        """PosCartItem is immutable — attribute assignment should raise ValidationError."""
        from pydantic import ValidationError

        item = PosCartItem(
            drug_code="DRUG001",
            drug_name="Test Drug",
            quantity=Decimal("1"),
            unit_price=Decimal("5.0000"),
            line_total=Decimal("5.0000"),
            cost_per_unit=Decimal("3.0000"),
        )
        with pytest.raises(ValidationError):
            # Pydantic v2 frozen models raise ValidationError on direct attribute assignment
            item.cost_per_unit = Decimal("4.0000")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Migration idempotency test
# ---------------------------------------------------------------------------


class TestMigration119Idempotent:
    def test_migration_sql_contains_idempotency_guard(self) -> None:
        """Migration 119 SQL must contain an IF NOT EXISTS guard.

        This is a static analysis test — it reads the file and asserts the
        presence of the idempotency pattern so that CI catches regressions
        without needing a live database.
        """
        import pathlib

        migration_path = (
            pathlib.Path(__file__).parent.parent / "migrations" / "119_transaction_items_cost.sql"
        )
        assert migration_path.exists(), "Migration file 119 not found"
        sql = migration_path.read_text(encoding="utf-8")

        assert "IF NOT EXISTS" in sql, "Migration must use IF NOT EXISTS for idempotency"
        assert "cost_per_unit" in sql, "Migration must add cost_per_unit column"
        assert "NUMERIC(18,4)" in sql, "cost_per_unit must use NUMERIC(18,4) precision"

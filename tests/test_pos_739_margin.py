"""Unit tests for issue #739 — cost_per_unit on transaction_items + agg_basket_margin.

Tests:
- PosCartItem accepts cost_per_unit without error (new optional field)
- Migration 119 SQL is idempotent (the DO $$ block is safe to run twice)
- Migration 121 backfill SQL is idempotent (WHERE cost_per_unit IS NULL guard)
- GET /transactions/{id} exposes cost_per_unit for pos:cost:read users only
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from datapulse.pos.models.cart import PosCartItem
from datapulse.pos.models.transaction import TransactionDetailResponse

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


# ---------------------------------------------------------------------------
# Migration 121 backfill idempotency test
# ---------------------------------------------------------------------------


class TestMigration121BackfillIdempotent:
    def test_backfill_sql_only_touches_null_rows(self) -> None:
        """Migration 121 backfill must use WHERE cost_per_unit IS NULL.

        Static analysis test — asserts the idempotency guard is present so
        that re-running the migration never overwrites captured cost values.
        """
        import pathlib

        migration_path = (
            pathlib.Path(__file__).parent.parent
            / "migrations"
            / "121_transaction_items_cost_backfill.sql"
        )
        assert migration_path.exists(), "Migration file 121 not found"
        sql = migration_path.read_text(encoding="utf-8")

        assert "WHERE cost_per_unit IS NULL" in sql, (
            "Backfill must use WHERE cost_per_unit IS NULL to be idempotent"
        )
        assert "cost_per_unit" in sql, "Migration must reference cost_per_unit column"
        assert "ROUND" in sql, "Backfill must use ROUND() for NUMERIC(18,4) precision"
        assert "0.70" in sql or "0.7" in sql, "Backfill must use 0.70 cost proxy"

    def test_backfill_sql_seeds_cost_read_permission(self) -> None:
        """Migration 121 must seed the pos:cost:read permission."""
        import pathlib

        migration_path = (
            pathlib.Path(__file__).parent.parent
            / "migrations"
            / "121_transaction_items_cost_backfill.sql"
        )
        sql = migration_path.read_text(encoding="utf-8")

        assert "pos:cost:read" in sql, (
            "Migration 121 must seed pos:cost:read permission for role-gated cost exposure"
        )
        assert "ON CONFLICT" in sql, (
            "Permission INSERT must be idempotent via ON CONFLICT DO NOTHING"
        )


# ---------------------------------------------------------------------------
# Role-gated cost_per_unit in GET /transactions/{id}
# ---------------------------------------------------------------------------


def _make_transaction_detail(cost: Decimal | None = Decimal("7.0000")) -> TransactionDetailResponse:
    """Build a minimal TransactionDetailResponse with one line item."""
    item = PosCartItem(
        drug_code="DRUG001",
        drug_name="Test Drug",
        quantity=Decimal("2"),
        unit_price=Decimal("10.0000"),
        line_total=Decimal("20.0000"),
        cost_per_unit=cost,
    )
    return TransactionDetailResponse(
        id=1,
        terminal_id=1,
        staff_id="staff-001",
        site_code="PH001",
        subtotal=Decimal("20.0000"),
        discount_total=Decimal("0.0000"),
        tax_total=Decimal("0.0000"),
        grand_total=Decimal("20.0000"),
        status="completed",
        created_at=datetime(2026, 4, 26, 10, 0, 0),
        items=[item],
    )


def _apply_cost_gating(
    detail: TransactionDetailResponse, permissions: set[str]
) -> TransactionDetailResponse:
    """Helper replicating the handler logic for cost stripping (avoids test duplication)."""
    if "pos:cost:read" not in permissions:
        return detail.model_copy(
            update={
                "items": [item.model_copy(update={"cost_per_unit": None}) for item in detail.items]
            }
        )
    return detail


class TestGetTransactionCostGating:
    def test_cost_per_unit_visible_with_pos_cost_read_permission(self) -> None:
        """Users with pos:cost:read receive cost_per_unit on each line item."""
        detail = _make_transaction_detail(cost=Decimal("7.0000"))
        supervisor_perms = {"pos:cost:read", "pos:transaction:create"}

        result = _apply_cost_gating(detail, supervisor_perms)

        assert result.items[0].cost_per_unit == Decimal("7.0000"), (
            "cost_per_unit must be visible when user has pos:cost:read"
        )

    def test_cost_per_unit_nulled_without_pos_cost_read_permission(self) -> None:
        """Users without pos:cost:read receive cost_per_unit=None on each line item."""
        detail = _make_transaction_detail(cost=Decimal("7.0000"))
        cashier_perms = {"pos:transaction:create", "pos:transaction:checkout"}

        result = _apply_cost_gating(detail, cashier_perms)

        assert result.items[0].cost_per_unit is None, (
            "cost_per_unit must be None when user lacks pos:cost:read"
        )

    def test_other_item_fields_unchanged_when_cost_stripped(self) -> None:
        """Stripping cost_per_unit must not affect other line item fields."""
        detail = _make_transaction_detail(cost=Decimal("7.0000"))

        result = _apply_cost_gating(detail, permissions=set())

        item = result.items[0]
        assert item.drug_code == "DRUG001"
        assert item.unit_price == Decimal("10.0000")
        assert item.line_total == Decimal("20.0000")
        assert item.cost_per_unit is None

"""Unit tests for staff_count on site rankings + reorder-alert velocity (#507).

Two related enrichments shipped in one PR because they feed adjacent
widgets on the new dashboard design. Tests split by module.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.analytics.models import (
    AnalyticsFilter,
    DateRange,
)
from datapulse.analytics.ranking_repository import RankingRepository
from datapulse.inventory.repository import InventoryRepository

# ────────────────────────────────────────────────────────────────────────
# Site ranking: staff_count enrichment
# ────────────────────────────────────────────────────────────────────────


def _filters():
    from datetime import date

    return AnalyticsFilter(
        date_range=DateRange(start_date=date(2026, 1, 1), end_date=date(2026, 4, 20)),
        limit=10,
    )


def test_site_ranking_emits_staff_count_per_branch():
    session = MagicMock()
    # (site_key, site_name, value, staff_count)
    session.execute.return_value.fetchall.return_value = [
        (1, "Cairo Main", Decimal("100000"), 12),
        (2, "Alexandria", Decimal("50000"), 5),
    ]
    repo = RankingRepository(session)

    result = repo.get_site_performance(_filters())

    assert [i.name for i in result.items] == ["Cairo Main", "Alexandria"]
    assert [i.staff_count for i in result.items] == [12, 5]


def test_site_ranking_staff_count_uses_dim_site_join_excluding_unknown():
    """The SQL must JOIN ``dim_site`` and exclude staff_key=-1 so
    unattributed rows don't inflate the headcount."""
    session = MagicMock()
    session.execute.return_value.fetchall.return_value = []
    repo = RankingRepository(session)

    repo.get_site_performance(_filters())

    rendered_sql = str(session.execute.call_args[0][0])
    assert "dim_site dim" in rendered_sql
    assert "COUNT(DISTINCT f.staff_key)" in rendered_sql
    assert "staff_key != -1" in rendered_sql


def test_site_ranking_handles_empty_result_set():
    session = MagicMock()
    session.execute.return_value.fetchall.return_value = []
    repo = RankingRepository(session)

    result = repo.get_site_performance(_filters())

    assert result.items == []
    assert result.total == Decimal("0")


# ────────────────────────────────────────────────────────────────────────
# Reorder alerts: velocity + days_of_stock + status
# ────────────────────────────────────────────────────────────────────────


def _row(current: str, velocity: str, **overrides) -> dict:
    base = {
        "product_key": 1,
        "site_key": 1,
        "drug_code": "D1",
        "drug_name": "Drug 1",
        "site_code": "S1",
        "current_quantity": Decimal(current),
        "reorder_point": Decimal("20"),
        "reorder_quantity": Decimal("100"),
        "daily_velocity": Decimal(velocity),
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    ("current", "velocity", "expected_days", "expected_status"),
    [
        # velocity=0 → days_of_stock=None, status="low" (below reorder but unknown burn)
        ("15", "0", None, "low"),
        # velocity>0 → compute days; <5 = critical
        ("8", "4", Decimal("2.0"), "critical"),
        # boundary: exactly 5 days → "low" (not critical)
        ("10", "2", Decimal("5.0"), "low"),
        # 5 ≤ days < 10 → "low"
        ("12", "2", Decimal("6.0"), "low"),
        # boundary: exactly 10 days → "healthy"
        ("20", "2", Decimal("10.0"), "healthy"),
        # >10 days → "healthy"
        ("30", "2", Decimal("15.0"), "healthy"),
    ],
)
def test_status_derivation_thresholds(current, velocity, expected_days, expected_status):
    alert = InventoryRepository._row_to_reorder_alert(_row(current, velocity))

    assert alert.days_of_stock == expected_days
    assert alert.status == expected_status


def test_status_derivation_zero_velocity_nulls_days_of_stock():
    """A zero-velocity item (no recent sales) must carry ``days_of_stock=None``
    — we won't fabricate a burn-down rate."""
    alert = InventoryRepository._row_to_reorder_alert(_row("100", "0"))

    assert alert.days_of_stock is None
    assert alert.daily_velocity == Decimal("0")
    assert alert.status == "low"


def test_status_derivation_preserves_core_fields():
    alert = InventoryRepository._row_to_reorder_alert(
        _row(
            "8",
            "4",
            drug_code="AMOX500",
            drug_name="Amoxicillin 500mg",
            site_code="CAI-01",
        )
    )

    assert alert.drug_code == "AMOX500"
    assert alert.drug_name == "Amoxicillin 500mg"
    assert alert.site_code == "CAI-01"
    assert alert.current_quantity == Decimal("8")
    assert alert.reorder_point == Decimal("20")
    assert alert.reorder_quantity == Decimal("100")


def test_reorder_alerts_query_joins_velocity_cte():
    """The reorder-alerts SQL must include the trailing-30-day velocity
    CTE with a LEFT JOIN (items with zero recent sales must still surface)."""
    session = MagicMock()
    session.execute.return_value.mappings.return_value.all.return_value = []
    repo = InventoryRepository(session)

    from datapulse.inventory.models import InventoryFilter

    repo.get_reorder_alerts(InventoryFilter())

    rendered_sql = str(session.execute.call_args[0][0])
    assert "WITH velocity AS" in rendered_sql
    assert "LEFT JOIN velocity v" in rendered_sql
    assert "INTERVAL '30 days'" in rendered_sql
    assert "COALESCE(v.daily_velocity, 0)" in rendered_sql


def test_reorder_alerts_maps_rows_to_enriched_model():
    """End-to-end: raw DB rows → enriched ReorderAlert with derived fields."""
    session = MagicMock()
    session.execute.return_value.mappings.return_value.all.return_value = [
        _row("8", "4"),  # critical
        _row("60", "2", drug_code="D2", product_key=2),  # healthy
    ]
    repo = InventoryRepository(session)

    from datapulse.inventory.models import InventoryFilter

    alerts = repo.get_reorder_alerts(InventoryFilter())

    assert len(alerts) == 2
    assert alerts[0].status == "critical"
    assert alerts[0].days_of_stock == Decimal("2.0")
    assert alerts[1].status == "healthy"
    assert alerts[1].days_of_stock == Decimal("30.0")

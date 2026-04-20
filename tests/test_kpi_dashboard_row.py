"""Unit tests for the new dashboard KPI row fields (#503).

Covers:
- 11-point trailing sparkline window + per-metric ``sparklines`` list.
- Route-level enrichment of ``stock_risk_count`` / ``expiry_exposure_egp``
  gated on ``PlanLimits``.
- Degraded path when inventory/expiry services fail.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from datapulse.analytics.kpi_repository import KpiRepository
from datapulse.analytics.models import KPISparkline, KPISummary, TimeSeriesPoint
from datapulse.api.routes.analytics.kpi import _enrich_kpi_row
from datapulse.billing.plans import PlanLimits
from datapulse.expiry.models import ExpirySummary
from datapulse.inventory.models import ReorderAlert

# ────────────────────────────────────────────────────────────────────────
# KpiRepository.get_kpi_summary — per-metric sparklines (#503)
# ────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def kpi_repo(mock_session):
    return KpiRepository(mock_session)


def _build_row(*, sparkline_points=None, orders_points=None, **overrides):
    """Shared unified-CTE row shape."""
    base = {
        "daily_gross_amount": 1000,
        "daily_discount": 0,
        "daily_quantity": 100,
        "mtd_gross_amount": 25000,
        "ytd_gross_amount": 300000,
        "daily_transactions": 42,
        "daily_unique_customers": 15,
        "daily_returns": 3,
        "mtd_transactions": 420,
        "ytd_transactions": 5000,
        "avg_basket_size": Decimal("595.24"),
        "prev_month_mtd": 20000,
        "prev_year_ytd": 250000,
        "sparkline_points": sparkline_points,
        "sparkline_orders_points": orders_points,
    }
    base.update(overrides)
    return base


def test_sparkline_window_is_eleven_trailing_days(kpi_repo, mock_session):
    """The unified CTE must be parameterised for an 11-point window."""
    mock_session.execute.return_value.mappings.return_value.fetchone.return_value = _build_row()

    target = date(2025, 6, 15)
    kpi_repo.get_kpi_summary(target)

    (_, bind_params) = mock_session.execute.call_args[0]
    assert bind_params["target_date"] == target
    # 11-point window → start = target - 10 days (inclusive endpoints).
    assert bind_params["sparkline_start"] == target - timedelta(days=10)


def test_sparklines_list_contains_revenue_and_orders(kpi_repo, mock_session):
    """Repository must emit a KPISparkline for revenue and orders."""
    revenue_points = [
        {"period": "2025-06-05", "value": 800},
        {"period": "2025-06-06", "value": 900},
        {"period": "2025-06-07", "value": 1000},
    ]
    orders_points = [
        {"period": "2025-06-05", "value": 40},
        {"period": "2025-06-06", "value": 42},
        {"period": "2025-06-07", "value": 45},
    ]
    row = _build_row(sparkline_points=revenue_points, orders_points=orders_points)
    mock_session.execute.return_value.mappings.return_value.fetchone.return_value = row

    result = kpi_repo.get_kpi_summary(date(2025, 6, 15))

    # Legacy sparkline field retained for AI Light / n8n consumers.
    assert len(result.sparkline) == 3
    assert result.sparkline[0] == TimeSeriesPoint(period="2025-06-05", value=Decimal("800"))

    # New per-metric sparklines list.
    metrics = {s.metric: s for s in result.sparklines}
    assert set(metrics) == {"revenue", "orders"}
    assert len(metrics["revenue"].points) == 3
    assert metrics["orders"].points[-1] == TimeSeriesPoint(period="2025-06-07", value=Decimal("45"))


def test_sparklines_empty_when_payload_missing(kpi_repo, mock_session):
    """Missing JSON aggregates must yield empty series — not crash."""
    mock_session.execute.return_value.mappings.return_value.fetchone.return_value = _build_row()

    result = kpi_repo.get_kpi_summary(date(2025, 6, 15))

    assert result.sparkline == []
    metrics = {s.metric: s for s in result.sparklines}
    assert metrics["revenue"].points == []
    assert metrics["orders"].points == []


def test_sparklines_accept_json_string_payload(kpi_repo, mock_session):
    """Drivers that return JSON as a string must be parsed transparently."""
    import json

    row = _build_row(
        sparkline_points=json.dumps([{"period": "2025-06-05", "value": 800}]),
        orders_points=json.dumps([{"period": "2025-06-05", "value": 40}]),
    )
    mock_session.execute.return_value.mappings.return_value.fetchone.return_value = row

    result = kpi_repo.get_kpi_summary(date(2025, 6, 15))

    assert result.sparkline[0].value == Decimal("800")
    assert result.sparklines[1].points[0].value == Decimal("40")


def test_no_data_returns_empty_sparklines(kpi_repo, mock_session):
    """The no-data branch returns a KPISummary with empty series."""
    mock_session.execute.return_value.mappings.return_value.fetchone.return_value = None

    result = kpi_repo.get_kpi_summary(date(2025, 1, 15))

    assert result.sparkline == []
    assert result.sparklines == []  # unified no-data branch returns empty list


# ────────────────────────────────────────────────────────────────────────
# Route enrichment — _enrich_kpi_row (#503)
# ────────────────────────────────────────────────────────────────────────


def _empty_summary() -> KPISummary:
    return KPISummary(
        today_gross=Decimal("0"),
        mtd_gross=Decimal("0"),
        ytd_gross=Decimal("0"),
        daily_transactions=0,
        daily_customers=0,
        sparklines=[KPISparkline(metric="revenue"), KPISparkline(metric="orders")],
    )


def _plan(inventory: bool, expiry: bool) -> PlanLimits:
    return PlanLimits(
        data_sources=1,
        max_rows=1_000,
        ai_insights=False,
        pipeline_automation=False,
        quality_gates=False,
        name="test",
        price_display="$0/mo",
        inventory_management=inventory,
        expiry_tracking=expiry,
    )


def _plan_free() -> PlanLimits:
    return _plan(inventory=False, expiry=False)


def _plan_full() -> PlanLimits:
    return _plan(inventory=True, expiry=True)


def _reorder_alert(drug_code: str) -> ReorderAlert:
    return ReorderAlert(
        product_key=1,
        site_key=1,
        drug_code=drug_code,
        drug_name=drug_code,
        site_code="S1",
        current_quantity=Decimal("0"),
        reorder_point=Decimal("10"),
        reorder_quantity=Decimal("50"),
    )


def _expiry_row(bucket: str, value: Decimal, batches: int) -> ExpirySummary:
    return ExpirySummary(
        site_key=1,
        site_code="S1",
        site_name="Site 1",
        expiry_bucket=bucket,
        batch_count=batches,
        total_quantity=Decimal("0"),
        total_value=value,
    )


def test_enrich_kpi_row_skips_when_plan_disallows_both():
    """Free plans see zeros — auxiliary services must not be queried."""
    inventory = MagicMock()
    expiry = MagicMock()

    summary = _enrich_kpi_row(_empty_summary(), _plan_free(), inventory, expiry)

    assert summary.stock_risk_count == 0
    assert summary.expiry_exposure_egp == Decimal("0")
    inventory.get_reorder_alerts.assert_not_called()
    expiry.get_expiry_summary.assert_not_called()


def test_enrich_kpi_row_populates_stock_risk_when_plan_allows():
    inventory = MagicMock()
    inventory.get_reorder_alerts.return_value = [
        _reorder_alert("D1"),
        _reorder_alert("D2"),
        _reorder_alert("D3"),
    ]
    expiry = MagicMock()
    expiry.get_expiry_summary.return_value = []

    summary = _enrich_kpi_row(_empty_summary(), _plan_full(), inventory, expiry)

    assert summary.stock_risk_count == 3


def test_enrich_kpi_row_sums_near_expiry_exposure_only():
    """Only ``near_expiry`` bucket contributes to exposure — stale / active excluded."""
    inventory = MagicMock()
    inventory.get_reorder_alerts.return_value = []
    expiry = MagicMock()
    expiry.get_expiry_summary.return_value = [
        _expiry_row("active", Decimal("100000"), 10),  # excluded
        _expiry_row("near_expiry", Decimal("12000"), 4),
        _expiry_row("near_expiry", Decimal("3000"), 2),
        _expiry_row("expired", Decimal("500"), 1),  # excluded
    ]

    summary = _enrich_kpi_row(_empty_summary(), _plan_full(), inventory, expiry)

    assert summary.expiry_exposure_egp == Decimal("15000")
    assert summary.expiry_batch_count == 6


def test_enrich_kpi_row_tolerates_auxiliary_failures():
    """A broken inventory/expiry service must not break the dashboard."""
    inventory = MagicMock()
    inventory.get_reorder_alerts.side_effect = RuntimeError("db down")
    expiry = MagicMock()
    expiry.get_expiry_summary.side_effect = RuntimeError("db down")

    summary = _enrich_kpi_row(_empty_summary(), _plan_full(), inventory, expiry)

    # Degrades gracefully to defaults.
    assert summary.stock_risk_count == 0
    assert summary.expiry_exposure_egp == Decimal("0")
    assert summary.expiry_batch_count == 0


def test_enrich_kpi_row_preserves_core_fields():
    """Enrichment must not disturb the core analytics KPIs."""
    base = _empty_summary().model_copy(
        update={
            "today_gross": Decimal("1000"),
            "mtd_gross": Decimal("25000"),
            "period_gross": Decimal("1000"),
            "daily_transactions": 39,
        }
    )
    inventory = MagicMock()
    inventory.get_reorder_alerts.return_value = [_reorder_alert("D1")]
    expiry = MagicMock()
    expiry.get_expiry_summary.return_value = [
        _expiry_row("near_expiry", Decimal("500"), 1),
    ]

    summary = _enrich_kpi_row(base, _plan_full(), inventory, expiry)

    assert summary.today_gross == Decimal("1000")
    assert summary.mtd_gross == Decimal("25000")
    assert summary.period_gross == Decimal("1000")
    assert summary.daily_transactions == 39
    assert summary.stock_risk_count == 1
    assert summary.expiry_exposure_egp == Decimal("500")

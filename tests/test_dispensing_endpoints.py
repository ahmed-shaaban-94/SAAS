"""Tests for dispensing analytics API endpoints — plan gating, RBAC, response shapes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_dispensing_service, get_tenant_plan_limits
from datapulse.billing.plans import PLAN_LIMITS
from datapulse.dispensing.models import (
    DaysOfStock,
    DispenseRate,
    StockoutRisk,
    VelocityClassification,
)
from datapulse.dispensing.service import DispensingService
from datapulse.inventory.models import StockReconciliation
from datapulse.rbac.dependencies import get_access_context
from datapulse.rbac.models import AccessContext

MOCK_USER = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "preferred_username": "test",
    "tenant_id": "1",
    "roles": ["admin"],
    "raw_claims": {},
}

_ADMIN_CTX = AccessContext(
    member_id=1,
    tenant_id=1,
    user_id="test-user",
    role_key="owner",
    permissions={"dispensing:read", "dispensing:write"},
    sector_ids=[],
    is_admin=True,
)

_PRO_LIMITS = PLAN_LIMITS["pro"]
_STARTER_LIMITS = PLAN_LIMITS["starter"]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_app(service: MagicMock, plan_limits) -> FastAPI:
    from datapulse.api.routes.dispensing import router as dispensing_router

    app = FastAPI()
    app.include_router(dispensing_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_dispensing_service] = lambda: service
    app.dependency_overrides[get_tenant_plan_limits] = lambda: plan_limits
    app.dependency_overrides[get_access_context] = lambda: _ADMIN_CTX
    return app


def _rate() -> DispenseRate:
    return DispenseRate(
        product_key=1,
        site_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        drug_brand="Generic",
        site_code="S01",
        site_name="Main",
        active_days=45,
        total_dispensed_90d=Decimal("450"),
        avg_daily_dispense=Decimal("10.0"),
        avg_weekly_dispense=Decimal("70.0"),
        avg_monthly_dispense=Decimal("300.0"),
    )


def _dos() -> DaysOfStock:
    return DaysOfStock(
        product_key=1,
        site_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        site_name="Main",
        current_quantity=Decimal("100"),
        avg_daily_dispense=Decimal("5.0"),
        days_of_stock=Decimal("20.0"),
        avg_weekly_dispense=Decimal("35.0"),
        avg_monthly_dispense=Decimal("150.0"),
    )


def _velocity() -> VelocityClassification:
    return VelocityClassification(
        product_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        drug_brand="Generic",
        drug_category="Analgesics",
        lifecycle_phase="Mature",
        velocity_class="fast_mover",
        avg_daily_dispense=Decimal("10.0"),
        category_avg_daily=Decimal("5.0"),
    )


def _risk() -> StockoutRisk:
    return StockoutRisk(
        product_key=1,
        site_key=1,
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        site_name="Main",
        current_quantity=Decimal("5"),
        days_of_stock=Decimal("0.5"),
        avg_daily_dispense=Decimal("10.0"),
        reorder_point=Decimal("20"),
        reorder_lead_days=7,
        min_stock=Decimal("10"),
        risk_level="critical",
        suggested_reorder_qty=Decimal("15"),
    )


def _recon() -> StockReconciliation:
    return StockReconciliation(
        product_key=1,
        site_key=1,
        count_date=date(2025, 3, 1),
        drug_code="D001",
        drug_name="Paracetamol",
        site_code="S01",
        site_name="Main",
        counted_quantity=Decimal("100"),
        calculated_quantity=Decimal("98"),
        variance=Decimal("-2"),
    )


# ------------------------------------------------------------------
# Plan gating — starter plan blocked
# ------------------------------------------------------------------


@pytest.mark.unit
def test_rates_blocked_on_starter_plan():
    svc = create_autospec(DispensingService)
    client = TestClient(_make_app(svc, _STARTER_LIMITS))
    resp = client.get("/api/v1/dispensing/rates")
    assert resp.status_code == 403


@pytest.mark.unit
def test_days_of_stock_blocked_on_starter_plan():
    svc = create_autospec(DispensingService)
    client = TestClient(_make_app(svc, _STARTER_LIMITS))
    resp = client.get("/api/v1/dispensing/days-of-stock")
    assert resp.status_code == 403


@pytest.mark.unit
def test_stockout_risk_blocked_on_starter_plan():
    svc = create_autospec(DispensingService)
    client = TestClient(_make_app(svc, _STARTER_LIMITS))
    resp = client.get("/api/v1/dispensing/stockout-risk")
    assert resp.status_code == 403


# ------------------------------------------------------------------
# Pro plan — endpoints return correct data
# ------------------------------------------------------------------


@pytest.mark.unit
def test_get_rates_pro_plan():
    svc = create_autospec(DispensingService)
    svc.get_dispense_rates.return_value = [_rate()]
    client = TestClient(_make_app(svc, _PRO_LIMITS))
    resp = client.get("/api/v1/dispensing/rates")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["drug_code"] == "D001"
    assert data[0]["avg_daily_dispense"] == 10.0


@pytest.mark.unit
def test_get_days_of_stock_pro_plan():
    svc = create_autospec(DispensingService)
    svc.get_days_of_stock.return_value = [_dos()]
    client = TestClient(_make_app(svc, _PRO_LIMITS))
    resp = client.get("/api/v1/dispensing/days-of-stock")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["days_of_stock"] == 20.0


@pytest.mark.unit
def test_get_days_of_stock_null_history():
    """days_of_stock=None serialized as null for products with no history."""
    no_history = DaysOfStock(
        product_key=2,
        site_key=1,
        drug_code="D002",
        drug_name="NewDrug",
        site_code="S01",
        site_name="Main",
        current_quantity=Decimal("50"),
        avg_daily_dispense=None,
        days_of_stock=None,
        avg_weekly_dispense=None,
        avg_monthly_dispense=None,
    )
    svc = create_autospec(DispensingService)
    svc.get_days_of_stock.return_value = [no_history]
    client = TestClient(_make_app(svc, _PRO_LIMITS))
    resp = client.get("/api/v1/dispensing/days-of-stock")
    assert resp.status_code == 200
    assert resp.json()[0]["days_of_stock"] is None


@pytest.mark.unit
def test_get_velocity_pro_plan():
    svc = create_autospec(DispensingService)
    svc.get_velocity.return_value = [_velocity()]
    client = TestClient(_make_app(svc, _PRO_LIMITS))
    resp = client.get("/api/v1/dispensing/velocity")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["velocity_class"] == "fast_mover"


@pytest.mark.unit
def test_get_stockout_risk_pro_plan():
    svc = create_autospec(DispensingService)
    svc.get_stockout_risk.return_value = [_risk()]
    client = TestClient(_make_app(svc, _PRO_LIMITS))
    resp = client.get("/api/v1/dispensing/stockout-risk")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["risk_level"] == "critical"


@pytest.mark.unit
def test_get_reconciliation_pro_plan():
    svc = create_autospec(DispensingService)
    svc.get_reconciliation.return_value = [_recon()]
    client = TestClient(_make_app(svc, _PRO_LIMITS))
    resp = client.get("/api/v1/dispensing/reconciliation")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["variance"] == -2.0


# ------------------------------------------------------------------
# Query param passing
# ------------------------------------------------------------------


@pytest.mark.unit
def test_rates_filters_passed_to_service():
    svc = create_autospec(DispensingService)
    svc.get_dispense_rates.return_value = []
    client = TestClient(_make_app(svc, _PRO_LIMITS))
    client.get("/api/v1/dispensing/rates?site_key=2&drug_code=D001&limit=10")
    call_args = svc.get_dispense_rates.call_args[0][0]
    assert call_args.site_key == 2
    assert call_args.drug_code == "D001"
    assert call_args.limit == 10


@pytest.mark.unit
def test_velocity_class_filter_passed():
    svc = create_autospec(DispensingService)
    svc.get_velocity.return_value = []
    client = TestClient(_make_app(svc, _PRO_LIMITS))
    client.get("/api/v1/dispensing/velocity?velocity_class=dead_stock")
    call_args = svc.get_velocity.call_args[0][0]
    assert call_args.velocity_class == "dead_stock"

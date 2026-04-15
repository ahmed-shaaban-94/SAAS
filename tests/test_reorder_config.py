"""Tests for reorder config CRUD — validation, repository, service, and endpoints."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from datapulse.api.auth import get_current_user
from datapulse.api.deps import (
    get_inventory_service,
    get_reorder_config_service,
    get_tenant_plan_limits,
)
from datapulse.billing.plans import PLAN_LIMITS
from datapulse.core.exceptions import ValidationError
from datapulse.inventory.reorder_repository import ReorderConfig, ReorderConfigRepository
from datapulse.inventory.reorder_service import (
    ReorderConfigRequest,
    ReorderConfigResponse,
    ReorderConfigService,
)
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
    permissions={"inventory:read", "inventory:write"},
    sector_ids=[],
    is_admin=True,
)

_PRO_LIMITS = PLAN_LIMITS["pro"]
_STARTER_LIMITS = PLAN_LIMITS["starter"]


# ------------------------------------------------------------------
# Service validation tests
# ------------------------------------------------------------------


@pytest.fixture()
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def reorder_svc(mock_repo: MagicMock) -> ReorderConfigService:
    return ReorderConfigService(mock_repo)


def _valid_request(**overrides) -> ReorderConfigRequest:
    defaults = {
        "drug_code": "D001",
        "site_code": "S01",
        "min_stock": Decimal("10"),
        "reorder_point": Decimal("20"),
        "max_stock": Decimal("100"),
        "reorder_lead_days": 7,
    }
    defaults.update(overrides)
    return ReorderConfigRequest(**defaults)


def _config_row(**overrides) -> ReorderConfig:
    c = ReorderConfig(
        id=1,
        tenant_id=1,
        drug_code="D001",
        site_code="S01",
        min_stock=Decimal("10"),
        reorder_point=Decimal("20"),
        max_stock=Decimal("100"),
        reorder_lead_days=7,
        is_active=True,
        updated_at=None,
        updated_by=None,
    )
    for k, v in overrides.items():
        setattr(c, k, v)
    return c


@pytest.mark.unit
def test_upsert_valid_config(reorder_svc, mock_repo):
    """Valid thresholds (min <= reorder <= max) should call the repo."""
    mock_repo.upsert_config.return_value = _config_row()
    result = reorder_svc.upsert_config(1, _valid_request())
    mock_repo.upsert_config.assert_called_once()
    assert result.reorder_point == Decimal("20")


@pytest.mark.unit
def test_upsert_rejects_min_gt_reorder():
    """min_stock > reorder_point must raise ValidationError."""
    svc = ReorderConfigService(MagicMock())
    req = _valid_request(min_stock=Decimal("30"), reorder_point=Decimal("20"))
    with pytest.raises(ValidationError, match="min_stock must be less than or equal"):
        svc.upsert_config(1, req)


@pytest.mark.unit
def test_upsert_rejects_reorder_gt_max():
    """reorder_point > max_stock must raise ValidationError."""
    svc = ReorderConfigService(MagicMock())
    req = _valid_request(reorder_point=Decimal("150"), max_stock=Decimal("100"))
    with pytest.raises(ValidationError, match="reorder_point must be less than or equal"):
        svc.upsert_config(1, req)


@pytest.mark.unit
def test_upsert_allows_equal_min_reorder():
    """min_stock == reorder_point is valid."""
    mock_repo = MagicMock()
    mock_repo.upsert_config.return_value = _config_row(
        min_stock=Decimal("20"), reorder_point=Decimal("20")
    )
    svc = ReorderConfigService(mock_repo)
    req = _valid_request(min_stock=Decimal("20"), reorder_point=Decimal("20"))
    result = svc.upsert_config(1, req)
    assert result is not None


@pytest.mark.unit
def test_upsert_allows_equal_reorder_max():
    """reorder_point == max_stock is valid."""
    mock_repo = MagicMock()
    mock_repo.upsert_config.return_value = _config_row(
        reorder_point=Decimal("100"), max_stock=Decimal("100")
    )
    svc = ReorderConfigService(mock_repo)
    req = _valid_request(reorder_point=Decimal("100"), max_stock=Decimal("100"))
    result = svc.upsert_config(1, req)
    assert result is not None


@pytest.mark.unit
def test_get_config_not_found(reorder_svc, mock_repo):
    mock_repo.get_config.return_value = None
    result = reorder_svc.get_config(1, "NOTEXIST", "S01")
    assert result is None


@pytest.mark.unit
def test_get_config_found(reorder_svc, mock_repo):
    mock_repo.get_config.return_value = _config_row()
    result = reorder_svc.get_config(1, "D001", "S01")
    assert isinstance(result, ReorderConfigResponse)
    assert result.drug_code == "D001"


@pytest.mark.unit
def test_list_configs(reorder_svc, mock_repo):
    mock_repo.list_configs.return_value = [_config_row(), _config_row(drug_code="D002")]
    result = reorder_svc.list_configs(1)
    assert len(result) == 2


@pytest.mark.unit
def test_deactivate_config_found(reorder_svc, mock_repo):
    mock_repo.deactivate_config.return_value = True
    assert reorder_svc.deactivate_config(1, "D001", "S01") is True


@pytest.mark.unit
def test_deactivate_config_not_found(reorder_svc, mock_repo):
    mock_repo.deactivate_config.return_value = False
    assert reorder_svc.deactivate_config(1, "NOTEXIST", "S01") is False


# ------------------------------------------------------------------
# Repository tests
# ------------------------------------------------------------------


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def rc_repo(mock_session: MagicMock) -> ReorderConfigRepository:
    return ReorderConfigRepository(mock_session)


def _mock_first(d) -> MagicMock:
    m = MagicMock()
    m.mappings.return_value.first.return_value = dict(d) if d else None
    return m


def _mock_rows(*dicts) -> MagicMock:
    m = MagicMock()
    m.mappings.return_value.all.return_value = [dict(d) for d in dicts]
    return m


@pytest.mark.unit
def test_repo_get_config_not_found(rc_repo, mock_session):
    mock_session.execute.return_value = _mock_first(None)
    result = rc_repo.get_config(1, "NOTEXIST", "S01")
    assert result is None


@pytest.mark.unit
def test_repo_get_config_found(rc_repo, mock_session):
    row = {
        "id": 1,
        "tenant_id": 1,
        "drug_code": "D001",
        "site_code": "S01",
        "min_stock": Decimal("10"),
        "reorder_point": Decimal("20"),
        "max_stock": Decimal("100"),
        "reorder_lead_days": 7,
        "is_active": True,
        "updated_at": None,
        "updated_by": None,
    }
    mock_session.execute.return_value = _mock_first(row)
    result = rc_repo.get_config(1, "D001", "S01")
    assert result is not None
    assert result.drug_code == "D001"
    assert result.reorder_point == Decimal("20")


@pytest.mark.unit
def test_repo_list_configs(rc_repo, mock_session):
    rows = [
        {
            "id": 1,
            "tenant_id": 1,
            "drug_code": "D001",
            "site_code": "S01",
            "min_stock": Decimal("10"),
            "reorder_point": Decimal("20"),
            "max_stock": Decimal("100"),
            "reorder_lead_days": 7,
            "is_active": True,
            "updated_at": None,
            "updated_by": None,
        }
    ]
    mock_session.execute.return_value = _mock_rows(*rows)
    result = rc_repo.list_configs(1)
    assert len(result) == 1
    assert result[0].drug_code == "D001"


@pytest.mark.unit
def test_repo_upsert_config(rc_repo, mock_session):
    row = {
        "id": 1,
        "tenant_id": 1,
        "drug_code": "D001",
        "site_code": "S01",
        "min_stock": Decimal("10"),
        "reorder_point": Decimal("20"),
        "max_stock": Decimal("100"),
        "reorder_lead_days": 7,
        "is_active": True,
        "updated_at": None,
        "updated_by": "test",
    }
    mock_session.execute.return_value = _mock_first(row)
    result = rc_repo.upsert_config(1, "D001", "S01", 10.0, 20.0, 100.0, 7, "test")
    assert result.reorder_point == Decimal("20")
    mock_session.execute.assert_called_once()


@pytest.mark.unit
def test_repo_deactivate_config(rc_repo, mock_session):
    m = MagicMock()
    m.first.return_value = (1,)
    mock_session.execute.return_value = m
    result = rc_repo.deactivate_config(1, "D001", "S01")
    assert result is True


@pytest.mark.unit
def test_repo_deactivate_config_not_found(rc_repo, mock_session):
    m = MagicMock()
    m.first.return_value = None
    mock_session.execute.return_value = m
    result = rc_repo.deactivate_config(1, "NOTEXIST", "S01")
    assert result is False


# ------------------------------------------------------------------
# Endpoint tests
# ------------------------------------------------------------------


def _make_inventory_app(
    inv_svc: MagicMock,
    reorder_svc: MagicMock,
    plan_limits,
) -> FastAPI:
    from datapulse.api.routes.inventory import router as inventory_router

    app = FastAPI()
    app.include_router(inventory_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_inventory_service] = lambda: inv_svc
    app.dependency_overrides[get_reorder_config_service] = lambda: reorder_svc
    app.dependency_overrides[get_tenant_plan_limits] = lambda: plan_limits
    app.dependency_overrides[get_access_context] = lambda: _ADMIN_CTX
    return app


@pytest.fixture()
def inv_svc() -> MagicMock:
    return create_autospec(
        __import__("datapulse.inventory.service", fromlist=["InventoryService"]).InventoryService
    )


@pytest.fixture()
def rc_svc() -> MagicMock:
    return create_autospec(ReorderConfigService)


@pytest.mark.unit
def test_list_reorder_configs_pro(inv_svc, rc_svc):
    rc_svc.list_configs.return_value = [
        ReorderConfigResponse(
            id=1,
            tenant_id=1,
            drug_code="D001",
            site_code="S01",
            min_stock=Decimal("10"),
            reorder_point=Decimal("20"),
            max_stock=Decimal("100"),
            reorder_lead_days=7,
            is_active=True,
        )
    ]
    client = TestClient(_make_inventory_app(inv_svc, rc_svc, _PRO_LIMITS))
    resp = client.get("/api/v1/inventory/reorder-config")
    assert resp.status_code == 200
    assert resp.json()[0]["drug_code"] == "D001"


@pytest.mark.unit
def test_list_reorder_configs_starter_blocked(inv_svc, rc_svc):
    client = TestClient(_make_inventory_app(inv_svc, rc_svc, _STARTER_LIMITS))
    resp = client.get("/api/v1/inventory/reorder-config")
    assert resp.status_code == 403


@pytest.mark.unit
def test_get_reorder_config_not_found(inv_svc, rc_svc):
    rc_svc.get_config.return_value = None
    client = TestClient(_make_inventory_app(inv_svc, rc_svc, _PRO_LIMITS))
    resp = client.get("/api/v1/inventory/reorder-config/NOTEXIST/S01")
    assert resp.status_code == 404


@pytest.mark.unit
def test_upsert_reorder_config_valid(inv_svc, rc_svc):
    rc_svc.upsert_config.return_value = ReorderConfigResponse(
        id=1,
        tenant_id=1,
        drug_code="D001",
        site_code="S01",
        min_stock=Decimal("10"),
        reorder_point=Decimal("20"),
        max_stock=Decimal("100"),
        reorder_lead_days=7,
        is_active=True,
    )
    client = TestClient(_make_inventory_app(inv_svc, rc_svc, _PRO_LIMITS))
    resp = client.put(
        "/api/v1/inventory/reorder-config",
        json={
            "drug_code": "D001",
            "site_code": "S01",
            "min_stock": "10",
            "reorder_point": "20",
            "max_stock": "100",
            "reorder_lead_days": 7,
        },
    )
    assert resp.status_code == 200
    # Decimal fields serialize as strings by default
    assert float(resp.json()["reorder_point"]) == 20.0


@pytest.mark.unit
def test_deactivate_reorder_config_found(inv_svc, rc_svc):
    rc_svc.deactivate_config.return_value = True
    client = TestClient(_make_inventory_app(inv_svc, rc_svc, _PRO_LIMITS))
    resp = client.delete("/api/v1/inventory/reorder-config/D001/S01")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deactivated"


@pytest.mark.unit
def test_deactivate_reorder_config_not_found(inv_svc, rc_svc):
    rc_svc.deactivate_config.return_value = False
    client = TestClient(_make_inventory_app(inv_svc, rc_svc, _PRO_LIMITS))
    resp = client.delete("/api/v1/inventory/reorder-config/NOTEXIST/S01")
    assert resp.status_code == 404

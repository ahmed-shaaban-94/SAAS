"""Tests for branding module — models, service, repository, endpoints."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from datapulse.api.app import create_app
from datapulse.api.auth import get_current_user
from datapulse.api.deps import get_tenant_session
from datapulse.branding.models import (
    BrandingResponse,
    BrandingUpdate,
    PublicBrandingResponse,
)
from datapulse.branding.repository import BrandingRepository
from datapulse.branding.service import BrandingService

NOW = datetime(2025, 6, 15, 12, 0, 0)

MOCK_USER = {
    "sub": "test-user",
    "email": "test@datapulse.local",
    "preferred_username": "test",
    "tenant_id": "1",
    "roles": ["owner"],
    "raw_claims": {},
}


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def repo(mock_session: MagicMock) -> BrandingRepository:
    return BrandingRepository(mock_session)


@pytest.fixture()
def mock_repo() -> MagicMock:
    return create_autospec(BrandingRepository, instance=True)


@pytest.fixture()
def service(mock_repo: MagicMock) -> BrandingService:
    return BrandingService(mock_repo)


@pytest.fixture()
def mock_service() -> MagicMock:
    return create_autospec(BrandingService, instance=True)


@pytest.fixture()
def client(mock_service: MagicMock) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_tenant_session] = lambda: MagicMock()

    from datapulse.api.routes.branding import get_branding_service
    app.dependency_overrides[get_branding_service] = lambda: mock_service

    return TestClient(app)


def _branding(**overrides) -> BrandingResponse:
    base = {
        "tenant_id": 1,
        "company_name": "TestCo",
        "primary_color": "#4F46E5",
        "accent_color": "#D97706",
        "font_family": "Inter",
        "created_at": NOW,
        "updated_at": NOW,
    }
    base.update(overrides)
    return BrandingResponse(**base)


# ══════════════════════════════════════════════════════════════════════
# Model tests
# ══════════════════════════════════════════════════════════════════════


class TestModels:
    def test_branding_response_defaults(self):
        br = BrandingResponse(tenant_id=1)
        assert br.company_name == "DataPulse"
        assert br.primary_color == "#4F46E5"
        assert br.hide_datapulse_branding is False

    def test_branding_response_frozen(self):
        br = BrandingResponse(tenant_id=1)
        with pytest.raises((TypeError, AttributeError, ValidationError)):
            br.company_name = "Other"

    def test_branding_update_partial(self):
        update = BrandingUpdate(company_name="NewCo")
        dumped = update.model_dump(exclude_none=True)
        assert dumped == {"company_name": "NewCo"}

    def test_public_branding_defaults(self):
        pb = PublicBrandingResponse()
        assert pb.company_name == "DataPulse"
        assert pb.primary_color == "#4F46E5"


# ══════════════════════════════════════════════════════════════════════
# Service tests
# ══════════════════════════════════════════════════════════════════════


class TestBrandingService:
    def test_get_branding(self, service, mock_repo):
        mock_repo.get_branding.return_value = _branding()
        result = service.get_branding(1)
        assert result.company_name == "TestCo"
        mock_repo.get_branding.assert_called_with(1)

    def test_update_branding_valid(self, service, mock_repo):
        mock_repo.update_branding.return_value = _branding(company_name="NewCo")
        result = service.update_branding(1, BrandingUpdate(company_name="NewCo"))
        assert result.company_name == "NewCo"

    def test_update_branding_invalid_color(self, service):
        with pytest.raises(ValueError, match="Invalid primary_color"):
            service.update_branding(1, BrandingUpdate(primary_color="not-a-color"))

    def test_update_branding_invalid_accent(self, service):
        with pytest.raises(ValueError, match="Invalid accent_color"):
            service.update_branding(1, BrandingUpdate(accent_color="xyz"))

    def test_update_branding_invalid_subdomain(self, service):
        with pytest.raises(ValueError, match="Invalid subdomain"):
            service.update_branding(1, BrandingUpdate(subdomain="INVALID!!"))

    def test_update_branding_valid_subdomain(self, service, mock_repo):
        mock_repo.update_branding.return_value = _branding(subdomain="my-tenant")
        result = service.update_branding(1, BrandingUpdate(subdomain="my-tenant"))
        assert result.subdomain == "my-tenant"

    def test_delete_logo(self, service, mock_repo):
        mock_repo.get_branding.return_value = _branding(logo_url=None)
        result = service.delete_logo(1)
        mock_repo.update_logo_url.assert_called_with(1, None)
        assert result.logo_url is None

    def test_get_public_branding_found(self, service, mock_repo):
        mock_repo.get_public_branding_by_domain.return_value = PublicBrandingResponse(
            company_name="ClientCo"
        )
        result = service.get_public_branding("client.datapulse.tech")
        assert result.company_name == "ClientCo"

    def test_get_public_branding_not_found(self, service, mock_repo):
        mock_repo.get_public_branding_by_domain.return_value = None
        result = service.get_public_branding("unknown.com")
        assert result.company_name == "DataPulse"

    def test_resolve_tenant(self, service, mock_repo):
        mock_repo.resolve_tenant_by_domain.return_value = 42
        result = service.resolve_tenant("client.datapulse.tech")
        assert result == 42

    def test_resolve_tenant_not_found(self, service, mock_repo):
        mock_repo.resolve_tenant_by_domain.return_value = None
        result = service.resolve_tenant("unknown.com")
        assert result is None


# ══════════════════════════════════════════════════════════════════════
# Endpoint tests
# ══════════════════════════════════════════════════════════════════════


class TestBrandingEndpoints:
    def test_get_branding(self, client, mock_service):
        mock_service.get_branding.return_value = _branding()
        resp = client.get("/api/v1/branding/")
        assert resp.status_code == 200
        assert resp.json()["company_name"] == "TestCo"

    def test_update_branding(self, client, mock_service):
        mock_service.update_branding.return_value = _branding(company_name="NewCo")
        resp = client.put("/api/v1/branding/", json={"company_name": "NewCo"})
        assert resp.status_code == 200
        assert resp.json()["company_name"] == "NewCo"

    def test_update_branding_invalid(self, client, mock_service):
        mock_service.update_branding.side_effect = ValueError("Invalid primary_color")
        resp = client.put("/api/v1/branding/", json={"primary_color": "bad"})
        assert resp.status_code == 400

    def test_delete_logo(self, client, mock_service):
        mock_service.delete_logo.return_value = _branding(logo_url=None)
        resp = client.delete("/api/v1/branding/logo")
        assert resp.status_code == 200
        assert resp.json()["logo_url"] is None

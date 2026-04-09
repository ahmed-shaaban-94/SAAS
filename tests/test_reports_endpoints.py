"""Tests for reports API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from datapulse.reports.models import (
    ParameterType,
    RenderedReport,
    RenderedSection,
    ReportParameter,
    ReportTemplate,
    SectionType,
)


def _make_reports_client():
    from datapulse.api import deps
    from datapulse.api.app import create_app
    from datapulse.api.auth import get_current_user

    _dev_user = {
        "sub": "test-user",
        "email": "test@datapulse.local",
        "preferred_username": "test",
        "tenant_id": "1",
        "roles": ["admin"],
        "raw_claims": {},
    }

    mock_session = MagicMock()
    app = create_app()
    app.dependency_overrides[deps.get_tenant_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: _dev_user

    client = TestClient(app, headers={"X-API-Key": "test-api-key"})
    return client, mock_session


_TEMPLATE = ReportTemplate(
    id="test-tpl",
    name="Test Template",
    description="A test",
    parameters=[
        ReportParameter(name="year", label="Year", param_type=ParameterType.number, default=2025)
    ],
    sections=[],
)


class TestListTemplates:
    @patch("datapulse.api.routes.reports.get_templates", return_value=[_TEMPLATE])
    def test_list_templates(self, mock_get):
        client, _ = _make_reports_client()
        resp = client.get("/api/v1/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "test-tpl"


class TestGetTemplateDetail:
    @patch("datapulse.api.routes.reports.get_template", return_value=_TEMPLATE)
    def test_get_template_found(self, mock_get):
        client, _ = _make_reports_client()
        resp = client.get("/api/v1/reports/test-tpl")
        assert resp.status_code == 200
        assert resp.json()["id"] == "test-tpl"

    @patch("datapulse.api.routes.reports.get_template", return_value=None)
    def test_get_template_not_found(self, mock_get):
        client, _ = _make_reports_client()
        resp = client.get("/api/v1/reports/nonexistent")
        assert resp.status_code == 404


class TestRenderReport:
    @patch("datapulse.api.routes.reports.render_report")
    @patch("datapulse.api.routes.reports.get_template", return_value=_TEMPLATE)
    def test_render_success(self, mock_get_tpl, mock_render):
        mock_render.return_value = RenderedReport(
            template_id="test-tpl",
            template_name="Test Template",
            parameters={"year": 2025},
            sections=[
                RenderedSection(
                    section_type=SectionType.text,
                    title="Summary",
                    text="Overview for 2025",
                )
            ],
        )
        client, _ = _make_reports_client()
        resp = client.post(
            "/api/v1/reports/test-tpl/render",
            json={"parameters": {"year": 2025}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["template_id"] == "test-tpl"
        assert len(data["sections"]) == 1

    @patch("datapulse.api.routes.reports.get_template", return_value=None)
    def test_render_template_not_found(self, mock_get):
        client, _ = _make_reports_client()
        resp = client.post(
            "/api/v1/reports/missing/render",
            json={"parameters": {}},
        )
        assert resp.status_code == 404

"""Async tests for the migrated leads vertical."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_leads_repository_email_exists_awaits_execute():
    """LeadRepository.email_exists must await session.execute."""
    from unittest.mock import MagicMock

    from datapulse.leads.repository import LeadRepository

    session = AsyncMock()
    # AsyncMock.execute awaits to a regular MagicMock result; configure fetchone
    result_mock = MagicMock()
    result_mock.fetchone.return_value = None
    session.execute.return_value = result_mock
    repo = LeadRepository(session)

    result = await repo.email_exists(email="x@y.com")

    session.execute.assert_awaited_once()
    assert result is False


@pytest.mark.asyncio
async def test_leads_repository_insert_awaits_execute():
    """LeadRepository.insert must await session.execute."""
    from datapulse.leads.repository import LeadRepository

    session = AsyncMock()
    repo = LeadRepository(session)

    await repo.insert(
        email="x@y.com",
        name="Test",
        company="Co",
        use_case=None,
        team_size=None,
        tier=None,
    )

    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_leads_post_endpoint_runs_async(monkeypatch):
    """POST /api/v1/leads goes through the async dep + service."""
    from httpx import ASGITransport, AsyncClient

    from datapulse.api.app import create_app
    from datapulse.api.deps import get_lead_service_async
    from datapulse.leads.models import LeadResponse
    from datapulse.leads.service import LeadService

    fake_service = AsyncMock(spec=LeadService)
    fake_service.capture.return_value = LeadResponse(
        success=True, message="You're on the list! We'll be in touch soon."
    )

    app = create_app()
    app.dependency_overrides[get_lead_service_async] = lambda: fake_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/leads",
            json={"email": "x@y.com", "name": "Test", "company": "C"},
        )

    assert resp.status_code in (200, 201)
    fake_service.capture.assert_awaited_once()

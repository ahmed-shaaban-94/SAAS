"""Unit tests for the outbound webhooks module (#608)."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from datapulse.webhooks.dispatcher import (
    _RETRY_DELAYS,
    MAX_ATTEMPTS,
    compute_signature,
    dispatch,
    next_retry_at,
)
from datapulse.webhooks.models import DeliveryLogResponse, SubscriptionCreate
from datapulse.webhooks.repository import WebhookRepository
from datapulse.webhooks.service import WebhookService, fire_event

# ── helpers ───────────────────────────────────────────────────────────────────


def _now():
    return datetime.datetime.now(datetime.UTC)


def _sub_row(**overrides):
    base = {
        "id": 1,
        "event_type": "sale.created",
        "target_url": "https://example.com/hook",
        "is_active": True,
        "created_at": _now(),
    }
    base.update(overrides)
    return base


def _delivery_row(**overrides):
    base = {
        "id": 1,
        "subscription_id": 1,
        "event_type": "sale.created",
        "payload": {"order_id": "abc"},
        "status": "sent",
        "attempt_count": 1,
        "next_retry_at": None,
        "last_error": None,
        "delivered_at": _now(),
        "created_at": _now(),
    }
    base.update(overrides)
    return base


# ── dispatcher ────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestDispatcher:
    def test_compute_signature_is_deterministic(self):
        sig1 = compute_signature("secret", b"body")
        sig2 = compute_signature("secret", b"body")
        assert sig1 == sig2
        assert sig1.startswith("sha256=")

    def test_compute_signature_differs_on_body_change(self):
        assert compute_signature("s", b"a") != compute_signature("s", b"b")

    def test_compute_signature_differs_on_secret_change(self):
        assert compute_signature("s1", b"body") != compute_signature("s2", b"body")

    def test_next_retry_at_returns_datetime_for_valid_attempts(self):
        for i in range(len(_RETRY_DELAYS)):
            result = next_retry_at(i)
            assert result is not None
            assert result > datetime.datetime.now(datetime.UTC)

    def test_next_retry_at_returns_none_when_exhausted(self):
        assert next_retry_at(len(_RETRY_DELAYS)) is None

    def test_max_attempts_is_one_more_than_delays(self):
        assert len(_RETRY_DELAYS) + 1 == MAX_ATTEMPTS

    def test_retry_delays_are_increasing(self):
        for i in range(len(_RETRY_DELAYS) - 1):
            assert _RETRY_DELAYS[i] < _RETRY_DELAYS[i + 1]

    def test_dispatch_sends_signed_post(self):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = Mock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            dispatch("https://recv.example.com", "secret123", "sale.created", {"id": "1"})

        call_kwargs = mock_client.post.call_args
        headers = call_kwargs.kwargs["headers"]
        assert "X-DataPulse-Signature" in headers
        assert headers["X-DataPulse-Signature"].startswith("sha256=")
        assert headers["X-DataPulse-Event"] == "sale.created"

    def test_dispatch_raises_on_http_error(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = Mock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_resp = Mock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500", request=Mock(), response=Mock()
            )
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                dispatch("https://recv.example.com", "sec", "sale.created", {})


# ── service ───────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestWebhookService:
    def _make_service(self):
        repo = MagicMock(spec=WebhookRepository)
        return WebhookService(repo), repo

    def test_create_subscription_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.create_subscription.return_value = _sub_row()
        result = svc.create_subscription(1, "sale.created", "https://example.com/hook", "secret123")
        repo.create_subscription.assert_called_once_with(
            1, "sale.created", "https://example.com/hook", "secret123"
        )
        assert result["event_type"] == "sale.created"

    def test_list_subscriptions_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.list_subscriptions.return_value = []
        result = svc.list_subscriptions(tenant_id=5)
        repo.list_subscriptions.assert_called_once_with(5)
        assert result == []

    def test_delete_subscription_returns_false_when_not_found(self):
        svc, repo = self._make_service()
        repo.delete_subscription.return_value = False
        assert svc.delete_subscription(99, 1) is False

    def test_list_deliveries_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.list_deliveries.return_value = [_delivery_row()]
        result = svc.list_deliveries(tenant_id=1, status="sent")
        repo.list_deliveries.assert_called_once_with(1, None, "sent", 50)
        assert len(result) == 1

    def test_fire_event_noop_when_no_subscribers(self):
        svc, repo = self._make_service()
        repo.get_active_subscribers.return_value = []
        svc.fire_event("sale.created", 1, {"order_id": "abc"})
        repo.create_delivery.assert_not_called()

    def test_fire_event_creates_delivery_per_subscriber(self):
        svc, repo = self._make_service()
        repo.get_active_subscribers.return_value = [
            {"id": 10, "target_url": "https://a.example.com", "secret": "s1"},
            {"id": 11, "target_url": "https://b.example.com", "secret": "s2"},
        ]
        repo.create_delivery.return_value = 42

        with patch("threading.Thread") as mock_thread:
            mock_thread.return_value.start = MagicMock()
            svc.fire_event("sale.created", 1, {"order_id": "abc"})

        assert repo.create_delivery.call_count == 2
        assert mock_thread.call_count == 2

    def test_retry_pending_dispatches_threads(self):
        svc, repo = self._make_service()
        repo.get_pending_retries.return_value = [
            {
                "id": 1,
                "target_url": "https://x.example.com",
                "secret": "sec",
                "event_type": "pipeline.completed",
                "payload": {"run_id": "abc"},
                "attempt_count": 1,
            }
        ]
        with patch("threading.Thread") as mock_thread:
            mock_thread.return_value.start = MagicMock()
            count = svc.retry_pending()

        assert count == 1
        mock_thread.assert_called_once()

    def test_retry_pending_returns_zero_when_empty(self):
        svc, repo = self._make_service()
        repo.get_pending_retries.return_value = []
        assert svc.retry_pending() == 0

    def test_replay_delivery_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.reset_for_replay.return_value = True
        assert svc.replay_delivery(7, 1) is True
        repo.reset_for_replay.assert_called_once_with(7, 1)

    def test_attempt_delivery_success_marks_sent(self):
        svc, repo = self._make_service()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=WebhookRepository)

        with (
            patch("datapulse.core.db_session.open_tenant_session", return_value=mock_session),
            patch("datapulse.webhooks.service.WebhookRepository", return_value=mock_repo),
            patch("datapulse.webhooks.service.dispatcher.dispatch") as mock_dispatch,
        ):
            svc._attempt_delivery(42, "https://x.com", "sec", "sale.created", {"k": "v"}, 0)

        mock_dispatch.assert_called_once()
        mock_repo.mark_sent.assert_called_once_with(42)
        mock_session.commit.assert_called_once()

    def test_attempt_delivery_failure_marks_failed_with_retry(self):
        svc, repo = self._make_service()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=WebhookRepository)

        with (
            patch("datapulse.core.db_session.open_tenant_session", return_value=mock_session),
            patch("datapulse.webhooks.service.WebhookRepository", return_value=mock_repo),
            patch(
                "datapulse.webhooks.service.dispatcher.dispatch",
                side_effect=Exception("timeout"),
            ),
        ):
            svc._attempt_delivery(42, "https://x.com", "sec", "sale.created", {}, 0)

        mock_repo.mark_failed.assert_called_once()
        call_kwargs = mock_repo.mark_failed.call_args.kwargs
        assert call_kwargs["attempt_count"] == 1
        assert call_kwargs["dead"] is False

    def test_attempt_delivery_dead_lettered_at_max(self):
        svc, repo = self._make_service()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=WebhookRepository)

        with (
            patch("datapulse.core.db_session.open_tenant_session", return_value=mock_session),
            patch("datapulse.webhooks.service.WebhookRepository", return_value=mock_repo),
            patch(
                "datapulse.webhooks.service.dispatcher.dispatch",
                side_effect=Exception("timeout"),
            ),
        ):
            # attempt_count=5 → 6th attempt → next_retry_at=None → dead
            svc._attempt_delivery(42, "https://x.com", "sec", "sale.created", {}, 5)

        call_kwargs = mock_repo.mark_failed.call_args.kwargs
        assert call_kwargs["dead"] is True
        assert call_kwargs["next_retry_at"] is None

    def test_module_level_fire_event(self):
        mock_session = MagicMock()
        mock_svc = MagicMock(spec=WebhookService)

        with (
            patch("datapulse.webhooks.service.WebhookRepository"),
            patch("datapulse.webhooks.service.WebhookService", return_value=mock_svc),
        ):
            fire_event("pipeline.completed", 1, {"run_id": "abc"}, mock_session)

        mock_svc.fire_event.assert_called_once_with("pipeline.completed", 1, {"run_id": "abc"})


# ── models ────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestWebhookModels:
    def test_subscription_create_rejects_non_http_url(self):
        with pytest.raises(ValidationError):
            SubscriptionCreate(
                event_type="sale.created",
                target_url="ftp://bad.com",  # type: ignore[arg-type]
                secret="s" * 16,
            )

    def test_subscription_create_rejects_short_secret(self):
        with pytest.raises(ValidationError):
            SubscriptionCreate(
                event_type="sale.created",
                target_url="https://ok.com",
                secret="short",
            )

    def test_subscription_create_valid(self):
        m = SubscriptionCreate(
            event_type="pipeline.completed",
            target_url="https://hooks.example.com/receive",
            secret="a" * 16,
        )
        assert m.event_type == "pipeline.completed"

    def test_delivery_log_response_from_dict(self):
        now = _now()
        data = {
            "id": 1,
            "subscription_id": 2,
            "event_type": "sale.created",
            "payload": {"order_id": "abc"},
            "status": "sent",
            "attempt_count": 1,
            "next_retry_at": None,
            "last_error": None,
            "delivered_at": now,
            "created_at": now,
        }
        resp = DeliveryLogResponse(**data)
        assert resp.status == "sent"
        assert resp.delivered_at == now


# ── routes (FastAPI TestClient) ───────────────────────────────────────────────


@pytest.fixture()
def mock_user():
    return {"sub": "u1", "tenant_id": "1", "roles": ["admin"], "email": "u@x.com"}


@pytest.fixture()
def mock_svc():
    return MagicMock(spec=WebhookService)


@pytest.fixture()
def client(mock_user, mock_svc):
    from datapulse.api.app import create_app
    from datapulse.api.auth import get_current_user
    from datapulse.api.routes.webhooks import _svc

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[_svc] = lambda: mock_svc
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.unit
class TestWebhookRoutes:
    def test_list_subscriptions_empty(self, client, mock_svc):
        mock_svc.list_subscriptions.return_value = []
        res = client.get("/api/v1/webhooks/subscriptions")
        assert res.status_code == 200
        assert res.json() == []

    def test_list_subscriptions_returns_rows(self, client, mock_svc):
        mock_svc.list_subscriptions.return_value = [_sub_row()]
        res = client.get("/api/v1/webhooks/subscriptions")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["event_type"] == "sale.created"

    def test_create_subscription(self, client, mock_svc):
        mock_svc.create_subscription.return_value = _sub_row()
        payload = {
            "event_type": "sale.created",
            "target_url": "https://recv.example.com/hook",
            "secret": "a" * 16,
        }
        res = client.post("/api/v1/webhooks/subscriptions", json=payload)
        assert res.status_code == 201
        assert res.json()["event_type"] == "sale.created"

    def test_delete_subscription_success(self, client, mock_svc):
        mock_svc.delete_subscription.return_value = True
        res = client.delete("/api/v1/webhooks/subscriptions/1")
        assert res.status_code == 204

    def test_delete_subscription_not_found(self, client, mock_svc):
        mock_svc.delete_subscription.return_value = False
        res = client.delete("/api/v1/webhooks/subscriptions/99")
        assert res.status_code == 404

    def test_list_deliveries(self, client, mock_svc):
        mock_svc.list_deliveries.return_value = [_delivery_row()]
        res = client.get("/api/v1/webhooks/deliveries")
        assert res.status_code == 200
        assert res.json()[0]["status"] == "sent"

    def test_list_deliveries_with_filters(self, client, mock_svc):
        mock_svc.list_deliveries.return_value = []
        res = client.get("/api/v1/webhooks/deliveries?subscription_id=1&status=failed&limit=10")
        assert res.status_code == 200
        mock_svc.list_deliveries.assert_called_once_with(
            tenant_id=1, subscription_id=1, status="failed", limit=10
        )

    def test_replay_delivery_success(self, client, mock_svc):
        mock_svc.replay_delivery.return_value = True
        res = client.post("/api/v1/webhooks/deliveries/7/replay")
        assert res.status_code == 202
        assert res.json()["delivery_id"] == 7

    def test_replay_delivery_not_found(self, client, mock_svc):
        mock_svc.replay_delivery.return_value = False
        res = client.post("/api/v1/webhooks/deliveries/99/replay")
        assert res.status_code == 404

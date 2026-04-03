"""Tests for health check component helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from datapulse.api.routes.health import _check_celery, _check_db, _check_redis


class TestCheckDb:
    @patch("datapulse.api.routes.health.get_engine")
    def test_ok(self, mock_engine):
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None
        result = _check_db()
        assert result["status"] == "ok"
        assert "latency_ms" in result

    @patch("datapulse.api.routes.health.get_engine")
    def test_error(self, mock_engine):
        mock_engine.return_value.connect.side_effect = Exception("refused")
        result = _check_db()
        assert result["status"] == "error"
        assert "refused" in result["error"]


class TestCheckRedis:
    @patch("datapulse.cache.get_redis_client", return_value=None)
    def test_disabled(self, _):
        result = _check_redis()
        assert result["status"] == "disabled"

    @patch("datapulse.cache.get_redis_client")
    def test_ok(self, mock_get):
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_get.return_value = mock_client
        result = _check_redis()
        assert result["status"] == "ok"
        assert "latency_ms" in result

    @patch("datapulse.cache.get_redis_client")
    def test_error(self, mock_get):
        mock_get.side_effect = Exception("connection refused")
        result = _check_redis()
        assert result["status"] == "error"


class TestCheckCelery:
    @patch("datapulse.tasks.celery_app.celery_app")
    def test_ok(self, mock_celery):
        inspector = MagicMock()
        inspector.active.return_value = {"worker1": []}
        mock_celery.control.inspect.return_value = inspector
        result = _check_celery()
        assert result["status"] == "ok"
        assert result["workers"] == 1

    @patch("datapulse.tasks.celery_app.celery_app")
    def test_no_workers(self, mock_celery):
        inspector = MagicMock()
        inspector.active.return_value = None
        mock_celery.control.inspect.return_value = inspector
        result = _check_celery()
        assert result["status"] == "no-workers"

    @patch("datapulse.tasks.celery_app.celery_app")
    def test_error(self, mock_celery):
        mock_celery.control.inspect.side_effect = Exception("broker down")
        result = _check_celery()
        assert result["status"] == "error"

"""Tests for health check component helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import redis
import sqlalchemy.exc

from datapulse.api.routes.health import (
    _check_data_freshness,
    _check_db,
    _check_dbt_freshness,
    _check_query_executor,
    _check_redis,
    _check_schema_version,
)


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
        mock_engine.return_value.connect.side_effect = sqlalchemy.exc.OperationalError(
            "SELECT 1", {}, Exception("refused")
        )
        result = _check_db()
        assert result["status"] == "error"
        assert result["error"] == "internal_error"


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
        mock_get.side_effect = redis.ConnectionError("connection refused")
        result = _check_redis()
        assert result["status"] == "error"


class TestCheckQueryExecutor:
    @patch("datapulse.tasks.async_executor._get_job_client", return_value=None)
    def test_disabled(self, _):
        result = _check_query_executor()
        assert result["status"] == "disabled"

    @patch("datapulse.tasks.async_executor._get_job_client")
    def test_ok(self, mock_get):
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_get.return_value = mock_client
        result = _check_query_executor()
        assert result["status"] == "ok"
        assert "latency_ms" in result

    @patch("datapulse.tasks.async_executor._get_job_client")
    def test_error(self, mock_get):
        mock_get.side_effect = redis.ConnectionError("connection refused")
        result = _check_query_executor()
        assert result["status"] == "error"


class TestCheckSchemaVersion:
    @patch("datapulse.api.routes.health.get_engine")
    def test_ok(self, mock_engine):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = ("abc1234",)
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None
        result = _check_schema_version()
        assert result["status"] == "ok"
        assert result["version"] == "abc1234"

    @patch("datapulse.api.routes.health.get_engine")
    def test_unknown_when_empty(self, mock_engine):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None
        result = _check_schema_version()
        assert result["status"] == "unknown"
        assert result["version"] is None

    @patch("datapulse.api.routes.health.get_engine")
    def test_error(self, mock_engine):
        mock_engine.return_value.connect.side_effect = sqlalchemy.exc.OperationalError(
            "SELECT version_num FROM alembic_version LIMIT 1", {}, Exception("timeout")
        )
        result = _check_schema_version()
        assert result["status"] == "error"
        assert "timeout" in result["error"] or result["error"] == "internal_error"


class TestCheckDbtFreshness:
    @patch("datapulse.api.routes.health.get_engine")
    def test_ok(self, mock_engine):
        mock_conn = MagicMock()
        recent = datetime.now(UTC) - timedelta(hours=1)
        mock_conn.execute.return_value.fetchone.return_value = (recent,)
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None
        result = _check_dbt_freshness()
        assert result["status"] == "ok"
        assert "last_updated_at" in result
        assert result["age_hours"] < 24

    @patch("datapulse.api.routes.health.get_engine")
    def test_stale(self, mock_engine):
        mock_conn = MagicMock()
        old_ts = datetime.now(UTC) - timedelta(hours=25)
        mock_conn.execute.return_value.fetchone.return_value = (old_ts,)
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None
        result = _check_dbt_freshness()
        assert result["status"] == "stale"
        assert result["age_hours"] > 24

    @patch("datapulse.api.routes.health.get_engine")
    def test_unknown_when_empty(self, mock_engine):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (None,)
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None
        result = _check_dbt_freshness()
        assert result["status"] == "unknown"
        assert result["last_updated_at"] is None

    @patch("datapulse.api.routes.health.get_engine")
    def test_error(self, mock_engine):
        mock_engine.return_value.connect.side_effect = sqlalchemy.exc.OperationalError(
            "SELECT MAX(updated_at) FROM gold.metrics_summary", {}, Exception("connection refused")
        )
        result = _check_dbt_freshness()
        assert result["status"] == "error"
        assert "connection refused" in result["error"] or result["error"] == "internal_error"


class TestCheckDataFreshness:
    @patch("datapulse.api.routes.health.get_engine")
    def test_ok(self, mock_engine):
        mock_conn = MagicMock()
        recent = datetime.now(UTC) - timedelta(hours=2)
        mock_conn.execute.return_value.fetchone.return_value = (recent,)
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None
        result = _check_data_freshness()
        assert result["status"] == "ok"
        assert "last_loaded_at" in result
        assert result["age_hours"] < 24

    @patch("datapulse.api.routes.health.get_engine")
    def test_stale(self, mock_engine):
        mock_conn = MagicMock()
        old_ts = datetime.now(UTC) - timedelta(hours=25)
        mock_conn.execute.return_value.fetchone.return_value = (old_ts,)
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None
        result = _check_data_freshness()
        assert result["status"] == "stale"
        assert result["age_hours"] > 24

    @patch("datapulse.api.routes.health.get_engine")
    def test_unknown_when_empty(self, mock_engine):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (None,)
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None
        result = _check_data_freshness()
        assert result["status"] == "unknown"
        assert result["last_loaded_at"] is None

    @patch("datapulse.api.routes.health.get_engine")
    def test_error(self, mock_engine):
        mock_engine.return_value.connect.side_effect = sqlalchemy.exc.OperationalError(
            "SELECT MAX(loaded_at) FROM bronze.sales", {}, Exception("db unavailable")
        )
        result = _check_data_freshness()
        assert result["status"] == "error"
        assert "db unavailable" in result["error"] or result["error"] == "internal_error"

"""Tests for health check component helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import redis
import sqlalchemy.exc
from fastapi import FastAPI
from fastapi.testclient import TestClient

from datapulse.api.routes.health import (
    _check_data_freshness,
    _check_db,
    _check_dbt_freshness,
    _check_query_executor,
    _check_redis,
    _check_table_bloat,
)


class TestCheckDb:
    @patch("datapulse.checks.get_engine")
    def test_ok(self, mock_engine):
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None
        result = _check_db()
        assert result["status"] == "ok"
        assert "latency_ms" in result

    @patch("datapulse.checks.get_engine")
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
        assert result["error"] == "internal_error"


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
        assert result["error"] == "internal_error"


class TestAuthCheck:
    """Tests for GET /health/auth-check endpoint."""

    @patch("datapulse.api.routes.health.get_engine")
    @patch("datapulse.config.get_settings")
    def test_ok(self, mock_settings, mock_engine):
        from datapulse.api.routes.health import router

        mock_settings.return_value.default_tenant_id = "1"
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        resp = client.get("/health/auth-check")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["default_tenant_id"] == "1"

    @patch("datapulse.config.get_settings")
    def test_no_default_tenant_id(self, mock_settings):
        from datapulse.api.routes.health import router

        mock_settings.return_value.default_tenant_id = ""

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        resp = client.get("/health/auth-check")
        assert resp.status_code == 503
        assert resp.json()["error"] == "no_default_tenant_id"

    @patch("datapulse.api.routes.health.get_engine")
    @patch("datapulse.config.get_settings")
    def test_db_error(self, mock_settings, mock_engine):
        from datapulse.api.routes.health import router

        mock_settings.return_value.default_tenant_id = "1"
        mock_engine.return_value.connect.side_effect = Exception("db down")

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        resp = client.get("/health/auth-check")
        assert resp.status_code == 503
        assert resp.json()["error"] == "tenant_session_failed"


# ---------------------------------------------------------------------------
# _check_table_bloat
# ---------------------------------------------------------------------------


def _make_bloat_row(schema, table, dead, live, last_vac=None, last_analyze=None):
    """Build a mock pg_stat_user_tables row tuple."""
    return (schema, table, dead, live, last_vac, last_analyze)


class TestCheckTableBloat:
    """Tests for the _check_table_bloat health helper."""

    @patch("datapulse.api.routes.health.get_engine")
    def test_all_ok(self, mock_engine):
        """Returns ok when all tables have fewer dead tuples than the warn threshold."""
        rows = [
            _make_bloat_row("pos", "transactions", 100, 50_000),
            _make_bloat_row("pos", "idempotency_keys", 50, 20_000),
            _make_bloat_row("bronze", "sales", 200, 100_000),
        ]
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = rows
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None

        result = _check_table_bloat()

        assert result["status"] == "ok"
        assert len(result["tables"]) == 3
        for t in result["tables"]:
            assert t["status"] == "ok"

    @patch("datapulse.api.routes.health.get_engine")
    def test_warning_threshold(self, mock_engine):
        """Returns warning when a table has 10k–100k dead tuples."""
        rows = [
            _make_bloat_row("pos", "transactions", 15_000, 200_000),
        ]
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = rows
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None

        result = _check_table_bloat()

        assert result["status"] == "warning"
        assert result["tables"][0]["status"] == "warning"

    @patch("datapulse.api.routes.health.get_engine")
    def test_critical_threshold(self, mock_engine):
        """Returns critical when a table has > 100k dead tuples."""
        rows = [
            _make_bloat_row("pos", "transactions", 150_000, 500_000),
        ]
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = rows
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None

        result = _check_table_bloat()

        assert result["status"] == "critical"
        assert result["tables"][0]["status"] == "critical"

    @patch("datapulse.api.routes.health.get_engine")
    def test_db_error_returns_error_status(self, mock_engine):
        """Returns error status (not a 500) when the DB query fails."""
        mock_engine.return_value.connect.side_effect = Exception("pg_stat unavailable")

        result = _check_table_bloat()

        assert result["status"] == "error"
        assert result["error"] == "internal_error"

    @patch("datapulse.api.routes.health.get_engine")
    def test_empty_result_ok(self, mock_engine):
        """Returns ok with empty table list when pg_stat returns no rows."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_engine.return_value.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.return_value.connect.return_value.__exit__ = lambda s, *a: None

        result = _check_table_bloat()

        assert result["status"] == "ok"
        assert result["tables"] == []

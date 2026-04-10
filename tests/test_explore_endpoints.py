"""Tests for explore API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from datapulse.explore.models import (
    Dimension,
    DimensionType,
    ExploreCatalog,
    ExploreModel,
    Metric,
    MetricType,
)


def _make_explore_client():
    """Build a TestClient with explore dependencies mocked."""
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


_FAKE_MODEL = ExploreModel(
    name="fct_sales",
    label="Sales Fact",
    schema_name="public_marts",
    dimensions=[
        Dimension(
            name="date_key", label="Date", dimension_type=DimensionType.date, model="fct_sales"
        )
    ],
    metrics=[
        Metric(
            name="total_sales",
            label="Total Sales",
            metric_type=MetricType.sum,
            column="net_amount",
            model="fct_sales",
        )
    ],
)

_FAKE_CATALOG = ExploreCatalog(models=[_FAKE_MODEL])


class TestListModels:
    @patch("datapulse.api.routes.explore._get_catalog", return_value=_FAKE_CATALOG)
    def test_list_models(self, mock_cat):
        client, _ = _make_explore_client()
        resp = client.get("/api/v1/explore/models")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["models"]) == 1
        assert data["models"][0]["name"] == "fct_sales"


class TestGetModel:
    @patch("datapulse.api.routes.explore._get_catalog", return_value=_FAKE_CATALOG)
    def test_get_model_found(self, mock_cat):
        client, _ = _make_explore_client()
        resp = client.get("/api/v1/explore/models/fct_sales")
        assert resp.status_code == 200
        assert resp.json()["name"] == "fct_sales"

    @patch("datapulse.api.routes.explore._get_catalog", return_value=_FAKE_CATALOG)
    def test_get_model_not_found(self, mock_cat):
        client, _ = _make_explore_client()
        resp = client.get("/api/v1/explore/models/nonexistent")
        assert resp.status_code == 404


class TestExecuteExploreQuery:
    @patch("datapulse.api.routes.explore._get_catalog", return_value=_FAKE_CATALOG)
    @patch("datapulse.api.routes.explore.build_sql")
    def test_query_success(self, mock_build_sql, mock_cat):
        client, mock_session = _make_explore_client()
        mock_build_sql.return_value = (
            "SELECT date_key, SUM(net_amount) FROM fct_sales GROUP BY 1",
            {},
        )

        mock_result = MagicMock()
        mock_result.keys.return_value = ["date_key", "total_sales"]
        mock_result.__iter__ = lambda self: iter([(20250101, 1000)])
        mock_session.execute.return_value = mock_result

        resp = client.post(
            "/api/v1/explore/query",
            json={"model": "fct_sales", "dimensions": ["date_key"], "metrics": ["total_sales"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["row_count"] == 1
        assert "date_key" in data["columns"]

    @patch("datapulse.api.routes.explore._get_catalog", return_value=_FAKE_CATALOG)
    @patch("datapulse.api.routes.explore.build_sql")
    def test_query_value_error(self, mock_build_sql, mock_cat):
        client, _ = _make_explore_client()
        mock_build_sql.side_effect = ValueError("bad field")

        resp = client.post(
            "/api/v1/explore/query",
            json={"model": "fct_sales", "dimensions": ["bad"], "metrics": []},
        )
        assert resp.status_code == 422

    @patch("datapulse.api.routes.explore._get_catalog", return_value=_FAKE_CATALOG)
    @patch("datapulse.api.routes.explore.build_sql")
    def test_query_execution_error(self, mock_build_sql, mock_cat):
        client, mock_session = _make_explore_client()
        mock_build_sql.return_value = ("SELECT 1", {})
        mock_session.execute.side_effect = RuntimeError("DB error")

        resp = client.post(
            "/api/v1/explore/query",
            json={"model": "fct_sales", "dimensions": [], "metrics": []},
        )
        assert resp.status_code == 500

    @patch("datapulse.api.routes.explore._get_catalog", return_value=_FAKE_CATALOG)
    @patch("datapulse.api.routes.explore.build_sql")
    def test_query_truncated(self, mock_build_sql, mock_cat):
        client, mock_session = _make_explore_client()
        mock_build_sql.return_value = ("SELECT 1", {})

        rows = [(i,) for i in range(20)]
        mock_result = MagicMock()
        mock_result.keys.return_value = ["v"]
        mock_result.__iter__ = lambda self: iter(rows)
        mock_session.execute.return_value = mock_result

        resp = client.post(
            "/api/v1/explore/query",
            json={"model": "fct_sales", "dimensions": [], "metrics": [], "limit": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["truncated"] is True
        assert data["row_count"] == 5


class TestRefreshCatalog:
    @patch("datapulse.api.routes.explore.refresh_catalog")
    def test_refresh_catalog(self, mock_refresh):
        mock_refresh.return_value = _FAKE_CATALOG
        client, _ = _make_explore_client()
        resp = client.post("/api/v1/explore/refresh-catalog")
        assert resp.status_code == 200
        mock_refresh.assert_called_once()


class TestExecuteExploreQueryExtra:
    @patch("datapulse.api.routes.explore._get_catalog", return_value=_FAKE_CATALOG)
    @patch("datapulse.api.routes.explore.build_sql")
    def test_sql_field_hidden_in_production(self, mock_build_sql, mock_cat):
        client, mock_session = _make_explore_client()
        mock_build_sql.return_value = ("SELECT 1", {})

        mock_result = MagicMock()
        mock_result.keys.return_value = ["col"]
        mock_result.__iter__ = lambda self: iter([(1,)])
        mock_session.execute.return_value = mock_result

        # Patch os.getenv at the stdlib level — the route uses a local `import os`
        with patch("os.getenv", return_value="production"):
            resp = client.post(
                "/api/v1/explore/query",
                json={"model": "fct_sales", "dimensions": [], "metrics": []},
            )
        assert resp.status_code == 200
        assert resp.json()["sql"] == ""

    @patch("datapulse.api.routes.explore._get_catalog", return_value=_FAKE_CATALOG)
    @patch("datapulse.api.routes.explore.build_sql")
    def test_sql_field_shown_in_development(self, mock_build_sql, mock_cat):
        client, mock_session = _make_explore_client()
        mock_build_sql.return_value = ("SELECT date_key FROM fct_sales", {})

        mock_result = MagicMock()
        mock_result.keys.return_value = ["date_key"]
        mock_result.__iter__ = lambda self: iter([(20250101,)])
        mock_session.execute.return_value = mock_result

        with patch("os.getenv", return_value="development"):
            resp = client.post(
                "/api/v1/explore/query",
                json={"model": "fct_sales", "dimensions": ["date_key"], "metrics": []},
            )
        assert resp.status_code == 200
        assert resp.json()["sql"] != ""

    @patch("datapulse.api.routes.explore._get_catalog", return_value=_FAKE_CATALOG)
    @patch("datapulse.api.routes.explore.build_sql")
    def test_injection_attempt_rejected_as_422(self, mock_build_sql, mock_cat):
        mock_build_sql.side_effect = ValueError("not in whitelist")
        client, _ = _make_explore_client()

        resp = client.post(
            "/api/v1/explore/query",
            json={
                "model": "fct_sales",
                "dimensions": ["; DROP TABLE fct_sales; --"],
                "metrics": [],
            },
        )
        assert resp.status_code == 422

    @patch("datapulse.api.routes.explore._get_catalog", return_value=_FAKE_CATALOG)
    @patch("datapulse.api.routes.explore.build_sql")
    def test_empty_result_set(self, mock_build_sql, mock_cat):
        mock_build_sql.return_value = ("SELECT date_key FROM fct_sales", {})
        client, mock_session = _make_explore_client()

        mock_result = MagicMock()
        mock_result.keys.return_value = ["date_key"]
        mock_result.__iter__ = lambda self: iter([])
        mock_session.execute.return_value = mock_result

        resp = client.post(
            "/api/v1/explore/query",
            json={"model": "fct_sales", "dimensions": ["date_key"], "metrics": []},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["row_count"] == 0
        assert data["truncated"] is False

    @patch("datapulse.api.routes.explore._get_catalog", return_value=_FAKE_CATALOG)
    @patch("datapulse.api.routes.explore.build_sql")
    def test_pagination_default_limit(self, mock_build_sql, mock_cat):
        mock_build_sql.return_value = ("SELECT date_key FROM fct_sales", {})
        client, mock_session = _make_explore_client()

        rows = [(i,) for i in range(10)]
        mock_result = MagicMock()
        mock_result.keys.return_value = ["date_key"]
        mock_result.__iter__ = lambda self: iter(rows)
        mock_session.execute.return_value = mock_result

        # Post without a "limit" key — uses ExploreQuery default (500)
        resp = client.post(
            "/api/v1/explore/query",
            json={"model": "fct_sales", "dimensions": ["date_key"], "metrics": []},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["row_count"] == 10
        assert data["truncated"] is False

    @patch("datapulse.api.routes.explore._get_catalog", return_value=_FAKE_CATALOG)
    @patch("datapulse.api.routes.explore.build_sql")
    def test_filter_combinations(self, mock_build_sql, mock_cat):
        mock_build_sql.return_value = ("SELECT 1", {"p0": "20250101"})
        client, mock_session = _make_explore_client()

        mock_result = MagicMock()
        mock_result.keys.return_value = ["col"]
        mock_result.__iter__ = lambda self: iter([(1,)])
        mock_session.execute.return_value = mock_result

        resp = client.post(
            "/api/v1/explore/query",
            json={
                "model": "fct_sales",
                "dimensions": ["date_key"],
                "metrics": [],
                "filters": [{"field": "date_key", "operator": "eq", "value": "20250101"}],
            },
        )
        assert resp.status_code == 200
        # Verify build_sql was called with a body that includes the filter
        call_args = mock_build_sql.call_args
        query_body = call_args[0][0]
        assert len(query_body.filters) == 1
        assert query_body.filters[0].field == "date_key"
        assert query_body.filters[0].value == "20250101"


class TestSerialise:
    def test_serialise_types(self):
        from datetime import date, datetime
        from decimal import Decimal

        from datapulse.api.routes.explore import _serialise

        assert _serialise(None) is None
        assert _serialise(Decimal("10.5")) == 10.5
        assert _serialise(datetime(2025, 1, 1, 12, 0)) == "2025-01-01T12:00:00"
        assert _serialise(date(2025, 1, 1)) == "2025-01-01"
        assert _serialise(42) == 42
        assert _serialise(True) is True
        assert _serialise(3.14) == 3.14
        assert _serialise("s") == "s"
        # fallback
        assert isinstance(_serialise(object()), str)

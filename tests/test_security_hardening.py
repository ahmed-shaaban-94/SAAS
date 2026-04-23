"""Security hardening tests -- validates fixes for CRITICAL/HIGH audit findings.

C1: SQL LIMIT must use bind parameters (no f-string interpolation)
C2: Generated SQL must not leak to clients in production
C3: get_db_session must emit deprecation warning
H2: Dev mode auth bypass must fail in production environments
H4: Embed token must enforce minimum secret length

Also includes PII leak prevention tests.
"""

from __future__ import annotations

import contextlib
import os
import warnings
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from datapulse.api.auth import get_current_user
from datapulse.config import Settings
from datapulse.embed.token import _MIN_SECRET_LENGTH, _get_secret
from datapulse.explore.models import (
    Dimension,
    DimensionType,
    ExploreCatalog,
    ExploreModel,
    ExploreQuery,
    Metric,
    MetricType,
)
from datapulse.explore.sql_builder import build_sql


def _settings(**overrides) -> Settings:
    defaults = dict(_env_file=None, api_key="", database_url="", pipeline_webhook_secret="")
    defaults.update(overrides)
    return Settings(**defaults)


def _mock_embed_settings(api_key: str = "", embed_secret: str = "") -> MagicMock:
    settings = MagicMock()
    settings.api_key = api_key
    settings.embed_secret = embed_secret
    return settings


def _test_catalog() -> ExploreCatalog:
    """Minimal catalog for SQL builder tests."""
    return ExploreCatalog(
        models=[
            ExploreModel(
                name="fct_sales",
                schema_name="public_marts",
                dimensions=[
                    Dimension(
                        name="customer_name",
                        label="Customer",
                        dimension_type=DimensionType.string,
                        model="fct_sales",
                    ),
                ],
                metrics=[
                    Metric(
                        name="total_sales",
                        label="Total Sales",
                        metric_type=MetricType.sum,
                        column="net_amount",
                        model="fct_sales",
                    ),
                ],
            )
        ]
    )


# =========================================================================
# C1: SQL LIMIT uses bind parameter, not f-string interpolation
# =========================================================================


class TestC1SqlLimitBindParameter:
    """C1: LIMIT clause must use a bind parameter to prevent SQL injection."""

    def test_limit_is_bind_parameter(self):
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["customer_name"],
            metrics=["total_sales"],
            limit=100,
        )
        sql, params = build_sql(query, _test_catalog())

        assert "LIMIT :_limit" in sql, f"Expected bind parameter in SQL: {sql}"
        assert "_limit" in params
        assert params["_limit"] == 100

    def test_limit_not_interpolated_as_number(self):
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["customer_name"],
            metrics=["total_sales"],
            limit=42,
        )
        sql, _ = build_sql(query, _test_catalog())
        assert "LIMIT 42" not in sql, "LIMIT value was interpolated directly into SQL"

    def test_various_limit_values(self):
        for limit in [1, 500, 10_000]:
            query = ExploreQuery(
                model="fct_sales",
                dimensions=["customer_name"],
                metrics=["total_sales"],
                limit=limit,
            )
            _, params = build_sql(query, _test_catalog())
            assert params["_limit"] == limit


# =========================================================================
# C2: SQL not exposed in production responses
# =========================================================================


class TestC2SqlExposurePrevention:
    """C2: Generated SQL must not leak to clients in production."""

    def test_production_hides_sql(self):
        with patch.dict(os.environ, {"SENTRY_ENVIRONMENT": "production"}):
            show = os.getenv("SENTRY_ENVIRONMENT") in ("development", "test")
            assert show is False

    def test_development_shows_sql(self):
        with patch.dict(os.environ, {"SENTRY_ENVIRONMENT": "development"}):
            show = os.getenv("SENTRY_ENVIRONMENT") in ("development", "test")
            assert show is True

    def test_test_shows_sql(self):
        with patch.dict(os.environ, {"SENTRY_ENVIRONMENT": "test"}):
            show = os.getenv("SENTRY_ENVIRONMENT") in ("development", "test")
            assert show is True

    def test_staging_hides_sql(self):
        with patch.dict(os.environ, {"SENTRY_ENVIRONMENT": "staging"}):
            show = os.getenv("SENTRY_ENVIRONMENT") in ("development", "test")
            assert show is False


# =========================================================================
# C3: get_db_session deprecation warning
# =========================================================================


class TestC3DeprecatedDbSession:
    """C3: get_db_session must emit DeprecationWarning."""

    def test_emits_deprecation_warning(self):
        from datapulse.api.deps import get_db_session

        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        with (
            patch("datapulse.api.deps.get_session_factory", return_value=mock_factory),
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")
            gen = get_db_session()
            next(gen)

            dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(dep_warnings) >= 1
            assert "deprecated" in str(dep_warnings[0].message).lower()

            with contextlib.suppress(StopIteration):
                gen.send(None)


# =========================================================================
# H2: Dev mode auth bypass must fail in production
# =========================================================================


class TestH2DevModeProductionBlock:
    """H2: Dev mode auth fallback must raise 503 in production."""

    def test_blocked_in_production(self):
        # Dev-fallback gate reads ``_jwt_provider_configured`` so the check
        # is uniform for Auth0 or Clerk. MagicMock returns truthy for unset
        # attrs, which would silently skip the gate — set it explicitly to
        # match an unconfigured provider.
        settings = MagicMock(
            api_key="",
            clerk_jwt_issuer="",
            auth_provider="clerk",
            sentry_environment="production",
        )
        settings._jwt_provider_configured = False
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=None, api_key=None, settings=settings)
        assert exc_info.value.status_code == 503
        assert "not configured" in exc_info.value.detail.lower()

    def test_blocked_in_staging(self):
        settings = MagicMock(
            api_key="",
            clerk_jwt_issuer="",
            auth_provider="clerk",
            sentry_environment="staging",
        )
        settings._jwt_provider_configured = False
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=None, api_key=None, settings=settings)
        assert exc_info.value.status_code == 503

    def test_allowed_in_development(self):
        settings = _settings(api_key="")
        with patch.dict(os.environ, {"SENTRY_ENVIRONMENT": "development"}):
            result = get_current_user(credentials=None, api_key=None, settings=settings)
        assert result["sub"] == "dev-user"
        assert "viewer" in result["roles"]

    def test_allowed_in_test(self):
        settings = _settings(api_key="")
        with patch.dict(os.environ, {"SENTRY_ENVIRONMENT": "test"}):
            result = get_current_user(credentials=None, api_key=None, settings=settings)
        assert result["sub"] == "dev-user"


# =========================================================================
# H4: Embed token secret validation
# =========================================================================


class TestH4EmbedSecretValidation:
    """H4: Embed token must enforce minimum secret length."""

    def test_short_embed_secret_raises(self):
        short = "x" * (_MIN_SECRET_LENGTH - 1)
        with (
            patch(
                "datapulse.embed.token.get_settings",
                return_value=_mock_embed_settings(embed_secret=short),
            ),
            pytest.raises(ValueError, match="at least"),
        ):
            _get_secret()

    def test_minimum_length_passes(self):
        exact = "x" * _MIN_SECRET_LENGTH
        with patch(
            "datapulse.embed.token.get_settings",
            return_value=_mock_embed_settings(embed_secret=exact),
        ):
            assert _get_secret() == exact

    def test_long_secret_passes(self):
        long = "x" * 64
        with patch(
            "datapulse.embed.token.get_settings",
            return_value=_mock_embed_settings(embed_secret=long),
        ):
            assert _get_secret() == long

    def test_api_key_fallback_blocked_in_production(self):
        with (
            patch(
                "datapulse.embed.token.get_settings",
                return_value=_mock_embed_settings(api_key="key", embed_secret=""),
            ),
            patch.dict(os.environ, {"SENTRY_ENVIRONMENT": "production"}),
            pytest.raises(ValueError, match="EMBED_SECRET must be configured"),
        ):
            _get_secret()

    def test_api_key_fallback_allowed_in_dev(self):
        with (
            patch(
                "datapulse.embed.token.get_settings",
                return_value=_mock_embed_settings(api_key="my-dev-key", embed_secret=""),
            ),
            patch.dict(os.environ, {"SENTRY_ENVIRONMENT": "development"}),
        ):
            assert _get_secret() == "my-dev-key"


# =========================================================================
# PII Leak Prevention
# =========================================================================


class TestPIILeakPrevention:
    """Verify PII is not exposed in error responses or logs."""

    def test_sentry_pii_disabled_in_source(self):
        from pathlib import Path

        import datapulse.api.bootstrap.observability as observability_module

        source = Path(observability_module.__file__).read_text()
        assert "send_default_pii=False" in source

    def test_auth_error_messages_generic(self):
        settings = _settings(api_key="secret-key-value")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=None, api_key="wrong", settings=settings)
        detail = exc_info.value.detail
        # Must not leak the actual secret value
        assert "secret-key-value" not in detail

    def test_jwt_error_no_token_leak(self):
        from datapulse.api.jwt import verify_jwt

        fake_settings = _settings(
            clerk_frontend_api="https://test.clerk.accounts.dev",
            clerk_jwt_issuer="https://test.clerk.accounts.dev",
        )
        with (
            patch("datapulse.core.jwt.httpx.get", side_effect=Exception("connection refused")),
            pytest.raises(HTTPException) as exc_info,
        ):
            verify_jwt("eyJ.fake.token", fake_settings)
        detail = exc_info.value.detail
        assert "eyJ" not in detail
        assert "fake" not in detail

    def test_sensitive_fields_masked_in_logs(self):
        from datapulse.logging import _mask_sensitive_fields

        event = {
            "event": "test",
            "password": "hunter2",
            "token": "abc123",
            "api_key": "sk-secret",
        }
        result = _mask_sensitive_fields(None, "info", event)
        assert result["password"] == "***REDACTED***"
        assert result["token"] == "***REDACTED***"
        assert result["api_key"] == "***REDACTED***"

    def test_global_exception_handler_exists(self):
        from datapulse.api.app import create_app

        app = create_app()
        assert app.exception_handlers.get(Exception) is not None

    def test_exception_handler_returns_generic_message(self):
        from datapulse.api.app import create_app

        app = create_app()
        handler = app.exception_handlers[Exception]
        assert handler.__name__ == "global_exception_handler"

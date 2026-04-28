"""Regression tests for [P0][SEC] #537 — dev-mode auth fallback must not be reachable in production.

The pre-fix gate was a single string comparison on ``sentry_environment``.
Setting ``SENTRY_ENVIRONMENT=development`` on a production deployment with
empty ``api_key`` / ``auth0_domain`` bypassed both the startup validator and
the runtime ``get_current_user`` fallback, returning fake ``tenant_id=1``,
``roles=["viewer"]`` claims to unauthenticated callers.

The fix introduces ``app_env`` as an authoritative deployment-mode field and
tightens both gates to refuse the fallback whenever *either* ``app_env`` or
``sentry_environment`` indicates a non-dev environment (OR logic — defense
in depth, can't be bypassed by misconfiguring a single variable).
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from datapulse.api.auth import get_current_user
from datapulse.config import Settings


def _prod_settings_with_dev_sentry_label(**overrides) -> Settings:
    """Construct settings for the exact bypass scenario.

    ``app_env=production`` (real deployment mode) with
    ``sentry_environment=development`` (misconfigured telemetry label) and
    both auth secrets empty. Pre-fix, this configuration loaded without
    error and leaked dev claims at runtime.
    """
    defaults = dict(
        _env_file=None,
        app_env="production",
        sentry_environment="development",
        api_key="",
        auth0_domain="",
        database_url="",
        pipeline_webhook_secret="disabled-for-test",
        db_reader_password="test",
        pharmacist_signing_secret="disabled-for-test",
    )
    defaults.update(overrides)
    return Settings(**defaults)


class TestStartupGateCannotBeBypassed:
    """Startup validator refuses non-dev ``app_env`` regardless of ``sentry_environment``."""

    def test_production_app_env_with_dev_sentry_raises(self):
        """The primary bypass: app_env=production, sentry_environment=development, no auth."""
        with pytest.raises(ValidationError, match="Auth must be configured"):
            _prod_settings_with_dev_sentry_label()

    def test_production_app_env_with_test_sentry_raises(self):
        """Same bypass with sentry_environment=test — still must fail."""
        with pytest.raises(ValidationError, match="Auth must be configured"):
            _prod_settings_with_dev_sentry_label(sentry_environment="test")

    def test_staging_app_env_with_dev_sentry_raises(self):
        """Staging is also a non-dev environment — dev fallback must not be allowed."""
        with pytest.raises(ValidationError, match="Auth must be configured"):
            _prod_settings_with_dev_sentry_label(app_env="staging")

    def test_production_app_env_passes_when_auth_configured(self):
        """Sanity check: production app_env + configured auth should NOT raise."""
        _prod_settings_with_dev_sentry_label(api_key="real-key")

    def test_development_default_still_works(self):
        """Sanity check: default dev environment with empty auth must still be allowed."""
        Settings(
            _env_file=None,
            database_url="",
            pipeline_webhook_secret="",
            api_key="",
            auth0_domain="",
        )

    def test_app_env_loads_from_environment_variable(self, monkeypatch):
        """APP_ENV env var must map to ``app_env`` — else the guard fails open.

        Unit tests pass ``app_env`` as a kwarg, but real deployments rely on
        pydantic_settings auto-mapping the env var. If the mapping breaks
        (renamed field, added ``env_prefix``, etc.) the code default
        ``"development"`` silently wins and re-opens the bypass this fix
        was designed to close.
        """
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("API_KEY", "configured-for-test")
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("PIPELINE_WEBHOOK_SECRET", "disabled-for-test")
        monkeypatch.setenv("DB_READER_PASSWORD", "test")
        monkeypatch.setenv("PHARMACIST_SIGNING_SECRET", "disabled-for-test")
        settings = Settings(_env_file=None)
        assert settings.app_env == "production"


class TestRuntimeGateCannotBeBypassed:
    """``get_current_user`` must refuse the dev fallback in any non-dev ``app_env``."""

    def _build_settings_bypassing_startup(self, **overrides):
        """Build a Settings instance simulating the misconfigured-at-runtime scenario.

        We cannot directly instantiate ``Settings`` with the bypass config (the
        startup validator now blocks it). Instead, we construct dev settings
        and monkey-patch ``app_env`` to simulate a deployment whose validator
        was somehow skipped (e.g. a future code path that bypasses validation).
        """
        settings = Settings(
            _env_file=None,
            database_url="",
            pipeline_webhook_secret="",
            api_key="",
            auth0_domain="",
            sentry_environment="development",
        )
        object.__setattr__(settings, "app_env", overrides.get("app_env", "production"))
        return settings

    def test_production_app_env_refuses_dev_fallback(self):
        """Runtime gate must refuse even if app_env==production slipped past startup."""
        settings = self._build_settings_bypassing_startup(app_env="production")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=None, api_key=None, settings=settings)
        assert exc_info.value.status_code == 503
        assert "not configured" in exc_info.value.detail.lower()

    def test_staging_app_env_refuses_dev_fallback(self):
        """Staging also must not get dev claims."""
        settings = self._build_settings_bypassing_startup(app_env="staging")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=None, api_key=None, settings=settings)
        assert exc_info.value.status_code == 503

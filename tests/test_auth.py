"""Tests for datapulse.api.auth — authentication and authorization dependencies."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from datapulse.api.auth import (
    get_current_user,
    get_optional_user,
    require_api_key,
    require_pipeline_token,
)
from datapulse.config import Settings


def _settings(**overrides) -> Settings:
    defaults = dict(
        _env_file=None,
        api_key="",
        database_url="",
        pipeline_webhook_secret="",
        sentry_environment="test",
    )
    defaults.update(overrides)
    return Settings(**defaults)


# ------------------------------------------------------------------
# require_api_key
# ------------------------------------------------------------------


class TestRequireApiKey:
    def test_dev_mode_skips(self):
        """No api_key configured -> dev mode, should pass."""
        require_api_key(api_key=None, settings=_settings(api_key=""))

    def test_valid_key(self):
        require_api_key(api_key="secret123", settings=_settings(api_key="secret123"))

    def test_invalid_key_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            require_api_key(api_key="wrong", settings=_settings(api_key="secret123"))
        assert exc_info.value.status_code == 401

    def test_missing_key_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            require_api_key(api_key=None, settings=_settings(api_key="secret123"))
        assert exc_info.value.status_code == 401

    def test_empty_key_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            require_api_key(api_key="", settings=_settings(api_key="secret123"))
        assert exc_info.value.status_code == 401


# ------------------------------------------------------------------
# require_pipeline_token
# ------------------------------------------------------------------


class TestRequirePipelineToken:
    def test_empty_secret_raises_503(self):
        """Empty secret always raises 503 — no env-var escape (issue #539)."""
        with pytest.raises(HTTPException) as exc_info:
            require_pipeline_token(token=None, settings=_settings(pipeline_webhook_secret=""))
        assert exc_info.value.status_code == 503

    def test_pipeline_auth_disabled_env_var_is_inert(self):
        """The legacy PIPELINE_AUTH_DISABLED kill-switch must have no effect.

        Regression guard for #539: pre-fix, setting this env var to "true"
        with an empty secret caused require_pipeline_token to return
        successfully (no auth). The kill-switch was removed entirely;
        setting the env var must not change behavior.
        """
        with (
            patch.dict(os.environ, {"PIPELINE_AUTH_DISABLED": "true"}),
            pytest.raises(HTTPException) as exc_info,
        ):
            require_pipeline_token(token=None, settings=_settings(pipeline_webhook_secret=""))
        assert exc_info.value.status_code == 503

    def test_valid_token(self):
        require_pipeline_token(token="tok123", settings=_settings(pipeline_webhook_secret="tok123"))

    def test_invalid_token_raises_403(self):
        with pytest.raises(HTTPException) as exc_info:
            require_pipeline_token(
                token="wrong", settings=_settings(pipeline_webhook_secret="tok123")
            )
        assert exc_info.value.status_code == 403

    def test_missing_token_raises_403(self):
        with pytest.raises(HTTPException) as exc_info:
            require_pipeline_token(token=None, settings=_settings(pipeline_webhook_secret="tok123"))
        assert exc_info.value.status_code == 403

    def test_empty_token_raises_403(self):
        with pytest.raises(HTTPException) as exc_info:
            require_pipeline_token(token="", settings=_settings(pipeline_webhook_secret="tok123"))
        assert exc_info.value.status_code == 403


# ------------------------------------------------------------------
# get_current_user
# ------------------------------------------------------------------


class TestGetCurrentUser:
    def test_jwt_bearer_token(self):
        """When Bearer token is present, verify_jwt is called and claims returned."""
        creds = MagicMock()
        creds.credentials = "jwt-token-value"
        fake_claims = {
            "sub": "user123",
            "email": "user@example.com",
            "preferred_username": "user123",
            "tenant_id": "42",
            "https://datapulse.tech/roles": ["admin"],
        }
        with patch("datapulse.core.auth.verify_jwt", return_value=fake_claims):
            result = get_current_user(
                credentials=creds,
                api_key=None,
                settings=_settings(api_key="key", auth0_domain="example.auth0.com"),
            )
        assert result["sub"] == "user123"
        assert result["tenant_id"] == "42"
        assert result["roles"] == ["admin"]

    def test_jwt_missing_tenant_id_falls_back_to_default(self):
        """When tenant_id is missing from JWT claims, falls back to default_tenant_id."""
        creds = MagicMock()
        creds.credentials = "jwt-token-value"
        fake_claims = {"sub": "user123"}
        with patch("datapulse.core.auth.verify_jwt", return_value=fake_claims):
            result = get_current_user(
                credentials=creds,
                api_key=None,
                settings=_settings(api_key="key"),
            )
        assert result["tenant_id"] == "1"  # default_tenant_id

    def test_jwt_missing_tenant_id_rejects_401_in_production(self):
        """#546: production must not fall back to default_tenant_id silently."""
        creds = MagicMock()
        creds.credentials = "jwt-token-value"
        fake_claims = {"sub": "user123"}
        prod_settings = _settings(
            app_env="production",
            sentry_environment="production",
            api_key="prod-key",
            auth0_domain="example.auth0.com",
            db_reader_password="reader-secret",
            pipeline_webhook_secret="pipeline-secret",
            pharmacist_signing_secret="pharmacist-secret",
        )
        with (
            patch("datapulse.core.auth.verify_jwt", return_value=fake_claims),
            pytest.raises(HTTPException) as exc_info,
        ):
            get_current_user(credentials=creds, api_key=None, settings=prod_settings)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "JWT missing tenant context"

    def test_jwt_missing_tenant_id_rejects_401_in_staging(self):
        """#546: staging is also non-dev — same strict rejection as production."""
        creds = MagicMock()
        creds.credentials = "jwt-token-value"
        fake_claims = {"sub": "user123"}
        stage_settings = _settings(
            app_env="staging",
            sentry_environment="staging",
            api_key="stage-key",
            auth0_domain="example.auth0.com",
            db_reader_password="reader-secret",
            pipeline_webhook_secret="pipeline-secret",
            pharmacist_signing_secret="pharmacist-secret",
        )
        with (
            patch("datapulse.core.auth.verify_jwt", return_value=fake_claims),
            pytest.raises(HTTPException) as exc_info,
        ):
            get_current_user(credentials=creds, api_key=None, settings=stage_settings)
        assert exc_info.value.status_code == 401

    def test_jwt_missing_tenant_id_dev_fallback_is_rate_limited(self):
        """#546: dev warning fires once per minute, not on every request."""
        from datapulse.core import auth as auth_mod

        auth_mod._log_dev_tenant_fallback_once.cache_clear()
        creds = MagicMock()
        creds.credentials = "jwt-token-value"
        fake_claims = {"sub": "user123"}
        with (
            patch("datapulse.core.auth.verify_jwt", return_value=fake_claims),
            patch.object(auth_mod, "_auth_logger") as mock_logger,
            patch("datapulse.core.auth.time.monotonic", return_value=60.0),
        ):
            for _ in range(5):
                get_current_user(
                    credentials=creds,
                    api_key=None,
                    settings=_settings(api_key="key"),
                )
        fallback_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and c.args[0] == "jwt_missing_tenant_id_dev_fallback"
        ]
        assert len(fallback_calls) == 1, (
            f"Expected exactly one fallback warning per minute bucket, got {len(fallback_calls)}"
        )

    def test_jwt_tid_claim_accepted(self):
        """When tenant_id is missing but 'tid' is present, it is used."""
        creds = MagicMock()
        creds.credentials = "jwt-token-value"
        fake_claims = {"sub": "user123", "tid": "99"}
        with patch("datapulse.core.auth.verify_jwt", return_value=fake_claims):
            result = get_current_user(
                credentials=creds,
                api_key=None,
                settings=_settings(api_key="key"),
            )
        assert result["tenant_id"] == "99"
        assert result["roles"] == []

    def test_jwt_namespaced_tenant_id_accepted(self):
        """Auth0 namespaced claim https://datapulse.tech/tenant_id is accepted."""
        creds = MagicMock()
        creds.credentials = "jwt-token-value"
        fake_claims = {
            "sub": "user123",
            "https://datapulse.tech/tenant_id": 7,
        }
        with patch("datapulse.core.auth.verify_jwt", return_value=fake_claims):
            result = get_current_user(
                credentials=creds,
                api_key=None,
                settings=_settings(api_key="key"),
            )
        assert result["tenant_id"] == "7"

    @pytest.mark.parametrize("tenant_id", ["abc", "12345678901", "1 OR 1=1", "12-34"])
    def test_invalid_tenant_id_claim_raises_401(self, tenant_id):
        creds = MagicMock()
        creds.credentials = "jwt-token-value"
        fake_claims = {"sub": "user123", "tenant_id": tenant_id}
        with (
            patch("datapulse.core.auth.verify_jwt", return_value=fake_claims),
            pytest.raises(HTTPException) as exc_info,
        ):
            get_current_user(
                credentials=creds,
                api_key=None,
                settings=_settings(api_key="key", auth0_domain="example.auth0.com"),
            )
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid tenant context"

    def test_api_key_fallback_valid(self):
        """No Bearer token, valid API key -> returns stub claims with configured roles."""
        result = get_current_user(
            credentials=None,
            api_key="secret123",
            settings=_settings(api_key="secret123"),
        )
        assert result["sub"] == "api-key-user"
        assert result["tenant_id"] == "1"
        assert "api-reader" in result["roles"]  # default role, not admin

    def test_api_key_custom_roles(self):
        """API key roles can be customised via settings."""
        result = get_current_user(
            credentials=None,
            api_key="secret123",
            settings=_settings(api_key="secret123", api_key_roles=["viewer", "export"]),
        )
        assert result["roles"] == ["viewer", "export"]

    def test_api_key_custom_tenant(self):
        """API key tenant_id uses default_tenant_id from settings."""
        result = get_current_user(
            credentials=None,
            api_key="secret123",
            settings=_settings(api_key="secret123", default_tenant_id="42"),
        )
        assert result["tenant_id"] == "42"

    def test_api_key_fallback_invalid(self):
        """No Bearer token, invalid API key -> 401."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(
                credentials=None,
                api_key="wrong",
                settings=_settings(api_key="secret123"),
            )
        assert exc_info.value.status_code == 401

    def test_dev_mode(self):
        """No Bearer, no API key, no auth configured -> dev claims."""
        result = get_current_user(
            credentials=None,
            api_key=None,
            settings=_settings(api_key="", auth0_domain=""),
        )
        assert result["sub"] == "dev-user"
        assert result["tenant_id"] == "1"

    def test_dev_mode_non_dev_environment_raises_at_startup(self):
        """Unconfigured auth in production raises ValueError at startup (T1.1)."""
        with pytest.raises(ValidationError, match="Auth must be configured"):
            Settings(
                _env_file=None,
                api_key="",
                auth0_domain="",
                database_url="",
                pipeline_webhook_secret="",
                sentry_environment="production",
            )

    def test_no_auth_but_configured_raises_401(self):
        """No credentials but auth IS configured -> 401."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(
                credentials=None,
                api_key=None,
                settings=_settings(api_key="configured-key"),
            )
        assert exc_info.value.status_code == 401

    def test_jwt_locale_claim_surfaced(self):
        """Auth0 'locale' claim lands on UserClaims['locale']."""
        creds = MagicMock()
        creds.credentials = "jwt-token-value"
        fake_claims = {
            "sub": "user123",
            "tenant_id": "42",
            "locale": "ar-EG",
        }
        with patch("datapulse.core.auth.verify_jwt", return_value=fake_claims):
            result = get_current_user(
                credentials=creds,
                api_key=None,
                settings=_settings(api_key="key", auth0_domain="example.auth0.com"),
            )
        assert result["locale"] == "ar-EG"

    def test_jwt_missing_locale_claim_defaults_to_en_us(self):
        creds = MagicMock()
        creds.credentials = "jwt-token-value"
        fake_claims = {"sub": "user123", "tenant_id": "42"}
        with patch("datapulse.core.auth.verify_jwt", return_value=fake_claims):
            result = get_current_user(
                credentials=creds,
                api_key=None,
                settings=_settings(api_key="key", auth0_domain="example.auth0.com"),
            )
        assert result["locale"] == "en-US"


# ------------------------------------------------------------------
# get_optional_user
# ------------------------------------------------------------------


class TestGetOptionalUser:
    def test_returns_user_on_success(self):
        result = get_optional_user(
            credentials=None,
            api_key=None,
            settings=_settings(api_key="", auth0_domain=""),
        )
        assert result is not None
        assert result["sub"] == "dev-user"

    def test_returns_none_on_401(self):
        """401 Unauthorized (bad/missing credentials) must return None, not raise."""
        result = get_optional_user(
            credentials=None,
            api_key=None,
            settings=_settings(api_key="configured-key"),
        )
        assert result is None

    def test_returns_none_on_403(self):
        """403 Forbidden must return None — caller handles auth failure gracefully."""
        creds = MagicMock()
        creds.credentials = "expired-jwt"
        with patch(
            "datapulse.core.auth.verify_jwt",
            side_effect=HTTPException(status_code=403, detail="Forbidden"),
        ):
            result = get_optional_user(
                credentials=creds,
                api_key=None,
                settings=_settings(api_key="key", auth0_domain="example.auth0.com"),
            )
        assert result is None

    def test_reraises_503_not_swallowed(self):
        """503 Service Unavailable (Auth0 outage) must be re-raised, not swallowed.

        H2.2 fix: get_optional_user must only catch 401/403; any 503 from the
        auth provider must propagate so the caller (health endpoint, middleware)
        can surface the dependency failure instead of silently granting access.

        This test will FAIL against H1 (which catches all HTTPException) and
        PASS after H2 is merged into main.
        """
        creds = MagicMock()
        creds.credentials = "any-token"
        with (
            patch(
                "datapulse.core.auth.verify_jwt",
                side_effect=HTTPException(status_code=503, detail="Auth0 unavailable"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            get_optional_user(
                credentials=creds,
                api_key=None,
                settings=_settings(api_key="key", auth0_domain="example.auth0.com"),
            )
        assert exc_info.value.status_code == 503, (
            "get_optional_user must re-raise 503 (Auth0 outage) — "
            "silently returning None would grant anonymous access during an auth provider outage."
        )

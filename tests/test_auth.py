"""Tests for datapulse.api.auth — authentication and authorization dependencies."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from datapulse.api.auth import (
    get_current_user,
    get_optional_user,
    require_api_key,
    require_pipeline_token,
)
from datapulse.config import Settings


def _settings(**overrides) -> Settings:
    defaults = dict(_env_file=None, api_key="", database_url="", pipeline_webhook_secret="")
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
    def test_dev_mode_skips(self):
        require_pipeline_token(token=None, settings=_settings(pipeline_webhook_secret=""))

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
        with patch("datapulse.api.auth.verify_jwt", return_value=fake_claims):
            result = get_current_user(
                credentials=creds,
                api_key=None,
                settings=_settings(api_key="key", auth0_domain="example.auth0.com"),
            )
        assert result["sub"] == "user123"
        assert result["tenant_id"] == "42"
        assert result["roles"] == ["admin"]

    def test_jwt_fallback_tenant_id(self):
        """When tenant_id not in claims, falls back to '1'."""
        creds = MagicMock()
        creds.credentials = "jwt-token-value"
        fake_claims = {"sub": "user123"}
        with patch("datapulse.api.auth.verify_jwt", return_value=fake_claims):
            result = get_current_user(
                credentials=creds,
                api_key=None,
                settings=_settings(api_key="key"),
            )
        assert result["tenant_id"] == "1"
        assert result["roles"] == []

    def test_api_key_fallback_valid(self):
        """No Bearer token, valid API key -> returns stub claims."""
        result = get_current_user(
            credentials=None,
            api_key="secret123",
            settings=_settings(api_key="secret123"),
        )
        assert result["sub"] == "api-key-user"
        assert result["tenant_id"] == "1"
        assert "admin" in result["roles"]

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

    def test_no_auth_but_configured_raises_401(self):
        """No credentials but auth IS configured -> 401."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(
                credentials=None,
                api_key=None,
                settings=_settings(api_key="configured-key"),
            )
        assert exc_info.value.status_code == 401


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

    def test_returns_none_on_failure(self):
        result = get_optional_user(
            credentials=None,
            api_key=None,
            settings=_settings(api_key="configured-key"),
        )
        assert result is None

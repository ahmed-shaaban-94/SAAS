"""Tests for datapulse.embed.token module."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import jwt
import pytest

from datapulse.embed.token import (
    _ALGORITHM,
    _ISSUER,
    _get_secret,
    create_embed_token,
    validate_embed_token,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_settings(
    api_key: str = "test-secret-key", embed_secret: str = ""
) -> MagicMock:
    """Return a Settings-like object with the given secrets."""
    settings = MagicMock()
    settings.api_key = api_key
    settings.embed_secret = embed_secret
    return settings


# ---------------------------------------------------------------------------
# _get_secret
# ---------------------------------------------------------------------------


class TestGetSecret:
    """Tests for _get_secret helper."""

    def test_prefers_embed_secret(self):
        with patch(
            "datapulse.embed.token.get_settings",
            return_value=_mock_settings(api_key="api-key", embed_secret="dedicated"),
        ):
            assert _get_secret() == "dedicated"

    def test_falls_back_to_api_key(self):
        with patch(
            "datapulse.embed.token.get_settings",
            return_value=_mock_settings(api_key="my-secret", embed_secret=""),
        ):
            assert _get_secret() == "my-secret"

    def test_raises_when_no_secret_configured(self):
        with patch(
            "datapulse.embed.token.get_settings",
            return_value=_mock_settings(api_key="", embed_secret=""),
        ), pytest.raises(ValueError, match="EMBED_SECRET or API_KEY must be configured"):
            _get_secret()

    def test_raises_when_both_none(self):
        with patch(
            "datapulse.embed.token.get_settings",
            return_value=_mock_settings(api_key=None, embed_secret=None),
        ), pytest.raises(ValueError, match="EMBED_SECRET or API_KEY must be configured"):
            _get_secret()


# ---------------------------------------------------------------------------
# create_embed_token
# ---------------------------------------------------------------------------


class TestCreateEmbedToken:
    """Tests for create_embed_token."""

    @pytest.fixture(autouse=True)
    def _patch_settings(self):
        with patch(
            "datapulse.embed.token.get_settings",
            return_value=_mock_settings("test-secret"),
        ):
            yield

    def test_returns_string(self):
        token = create_embed_token("tenant-1")
        assert isinstance(token, str)

    def test_returns_valid_jwt(self):
        token = create_embed_token("tenant-1")
        decoded = jwt.decode(token, "test-secret", algorithms=[_ALGORITHM], issuer=_ISSUER)
        assert isinstance(decoded, dict)

    def test_correct_claims(self):
        token = create_embed_token(
            tenant_id="t-42",
            resource_type="dashboard",
            resource_id="dash-7",
        )
        decoded = jwt.decode(token, "test-secret", algorithms=[_ALGORITHM], issuer=_ISSUER)
        assert decoded["iss"] == _ISSUER
        assert decoded["tenant_id"] == "t-42"
        assert decoded["resource_type"] == "dashboard"
        assert decoded["resource_id"] == "dash-7"

    def test_default_resource_type(self):
        token = create_embed_token("t-1")
        decoded = jwt.decode(token, "test-secret", algorithms=[_ALGORITHM], issuer=_ISSUER)
        assert decoded["resource_type"] == "explore"
        assert decoded["resource_id"] == ""

    def test_expiration_is_set(self):
        token = create_embed_token("t-1", expires_hours=2)
        decoded = jwt.decode(token, "test-secret", algorithms=[_ALGORITHM], issuer=_ISSUER)
        assert "exp" in decoded
        assert "iat" in decoded
        # exp should be ~2 hours after iat
        diff = decoded["exp"] - decoded["iat"]
        assert 7199 <= diff <= 7201  # allow 1-second tolerance

    def test_custom_expires_hours(self):
        token = create_embed_token("t-1", expires_hours=24)
        decoded = jwt.decode(token, "test-secret", algorithms=[_ALGORITHM], issuer=_ISSUER)
        diff = decoded["exp"] - decoded["iat"]
        assert 86399 <= diff <= 86401


# ---------------------------------------------------------------------------
# validate_embed_token
# ---------------------------------------------------------------------------


class TestValidateEmbedToken:
    """Tests for validate_embed_token."""

    @pytest.fixture(autouse=True)
    def _patch_settings(self):
        with patch(
            "datapulse.embed.token.get_settings",
            return_value=_mock_settings("test-secret"),
        ):
            yield

    def test_decodes_valid_token(self):
        token = create_embed_token("t-1", "explore", "res-5")
        result = validate_embed_token(token)
        assert result["tenant_id"] == "t-1"
        assert result["resource_type"] == "explore"
        assert result["resource_id"] == "res-5"

    def test_raises_on_expired_token(self):
        # Create a token that expired 1 hour ago
        payload = {
            "iss": _ISSUER,
            "iat": time.time() - 7200,
            "exp": time.time() - 3600,
            "tenant_id": "t-1",
            "resource_type": "explore",
            "resource_id": "",
        }
        token = jwt.encode(payload, "test-secret", algorithm=_ALGORITHM)
        with pytest.raises(jwt.InvalidTokenError):
            validate_embed_token(token)

    def test_raises_on_invalid_signature(self):
        payload = {
            "iss": _ISSUER,
            "iat": time.time(),
            "exp": time.time() + 3600,
            "tenant_id": "t-1",
            "resource_type": "explore",
            "resource_id": "",
        }
        token = jwt.encode(payload, "wrong-secret", algorithm=_ALGORITHM)
        with pytest.raises(jwt.InvalidTokenError):
            validate_embed_token(token)

    def test_raises_on_wrong_issuer(self):
        payload = {
            "iss": "not-datapulse",
            "iat": time.time(),
            "exp": time.time() + 3600,
            "tenant_id": "t-1",
            "resource_type": "explore",
            "resource_id": "",
        }
        token = jwt.encode(payload, "test-secret", algorithm=_ALGORITHM)
        with pytest.raises(jwt.InvalidTokenError):
            validate_embed_token(token)

    def test_raises_on_garbage_token(self):
        with pytest.raises(jwt.InvalidTokenError):
            validate_embed_token("not.a.jwt")


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Round-trip: create then validate returns correct claims."""

    @pytest.fixture(autouse=True)
    def _patch_settings(self):
        with patch(
            "datapulse.embed.token.get_settings",
            return_value=_mock_settings("round-trip-secret"),
        ):
            yield

    def test_round_trip_all_fields(self):
        token = create_embed_token(
            tenant_id="tenant-abc",
            resource_type="dashboard",
            resource_id="dash-99",
            expires_hours=4,
        )
        claims = validate_embed_token(token)
        assert claims["iss"] == "datapulse-embed"
        assert claims["tenant_id"] == "tenant-abc"
        assert claims["resource_type"] == "dashboard"
        assert claims["resource_id"] == "dash-99"

    def test_round_trip_defaults(self):
        token = create_embed_token(tenant_id="t-default")
        claims = validate_embed_token(token)
        assert claims["tenant_id"] == "t-default"
        assert claims["resource_type"] == "explore"
        assert claims["resource_id"] == ""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Verify module-level constants."""

    def test_issuer(self):
        assert _ISSUER == "datapulse-embed"

    def test_algorithm(self):
        assert _ALGORITHM == "HS256"

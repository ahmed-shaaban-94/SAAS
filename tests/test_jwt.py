"""Tests for JWT verification module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi import HTTPException

from datapulse.api.jwt import _fetch_jwks, clear_jwks_cache, verify_jwt


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear JWKS cache before each test."""
    clear_jwks_cache()
    yield
    clear_jwks_cache()


@pytest.fixture()
def mock_settings() -> MagicMock:
    s = MagicMock()
    s.auth0_jwks_url = "https://test.auth0.com/.well-known/jwks.json"
    s.auth0_issuer_url = "https://test.auth0.com/"
    s.auth0_audience = "https://api.test.com"
    s.auth0_client_id = "test-client-id"
    return s


class TestFetchJWKS:
    @patch("datapulse.core.jwt.httpx.get")
    def test_fetch_jwks_success(self, mock_get, mock_settings):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"keys": [{"kid": "key1"}]}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = _fetch_jwks(mock_settings)
        assert result["keys"][0]["kid"] == "key1"

    @patch("datapulse.core.jwt.httpx.get")
    def test_fetch_jwks_cached(self, mock_get, mock_settings):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"keys": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        _fetch_jwks(mock_settings)
        _fetch_jwks(mock_settings)
        # Should only call httpx once (cached)
        assert mock_get.call_count == 1

    @patch("datapulse.core.jwt.httpx.get")
    def test_fetch_jwks_failure_no_cache(self, mock_get, mock_settings):
        import httpx

        mock_get.side_effect = httpx.TransportError("Connection refused")

        with pytest.raises(HTTPException) as exc:
            _fetch_jwks(mock_settings)
        assert exc.value.status_code == 503

    @patch("datapulse.core.jwt.httpx.get")
    def test_fetch_jwks_failure_returns_stale_cache(self, mock_get, mock_settings):
        import httpx

        # First call succeeds
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"keys": [{"kid": "stale"}]}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        _fetch_jwks(mock_settings)

        # Force cache expiry and make second call fail
        import datapulse.core.jwt as jwt_mod

        jwt_mod._jwks_cache_time = 0.0
        mock_get.side_effect = httpx.TransportError("timeout")

        result = _fetch_jwks(mock_settings)
        assert result["keys"][0]["kid"] == "stale"


class TestVerifyJWT:
    @patch("datapulse.core.jwt.jwt.decode", side_effect=pyjwt.ExpiredSignatureError)
    @patch("datapulse.core.jwt._get_signing_key")
    def test_verify_jwt_expired(self, mock_key, mock_decode, mock_settings):
        mock_key.return_value = MagicMock(key="fake-key")
        with pytest.raises(HTTPException) as exc:
            verify_jwt("expired-token", settings=mock_settings)
        assert exc.value.status_code == 401
        assert "expired" in exc.value.detail.lower()

    @patch("datapulse.core.jwt._get_signing_key")
    @patch("datapulse.core.jwt.jwt.decode")
    def test_verify_jwt_invalid_issuer(self, mock_decode, mock_key, mock_settings):
        mock_key.return_value = MagicMock(key="fake")
        mock_decode.side_effect = pyjwt.InvalidIssuerError()

        with pytest.raises(HTTPException) as exc:
            verify_jwt("bad-token", settings=mock_settings)
        assert exc.value.status_code == 401

    @patch("datapulse.core.jwt._get_signing_key")
    @patch("datapulse.core.jwt.jwt.decode")
    def test_verify_jwt_invalid_audience(self, mock_decode, mock_key, mock_settings):
        mock_key.return_value = MagicMock(key="fake")
        mock_decode.side_effect = pyjwt.InvalidAudienceError()

        with pytest.raises(HTTPException) as exc:
            verify_jwt("bad-token", settings=mock_settings)
        assert exc.value.status_code == 401

    @patch("datapulse.core.jwt._get_signing_key")
    @patch("datapulse.core.jwt.jwt.decode")
    def test_verify_jwt_success(self, mock_decode, mock_key, mock_settings):
        mock_key.return_value = MagicMock(key="fake")
        mock_decode.return_value = {
            "sub": "user-1",
            "email": "test@test.com",
            "azp": "test-client-id",
        }
        claims = verify_jwt("valid-token", settings=mock_settings)
        assert claims["sub"] == "user-1"

    @patch("datapulse.core.jwt._get_signing_key")
    @patch("datapulse.core.jwt.jwt.decode")
    def test_verify_jwt_wrong_azp(self, mock_decode, mock_key, mock_settings):
        mock_key.return_value = MagicMock(key="fake")
        mock_decode.return_value = {
            "sub": "user-1",
            "azp": "wrong-client-id",
        }
        with pytest.raises(HTTPException) as exc:
            verify_jwt("token", settings=mock_settings)
        assert exc.value.status_code == 401
        assert "client" in exc.value.detail.lower()

    @patch("datapulse.core.jwt._get_signing_key")
    @patch("datapulse.core.jwt.jwt.decode")
    def test_verify_jwt_no_azp_passes(self, mock_decode, mock_key, mock_settings):
        mock_key.return_value = MagicMock(key="fake")
        mock_decode.return_value = {"sub": "user-1"}
        claims = verify_jwt("token", settings=mock_settings)
        assert claims["sub"] == "user-1"


class TestClearCache:
    def test_clear_jwks_cache(self):
        import datapulse.core.jwt as jwt_mod

        jwt_mod._jwks_cache = {"keys": []}
        jwt_mod._jwks_cache_time = 100.0
        clear_jwks_cache()
        assert jwt_mod._jwks_cache == {}
        assert jwt_mod._jwks_cache_time == 0.0
